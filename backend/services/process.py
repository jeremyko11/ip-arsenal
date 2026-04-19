# -*- coding: utf-8 -*-
"""
services/process.py - 任务执行核心逻辑

从 main.py 迁移而来，供 tasks.py worker 调用。
"""
import uuid, json, concurrent.futures

from config import (
    client, fallback_client, fallback2_client,
    MODEL_ID, FALLBACK_MODEL_ID, FALLBACK2_MODEL_ID,
    IP_DIRECTION, is_xunfei_blocked,
    SMART_EXTRACTION_AVAILABLE,
)
from db import get_db, now
from ai import ai_extract
from extraction import (
    extract_text_from_epub, extract_text_from_txt,
    extract_text_from_docx, extract_text_from_pdf,
    extract_text_from_url,
)
from prompts import build_prompt, parse_materials


def process_source_task(task_id: str, source_id: str, mode: str):
    conn = get_db()
    try:
        def update_task(status, progress, message, result=None):
            conn.execute(
                "UPDATE tasks SET status=%s,progress=%s,message=%s,result=%s,updated_at=%s WHERE id=%s",
                (status, progress, message, result, now(), task_id)
            )
            conn.commit()

        update_task("processing", 10, "读取文件中...")
        src = conn.execute("SELECT * FROM sources WHERE id=%s", (source_id,)).fetchone()
        if not src:
            update_task("error", 0, "找不到来源记录")
            return

        # 提取文本
        text = ""
        page_count = 0
        is_scanned = False
        is分段处理 = False
        if src["type"] == "epub" and src["file_path"]:
            is分段处理 = False
            text, page_count, is_scanned = extract_text_from_epub(src["file_path"], update_task)
            if not text:
                conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                             ("EPUB 解析失败，文件可能损坏或格式不标准", now(), source_id))
                conn.commit()
                update_task("error", 0, "EPUB 解析失败，请检查文件")
                return
        elif src["type"] == "txt" and src["file_path"]:
            text, page_count, is_scanned = extract_text_from_txt(src["file_path"], update_task)
            if not text:
                conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                             ("文本文件读取失败", now(), source_id))
                conn.commit()
                update_task("error", 0, "文本文件读取失败")
                return
            is分段处理 = isinstance(text, list)
        elif src["type"] == "docx" and src["file_path"]:
            is分段处理 = False
            text, page_count, is_scanned = extract_text_from_docx(src["file_path"], update_task)
            if not text:
                conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                             ("Word 文档读取失败，文件可能损坏或加密", now(), source_id))
                conn.commit()
                update_task("error", 0, "Word 文档读取失败，请检查文件")
                return
        elif src["type"] == "book" and src["file_path"]:
            is分段处理 = False
            text, page_count, is_scanned = extract_text_from_pdf(src["file_path"], update_task)
            if not text:
                conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                             ("PDF无可提取文字（可能是加密或损坏）", now(), source_id))
                conn.commit()
                update_task("error", 0, "PDF无法识别文字，请检查文件是否加密或损坏")
                return
        elif src["type"] == "text":
            is分段处理 = False
            text = src["url"] or ""
            page_count = 1
        elif src["type"] == "url":
            try:
                text = extract_text_from_url(src["url"])
            except ValueError as ve:
                err_msg = str(ve)
                conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                             (err_msg, now(), source_id))
                conn.commit()
                update_task("error", 0, err_msg)
                return
            page_count = 1

        total_chars = sum(len(c) for c in text) if isinstance(text, list) else len(text)
        conn.execute("UPDATE sources SET page_count=%s,char_count=%s,status='processing',updated_at=%s WHERE id=%s",
                     (page_count, total_chars, now(), source_id))
        conn.commit()

        ocr_hint = "（扫描版·AI-OCR）" if is_scanned else ""

        if is分段处理:
            update_task("processing", 60, f"文本提取完成{ocr_hint}（{len(text)} 个分段，共 {total_chars:,} 字），正在并行 AI 提炼（{len(text)} 个分段）...")

            def _extract_one_sync(i: int, chunk: str, title: str):
                """同步执行单个分段的 AI 提炼（在 ThreadPoolExecutor 中运行）"""
                prompt_sys, prompt_usr = build_prompt(f"{title} (第{i+1}段)", chunk, mode)
                raw, model = ai_extract(prompt_sys, prompt_usr, 8000, 0.7)
                return parse_materials(source_id, raw)

            # 所有分段并行提炼（使用 ThreadPoolExecutor 代替 asyncio.run）
            n_chunks = len(text)
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(n_chunks, 8), thread_name_prefix="ExtractChunk") as tex:
                futures = [tex.submit(_extract_one_sync, i, text[i], src["title"]) for i in range(n_chunks)]
                chunk_results = [f.result() for f in concurrent.futures.as_completed(futures)]
            all_materials = []
            for mats in chunk_results:
                all_materials.extend(mats)

            raw_content = f"【合并 {len(text)} 个分段提炼结果】\n" + "\n---\n".join([f"第{i+1}段" for i in range(len(text))])
            materials = all_materials
            model_used = "分段模式"
        else:
            update_task("processing", 72, f"文本提取完成{ocr_hint}（{total_chars:,}字），正在调用AI提炼...")
            system_prompt, user_prompt = build_prompt(src["title"], text, mode)
            raw_content, model_used = ai_extract(system_prompt, user_prompt, max_tokens=8000, temperature=0.7)
            fallback_hint = "（备用模型）" if model_used == FALLBACK_MODEL_ID else ""
            update_task("processing", 88, f"AI提炼完成{fallback_hint}，正在解析存储...")
            materials = parse_materials(source_id, raw_content)

        update_task("processing", 92, f"正在存储 {len(materials)} 条素材...")

        for m in materials:
            conn.execute("""
                INSERT INTO materials (id, source_id, category, content, metadata, tags, platform, use_count, is_starred, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    source_id=EXCLUDED.source_id,
                    category=EXCLUDED.category,
                    content=EXCLUDED.content,
                    metadata=EXCLUDED.metadata,
                    tags=EXCLUDED.tags,
                    platform=EXCLUDED.platform,
                    use_count=EXCLUDED.use_count,
                    is_starred=EXCLUDED.is_starred
            """, (m["id"], m["source_id"], m["category"], m["content"],
                  m["metadata"], m["tags"], m["platform"],
                  m["use_count"], m["is_starred"], m["created_at"]))

        conn.execute("UPDATE sources SET status='done',is_scanned=%s,updated_at=%s WHERE id=%s",
                     (1 if is_scanned else 0, now(), source_id))
        conn.commit()

        update_task("done", 100, f"完成！提取 {len(materials)} 条素材（{len(text) if is分段处理 else 1} 个分段）", raw_content[:500])

    except Exception as e:
        err_str = str(e)
        is_all_xunfei_block = (
            is_xunfei_blocked(err_str) and
            "MiniMax" not in err_str and
            "minimax" not in err_str.lower() and
            "DeepSeek" not in err_str
        )
        if is_all_xunfei_block:
            friendly = "讯飞内容审核拦截，备用模型也未能处理。建议手动删除后重新上传，或换用其他同类书籍。"
        else:
            friendly = f"提炼失败：{err_str[:300]}"
        conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                     (friendly, now(), source_id))
        conn.commit()
        conn.execute("UPDATE tasks SET status='error',message=%s,updated_at=%s WHERE id=%s",
                     (friendly, now(), task_id))
        conn.commit()
    finally:
        conn.close()


def process_source_task_smart(task_id: str, source_id: str, mode: str = "full"):
    """
    智能提取流程 - 使用分层 Chunking + 多轮迭代 + 质量评分

    相比原版 process_source_task，改进点：
    1. 分层 Chunking：保留书籍结构，按章节语义切分
    2. 多轮迭代：结构理解 → 逐章提取 → 跨章分析 → IP选题
    3. 质量评分：完整度/唯一性/IP契合度/可执行性/风险等级
    4. 智能路由：自动批准/人工审核/自动丢弃
    """
    if not SMART_EXTRACTION_AVAILABLE:
        print(f"[SmartExtraction] 模块不可用，回退到原版流程")
        process_source_task(task_id, source_id, mode)
        return

    conn = get_db()

    def update_task(status, progress, message, result=None):
        conn.execute(
            "UPDATE tasks SET status=%s,progress=%s,message=%s,result=%s,updated_at=%s WHERE id=%s",
            (status, progress, message, result, now(), task_id)
        )
        conn.commit()

    try:
        update_task("processing", 5, "准备智能提取流程...")

        src = conn.execute("SELECT * FROM sources WHERE id=%s", (source_id,)).fetchone()
        if not src:
            update_task("error", 0, "找不到来源记录")
            return

        update_task("processing", 10, "正在提取文本...")
        text = ""
        page_count = 0
        is_scanned = False

        if src["type"] == "epub" and src["file_path"]:
            text, page_count, is_scanned = extract_text_from_epub(src["file_path"], update_task)
            if not text:
                conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                             ("EPUB 解析失败", now(), source_id))
                conn.commit()
                update_task("error", 0, "EPUB 解析失败")
                return
        elif src["type"] == "txt" and src["file_path"]:
            text, page_count, is_scanned = extract_text_from_txt(src["file_path"], update_task)
            if not text:
                conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                             ("文本文件读取失败", now(), source_id))
                conn.commit()
                update_task("error", 0, "文本文件读取失败")
                return
            if isinstance(text, list):
                text = "\n\n".join(text)
        elif src["type"] == "docx" and src["file_path"]:
            text, page_count, is_scanned = extract_text_from_docx(src["file_path"], update_task)
            if not text:
                conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                             ("Word 文档读取失败", now(), source_id))
                conn.commit()
                update_task("error", 0, "Word 文档读取失败")
                return
        elif src["type"] == "book" and src["file_path"]:
            text, page_count, is_scanned = extract_text_from_pdf(src["file_path"], update_task)
            if not text:
                conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                             ("PDF无可提取文字", now(), source_id))
                conn.commit()
                update_task("error", 0, "PDF无法识别文字")
                return
        elif src["type"] == "text":
            text = src["url"] or ""
            page_count = 1
        elif src["type"] == "url":
            text = extract_text_from_url(src["url"])
            page_count = 1

        conn.execute("UPDATE sources SET page_count=%s,char_count=%s,status='processing',updated_at=%s WHERE id=%s",
                     (page_count, len(text), now(), source_id))
        conn.commit()

        ocr_hint = "（扫描版·AI-OCR）" if is_scanned else ""
        update_task("processing", 15, f"文本提取完成{ocr_hint}（{len(text):,}字），启动智能分析...")

        from chunking import chunk_book_text

        def chunking_progress(stage, progress, message):
            mapped = 15 + int(progress * 0.1)
            update_task("processing", mapped, f"[结构分析] {message}")

        chunked = chunk_book_text(
            text=text,
            book_name=src["title"],
            max_chunk_size=4000
        )

        update_task("processing", 25,
                    f"结构分析完成：{chunked['chapter_count']}章节，{chunked['chunk_count']}个片段")

        from extraction_pipeline import MultiRoundExtractionPipeline

        pipeline = MultiRoundExtractionPipeline(
            primary_client=client,
            fallback_client=fallback_client,
            fallback2_client=fallback2_client,
            primary_model=MODEL_ID,
            fallback_model=FALLBACK_MODEL_ID,
            fallback2_model=FALLBACK2_MODEL_ID,
            ip_direction=IP_DIRECTION
        )

        def extraction_progress(stage, progress, message):
            mapped = 25 + int(progress * 0.65)
            update_task("processing", mapped, f"[{stage}] {message}")

        result = pipeline.extract_full(
            book_name=src["title"],
            text=text,
            progress_callback=extraction_progress
        )

        update_task("processing", 90, "提取完成，正在进行质量评分...")

        from quality_control import QualityControlPipeline

        qc = QualityControlPipeline(ip_direction=IP_DIRECTION)

        all_materials = []
        round2_results = result["extraction_pipeline"]["round2_chapters"]

        for r in round2_results:
            data = r["structured_data"]

            for q in data.get("quotes", []):
                all_materials.append({
                    "category": "quote",
                    "content": q.get("text", ""),
                    "metadata": {
                        "risk": q.get("risk", "safe"),
                        "scene": q.get("scene", "deep"),
                        "cost": q.get("cost", "mid"),
                        "timeliness": q.get("timeliness", "long"),
                        "context": q.get("context", "")
                    }
                })

            for c in data.get("cases", []):
                content = f"**{c.get('name', '案例')}**\n- 冲突：{c.get('conflict', '')}\n- 动作：{c.get('action', '')}\n- 结果：{c.get('result', '')}\n- 启示：{c.get('insight', '')}"
                all_materials.append({
                    "category": "case",
                    "content": content,
                    "metadata": {
                        "risk": c.get("risk", "safe"),
                        "timeliness": c.get("timeliness", "long")
                    }
                })

            for v in data.get("viewpoints", []):
                content = f"**{v.get('title', '观点')}**\n- 书中依据：{v.get('evidence', '')}\n- IP化角度：{v.get('angle', '')}\n- 冲突预警：{v.get('conflict_warning', '')}"
                all_materials.append({
                    "category": "viewpoint",
                    "content": content,
                    "metadata": {
                        "risk": v.get("risk", "safe"),
                        "timeliness": v.get("timeliness", "long")
                    }
                })

            for a in data.get("actions", []):
                steps = "\n".join([f"  {i+1}. {s}" for i, s in enumerate(a.get("steps", []))])
                content = f"**{a.get('name', '行动')}**\n- 步骤：\n{steps}\n- 适用场景：{a.get('scenario', '')}\n- 风险提示：{a.get('risk_hint', '')}"
                all_materials.append({
                    "category": "action",
                    "content": content,
                    "metadata": {
                        "cost": a.get("cost", "mid")
                    }
                })

        existing = conn.execute(
            "SELECT content FROM materials WHERE source_id=%s", (source_id,)
        ).fetchall()
        existing_contents = [{"content": row["content"]} for row in existing]

        qc_results = qc.process(all_materials, existing_contents)

        approved_count = 0
        review_count = 0
        discarded_count = 0

        for m in qc_results["approved"]:
            meta = {**m["metadata"], "_quality_score": m.get("quality_score", {}), "_routing": "approved"}
            mid = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO materials (id, source_id, category, content, metadata, tags, platform, use_count, is_starred, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    source_id=EXCLUDED.source_id,
                    category=EXCLUDED.category,
                    content=EXCLUDED.content,
                    metadata=EXCLUDED.metadata,
                    tags=EXCLUDED.tags,
                    platform=EXCLUDED.platform,
                    use_count=EXCLUDED.use_count,
                    is_starred=EXCLUDED.is_starred
            """, (mid, source_id, m["category"], m["content"],
                  json.dumps(meta, ensure_ascii=False),
                  json.dumps([], ensure_ascii=False),
                  "[]", 0, 0, now()))
            approved_count += 1

        for m in qc_results["review"]:
            meta = {**m["metadata"], "_quality_score": m.get("quality_score", {}), "_routing": "review", "_review_needed": True}
            mid = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO materials (id, source_id, category, content, metadata, tags, platform, use_count, is_starred, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    source_id=EXCLUDED.source_id,
                    category=EXCLUDED.category,
                    content=EXCLUDED.content,
                    metadata=EXCLUDED.metadata,
                    tags=EXCLUDED.tags,
                    platform=EXCLUDED.platform,
                    use_count=EXCLUDED.use_count,
                    is_starred=EXCLUDED.is_starred
            """, (mid, source_id, m["category"], m["content"],
                  json.dumps(meta, ensure_ascii=False),
                  json.dumps([], ensure_ascii=False),
                  "[]", 0, 0, now()))
            review_count += 1

        discarded_count = len(qc_results["discarded"])

        conn.execute("UPDATE sources SET status='done',is_scanned=%s,updated_at=%s WHERE id=%s",
                     (1 if is_scanned else 0, now(), source_id))
        conn.commit()

        summary = result["summary"]
        report = (f"智能提取完成！\n"
                  f"✓ 自动入库: {approved_count} 条\n"
                  f"⚠ 待审核: {review_count} 条\n"
                  f"✗ 已过滤: {discarded_count} 条\n"
                  f"📊 原始素材: 金句{summary['total_quotes']}/"
                  f"案例{summary['total_cases']}/"
                  f"观点{summary['total_viewpoints']}/"
                  f"选题{summary['total_topics']}")

        update_task("done", 100, report, json.dumps(result, ensure_ascii=False)[:500])

    except Exception as e:
        err_str = str(e)
        print(f"[SmartExtraction] Error: {err_str}")
        import traceback
        traceback.print_exc()

        if is_xunfei_blocked(err_str):
            friendly = "内容审核拦截，请尝试其他书籍"
        else:
            friendly = f"智能提取失败：{err_str[:200]}"

        conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                     (friendly, now(), source_id))
        conn.commit()
        update_task("error", 0, friendly)
    finally:
        conn.close()
