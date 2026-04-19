# -*- coding: utf-8 -*-
"""routes/sources.py - 来源管理相关 API"""
from __future__ import annotations

import json, sqlite3, uuid, time, asyncio, base64, io, threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ─── 核心模块导入 ─────────────────────────────────────────────────────
from config import (
    BASE_DIR, DB_PATH, DATA_DIR, UPLOAD_DIR, FRONT_DIR,
    client, fallback_client, fallback2_client, get_minimax2_client,
    is_xunfei_blocked, ODL_AVAILABLE, get_paddle_ocr,
    MAX_CHARS, MAX_PROMPT_TEXT_CHARS, IP_DIRECTION,
    SMART_EXTRACTION_AVAILABLE,
    MINIMAX_API_KEY_2, MINIMAX_API_BASE_2, _AI_PREFERRED,
)
from db import get_db, now
from ai import ai_extract
from tasks import enqueue_task, _start_workers, _recover_stuck_tasks
from services.process import process_source_task, process_source_task_smart
from extraction import (
    extract_text_from_epub, extract_text_from_txt, extract_text_from_docx,
    extract_text_from_pdf, extract_text_from_url,
)
from prompts import EXTRACT_MODES, build_prompt, parse_materials, parse_atomic_notes

# ─── Worker 队列引用 ─────────────────────────────────────────────────
from tasks import _task_queue, WORKER_COUNT, TASK_MAX_SECONDS, _worker_threads, _worker_heartbeats
from tasks import _worker_loop, _spawn_worker, _watchdog_loop

# ─── 全局变量（运行时可修改）──────────────────────────────────────────
# AI Studio OCR Token（运行时初始化）
AISTUDIO_TOKEN = ""

# MiniMax2 客户端（运行时可更新）
_minimax2_client = None

router = APIRouter(tags=["sources"])

# ─── 辅助函数 ───────────────────────────────────────────────────────────
# 移除代理字符范围 (U+D800 到 U+DFFF)
_SURROGATE_RANGE = {i: None for i in range(0xD800, 0xE000)}


def _clean_surrogate(obj):
    """递归清理字符串中的 Python 代理字符（JSON 不支持）"""
    if isinstance(obj, str):
        return obj.translate(_SURROGATE_RANGE)
    elif isinstance(obj, dict):
        return {k: _clean_surrogate(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_surrogate(item) for item in obj]
    return obj

# ─── Request Models ──────────────────────────────────────────────────
class ImportFolderRequest(BaseModel):
    folder_path: str
    mode: str = "full"
    recursive: bool = False
    skip_existing: bool = True


class AddSourceRequest(BaseModel):
    title: str
    type: str
    content: str
    mode: str = "full"


class AistudioTokenRequest(BaseModel):
    token: str


class AiModelRequest(BaseModel):
    preferred: str
    minimax2_key: Optional[str] = None
    minimax2_base: Optional[str] = None


# ─── Routes ─────────────────────────────────────────────────────────

# 上传PDF书籍
@router.post("/api/sources/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), mode: str = "full"):
    file_id = str(uuid.uuid4())
    filename = file.filename or "unknown.pdf"
    save_path = UPLOAD_DIR / f"{file_id}_{filename}"

    content = await file.read()
    save_path.write_bytes(content)

    source_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    title = Path(filename).stem

    ext = Path(filename).suffix.lower()
    if ext == ".epub":
        source_type = "epub"
    elif ext in (".txt", ".md"):
        source_type = "txt"
    elif ext == ".docx":
        source_type = "docx"
    else:
        source_type = "book"

    conn = get_db()
    conn.execute(
        "INSERT INTO sources VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (source_id, title, source_type, str(save_path), None, "[]", 0, 0, "pending", None, 0, now(), now())
    )
    conn.execute(
        "INSERT INTO tasks VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (task_id, source_id, "pending", 0, "等待处理...", None, now(), now())
    )
    conn.commit()
    conn.close()

    enqueue_task(task_id, source_id, mode)
    return {"source_id": source_id, "task_id": task_id, "title": title}


# 文件夹批量导入
@router.post("/api/sources/import-folder")
async def import_folder(req: ImportFolderRequest):
    """扫描本地文件夹，将所有 PDF/EPUB/TXT 加入书库并启动提炼任务"""
    folder = Path(req.folder_path.strip())
    if not folder.exists():
        raise HTTPException(400, f"路径不存在：{folder}")
    if not folder.is_dir():
        raise HTTPException(400, f"该路径不是文件夹：{folder}")

    SUPPORTED_EXTS = (".pdf", ".epub", ".txt", ".md", ".docx")
    if req.recursive:
        all_files = [f for f in sorted(folder.rglob("*")) if f.suffix.lower() in SUPPORTED_EXTS]
    else:
        all_files = [f for f in sorted(folder.glob("*")) if f.suffix.lower() in SUPPORTED_EXTS]

    if not all_files:
        return {"total": 0, "queued": 0, "skipped": 0, "tasks": [],
                "message": "文件夹中没有找到 PDF/EPUB/TXT 文件"}

    conn = get_db()
    existing_titles = set()
    if req.skip_existing:
        rows = conn.execute("SELECT title FROM sources WHERE type IN ('book','epub','txt')").fetchall()
        existing_titles = {r["title"] for r in rows}

    tasks_created = []
    skipped = []

    for file_path in all_files:
        title = file_path.stem
        if req.skip_existing and title in existing_titles:
            skipped.append(title)
            continue

        ext = file_path.suffix.lower()
        if ext == ".epub":
            source_type = "epub"
        elif ext in (".txt", ".md"):
            source_type = "txt"
        elif ext == ".docx":
            source_type = "docx"
        else:
            source_type = "book"

        file_id = str(uuid.uuid4())
        dest = UPLOAD_DIR / f"{file_id}_{file_path.name}"
        try:
            import shutil
            shutil.copy2(str(file_path), str(dest))
        except Exception as e:
            skipped.append(f"{title} (复制失败: {e})")
            continue

        source_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO sources VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (source_id, title, source_type, str(dest), None, "[]", 0, 0,
             "pending", None, 0, now(), now())
        )
        conn.execute(
            "INSERT INTO tasks VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (task_id, source_id, "pending", 0, "等待批量提炼...", None, now(), now())
        )
        tasks_created.append({"task_id": task_id, "source_id": source_id, "title": title})
        existing_titles.add(title)

    conn.commit()
    conn.close()

    for t in tasks_created:
        enqueue_task(t["task_id"], t["source_id"], req.mode)

    return {
        "total": len(all_files),
        "queued": len(tasks_created),
        "skipped": len(skipped),
        "tasks": tasks_created,
        "message": f"已加入队列 {len(tasks_created)} 本，跳过 {len(skipped)} 本"
    }


# 预扫描文件夹
@router.get("/api/sources/scan-folder")
def scan_folder(path: str, recursive: bool = False):
    """预扫描文件夹，返回文件列表（不导入），用于前端预览"""
    folder = Path(path.strip())
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(400, "路径无效或不是文件夹")

    SUPPORTED_EXTS = (".pdf", ".epub", ".txt", ".md", ".docx")
    if recursive:
        all_files = sorted(f for f in folder.rglob("*") if f.suffix.lower() in SUPPORTED_EXTS)
    else:
        all_files = sorted(f for f in folder.glob("*") if f.suffix.lower() in SUPPORTED_EXTS)

    conn = get_db()
    existing_titles = {r["title"] for r in
                       conn.execute("SELECT title FROM sources WHERE type IN ('book','epub','txt','docx')").fetchall()}
    conn.close()

    items = []
    for p in all_files[:200]:
        size_mb = round(p.stat().st_size / 1024 / 1024, 1)
        items.append({
            "name": p.stem,
            "filename": p.name,
            "size_mb": size_mb,
            "already_imported": p.stem in existing_titles
        })

    return {"path": str(folder), "count": len(all_files), "items": items}


# 弹出系统文件夹选择对话框
@router.get("/api/pick-folder")
def pick_folder(initial_dir: str = ""):
    """弹出系统原生文件夹选择对话框，返回用户选中的路径。
    使用 tkinter（Python 标准库），无需额外安装。
    在后台线程中运行以避免阻塞 asyncio 事件循环。
    """
    import threading

    result_holder = {"path": None, "error": None}

    def _show_dialog():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            root.update()
            kwargs = {"title": "选择书籍文件夹"}
            if initial_dir and Path(initial_dir).is_dir():
                kwargs["initialdir"] = initial_dir
            selected = filedialog.askdirectory(**kwargs)
            root.destroy()
            result_holder["path"] = selected or ""
        except Exception as e:
            result_holder["error"] = str(e)

    t = threading.Thread(target=_show_dialog, daemon=True)
    t.start()
    t.join(timeout=120)

    if result_holder["error"]:
        raise HTTPException(500, f"无法打开文件夹选择框：{result_holder['error']}")

    return {"selected": result_holder["path"] or ""}


# 添加文字/URL来源
@router.post("/api/sources/add")
async def add_source(req: AddSourceRequest):
    source_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())

    conn = get_db()
    conn.execute(
        "INSERT INTO sources VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (source_id, req.title, req.type, None, req.content, "[]", 0, 0, "pending", None, 0, now(), now())
    )
    conn.execute(
        "INSERT INTO tasks VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (task_id, source_id, "pending", 0, "等待处理...", None, now(), now())
    )
    conn.commit()
    conn.close()

    enqueue_task(task_id, source_id, req.mode)
    return {"source_id": source_id, "task_id": task_id}


# 查询任务进度
@router.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id=%s", (task_id,)).fetchone()
    conn.close()
    if not task:
        raise HTTPException(404, "任务不存在")
    return dict(task)


# 获取所有书库
@router.get("/api/sources")
def list_sources(q: str = "", type: str = ""):
    conn = get_db()
    sql = "SELECT s.*, (SELECT COUNT(*) FROM materials m WHERE m.source_id=s.id) as material_count FROM sources s WHERE 1=1"
    params = []
    if q:
        sql += " AND s.title LIKE %s"
        params.append(f"%{q}%")
    if type:
        sql += " AND s.type=%s"
        params.append(type)
    sql += " ORDER BY s.created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return _clean_surrogate([dict(r) for r in rows])


# 重试失败任务
@router.post("/api/sources/{source_id}/retry")
async def retry_source(source_id: str, mode: str = "full"):
    """重新提炼：重置 source + task 状态，立即重新入队"""
    conn = get_db()
    src = conn.execute("SELECT * FROM sources WHERE id=%s", (source_id,)).fetchone()
    if not src:
        conn.close()
        raise HTTPException(404, "书籍不存在")

    conn.execute(
        "UPDATE sources SET status='pending', error_msg=NULL, updated_at=%s WHERE id=%s",
        (now(), source_id)
    )

    existing_task = conn.execute(
        "SELECT id FROM tasks WHERE source_id=%s ORDER BY created_at DESC LIMIT 1",
        (source_id,)
    ).fetchone()
    if existing_task:
        task_id = existing_task["id"]
        conn.execute(
            "UPDATE tasks SET status='pending', progress=0, message='重试中，等待处理...', result=NULL, updated_at=%s WHERE id=%s",
            (now(), task_id)
        )
    else:
        task_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO tasks VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (task_id, source_id, "pending", 0, "重试中，等待处理...", None, now(), now())
        )

    conn.commit()
    conn.close()

    enqueue_task(task_id, source_id, mode)
    return {"ok": True, "task_id": task_id, "status": "pending"}


# 一键恢复所有卡住的任务
@router.post("/api/sources/recover-all")
def recover_all_stuck():
    """将所有 processing/pending 状态的任务重新入队"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE sources SET status='pending', updated_at=%s WHERE status='processing'",
            (now(),)
        )
        conn.execute(
            "UPDATE tasks SET status='pending', message='等待恢复处理...', updated_at=%s WHERE status='processing'",
            (now(),)
        )
        conn.commit()

        rows = conn.execute(
            """SELECT t.id as task_id, t.source_id
               FROM tasks t JOIN sources s ON t.source_id = s.id
               WHERE s.status = 'pending'
               ORDER BY s.created_at"""
        ).fetchall()

        queued = 0
        for row in rows:
            enqueue_task(row["task_id"], row["source_id"], "full")
            queued += 1

        return {"ok": True, "queued": queued, "queue_size": _task_queue.qsize()}
    finally:
        conn.close()


# AI Studio OCR Token - 查询
@router.get("/api/ocr/aistudio-token")
def get_aistudio_token():
    """查询当前 AI Studio token 状态（不返回 token 明文）"""
    return {"configured": bool(AISTUDIO_TOKEN), "length": len(AISTUDIO_TOKEN)}


# AI Studio OCR Token - 设置
@router.post("/api/ocr/aistudio-token")
def set_aistudio_token(req: AistudioTokenRequest):
    """设置 AI Studio OCR token（运行时生效，重启后失效，如需持久化请设置环境变量 AISTUDIO_TOKEN）"""
    global AISTUDIO_TOKEN
    AISTUDIO_TOKEN = req.token.strip()
    os.environ["AISTUDIO_TOKEN"] = AISTUDIO_TOKEN
    return {"ok": True, "configured": bool(AISTUDIO_TOKEN)}


# AI 模型选择 - 查询
@router.get("/api/ai-model")
def get_ai_model():
    """查询当前 AI 首选模型状态"""
    global _AI_PREFERRED, MINIMAX_API_KEY_2, MINIMAX_API_BASE_2
    labels = {
        "xunfei":   "讯飞星辰",
        "minimax":  "MiniMax（账号1）",
        "minimax2": "MiniMax（账号2）",
        "deepseek": "DeepSeek",
    }
    return {
        "preferred": _AI_PREFERRED,
        "preferred_label": labels.get(_AI_PREFERRED, _AI_PREFERRED),
        "minimax2_configured": bool(MINIMAX_API_KEY_2),
        "minimax2_key_preview": (MINIMAX_API_KEY_2[:8] + "****") if MINIMAX_API_KEY_2 else "",
        "minimax2_base": MINIMAX_API_BASE_2,
        "available_models": [
            {"id": "xunfei",   "label": "讯飞星辰",       "note": "每日 5000万 token，文本理解最强"},
            {"id": "minimax",  "label": "MiniMax（账号1）","note": "每6小时 4000次，旧账号"},
            {"id": "minimax2", "label": "MiniMax（账号2）","note": "每6小时 4000次，需填入 API Key"},
            {"id": "deepseek", "label": "DeepSeek",        "note": "最终兜底，按量计费"},
        ]
    }


# AI 模型选择 - 设置
@router.post("/api/ai-model")
def set_ai_model(req: AiModelRequest):
    """切换全局 AI 首选模型（立即生效，后续所有提炼任务从该模型开始）"""
    global _AI_PREFERRED, MINIMAX_API_KEY_2, MINIMAX_API_BASE_2, _minimax2_client
    allowed = {"xunfei", "minimax", "minimax2", "deepseek"}
    if req.preferred not in allowed:
        raise HTTPException(status_code=400, detail=f"preferred 必须是: {allowed}")

    if req.minimax2_key is not None:
        MINIMAX_API_KEY_2 = req.minimax2_key.strip()
        _minimax2_client = None
        if req.minimax2_base:
            MINIMAX_API_BASE_2 = req.minimax2_base.strip()

    if req.preferred == "minimax2" and not MINIMAX_API_KEY_2:
        raise HTTPException(status_code=400, detail="切换到 MiniMax 账号2 前，请先在 minimax2_key 字段填写 API Key")

    _AI_PREFERRED = req.preferred
    labels = {"xunfei":"讯飞星辰","minimax":"MiniMax（账号1）","minimax2":"MiniMax（账号2）","deepseek":"DeepSeek"}
    print(f"[AI] 用户切换首选模型 → {labels.get(_AI_PREFERRED)}")
    return {"ok": True, "preferred": _AI_PREFERRED, "label": labels.get(_AI_PREFERRED)}


# 查询正在处理中的任务详情
@router.get("/api/processing-tasks")
def processing_tasks():
    """返回所有 processing 状态的书籍及其最新任务进度（title、progress、message）"""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT s.id as source_id, s.title, s.status as source_status,
                   t.id as task_id, t.status as task_status,
                   t.progress, t.message, t.updated_at
            FROM sources s
            LEFT JOIN tasks t ON t.source_id = s.id
            WHERE s.status IN ('processing', 'pending')
            ORDER BY t.updated_at DESC
        """).fetchall()
        seen = set()
        result = []
        for row in rows:
            sid = row["source_id"]
            if sid in seen:
                continue
            seen.add(sid)
            result.append({
                "source_id": sid,
                "title": row["title"],
                "source_status": row["source_status"],
                "task_id": row["task_id"],
                "task_status": row["task_status"],
                "progress": row["progress"] or 0,
                "message": row["message"] or "",
                "updated_at": row["updated_at"] or "",
            })
        return result
    finally:
        conn.close()


# 查询当前队列状态
@router.get("/api/queue-status")
def queue_status():
    """返回当前任务队列大小 + worker 线程存活状态 + 心跳信息"""
    conn = get_db()
    try:
        pending = conn.execute("SELECT COUNT(*) FROM sources WHERE status='pending'").fetchone()['count']
        processing = conn.execute("SELECT COUNT(*) FROM sources WHERE status='processing'").fetchone()['count']
        done = conn.execute("SELECT COUNT(*) FROM sources WHERE status='done'").fetchone()['count']
        error = conn.execute("SELECT COUNT(*) FROM sources WHERE status='error'").fetchone()['count']
        alive_workers = sum(1 for t in _worker_threads if t.is_alive())
        now_ts = time.time()
        worker_states = []
        for i, t in enumerate(_worker_threads):
            wid = i + 1
            hb = _worker_heartbeats.get(wid, 0)
            if not t.is_alive():
                state = "dead"
            elif hb == 0:
                state = "idle"
            else:
                elapsed = int(now_ts - hb)
                state = f"busy({elapsed}s)"
            worker_states.append(state)
        return {
            "queue_size": _task_queue.qsize(),
            "workers": WORKER_COUNT,
            "alive_workers": alive_workers,
            "worker_states": worker_states,
            "pending": pending,
            "processing": processing,
            "done": done,
            "error": error,
        }
    finally:
        conn.close()


# 手动重启 workers
@router.post("/api/workers/restart")
def restart_workers():
    """手动重建所有 worker 线程（用于 worker 线程异常死亡时应急恢复）"""
    global _worker_threads
    dead = [i for i, t in enumerate(_worker_threads) if not t.is_alive()]
    for i in dead:
        new_t = _spawn_worker(i + 1)
        _worker_threads[i] = new_t
        print(f"[API] Worker-{i+1} 手动重建")
    alive = sum(1 for t in _worker_threads if t.is_alive())
    return {"ok": True, "restarted": len(dead), "alive_workers": alive, "queue_size": _task_queue.qsize()}


# 强制跳过卡住的任务
@router.post("/api/sources/skip-stuck")
def skip_stuck_tasks():
    """将所有长时间卡在 processing 的任务标记为 error，让队列继续跑"""
    conn = get_db()
    try:
        stuck_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rows = conn.execute(
            """SELECT s.id as source_id, t.id as task_id
               FROM sources s LEFT JOIN tasks t ON t.source_id = s.id
               WHERE s.status = 'processing'"""
        ).fetchall()
        skipped = 0
        for row in rows:
            conn.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                         ("手动强制跳过（任务卡住）", now(), row["source_id"]))
            if row["task_id"]:
                conn.execute("UPDATE tasks SET status='error',message=%s,updated_at=%s WHERE id=%s",
                             ("手动强制跳过（任务卡住）", now(), row["task_id"]))
            skipped += 1
        conn.commit()
        print(f"[API] 强制跳过 {skipped} 个卡住任务")
        return {"ok": True, "skipped": skipped, "queue_size": _task_queue.qsize()}
    finally:
        conn.close()


# 重置所有错误任务为 pending，重新入队
@router.post("/api/sources/retry-errors")
def retry_error_tasks():
    """将所有 error 状态的任务重置为 pending 重新入队"""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT t.id as task_id, t.source_id
               FROM tasks t JOIN sources s ON t.source_id = s.id
               WHERE s.status = 'error'"""
        ).fetchall()
        retried = 0
        for row in rows:
            conn.execute("UPDATE sources SET status='pending',error_msg=NULL,updated_at=%s WHERE id=%s",
                         (now(), row["source_id"]))
            conn.execute("UPDATE tasks SET status='pending',message='重新等待处理...',progress=0,updated_at=%s WHERE id=%s",
                         (now(), row["task_id"]))
            enqueue_task(row["task_id"], row["source_id"], "full")
            retried += 1
        conn.commit()
        print(f"[API] 重试 {retried} 个错误任务")
        return {"ok": True, "retried": retried, "queue_size": _task_queue.qsize()}
    finally:
        conn.close()


# 一键清空书库（全部删除）
@router.delete("/api/sources")
def delete_all_sources():
    conn = get_db()
    try:
        rows = conn.execute("SELECT file_path FROM sources WHERE file_path IS NOT NULL AND file_path != ''").fetchall()
        for row in rows:
            try:
                Path(row["file_path"]).unlink(missing_ok=True)
            except Exception:
                pass
        conn.execute("DELETE FROM materials")
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM sources")
        conn.commit()
        return {"ok": True, "deleted": len(rows)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# 删除来源
@router.delete("/api/sources/{source_id}")
def delete_source(source_id: str):
    conn = get_db()
    conn.execute("DELETE FROM materials WHERE source_id=%s", (source_id,))
    conn.execute("DELETE FROM tasks WHERE source_id=%s", (source_id,))
    src = conn.execute("SELECT file_path FROM sources WHERE id=%s", (source_id,)).fetchone()
    if src and src["file_path"]:
        try: Path(src["file_path"]).unlink()
        except: pass
    conn.execute("DELETE FROM sources WHERE id=%s", (source_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# 来源健康检查
@router.get("/api/sources/{source_id}")
def get_source_health(source_id: str):
    """来源健康检查端点"""
    return {"status": "ok", "source_id": source_id}


# 启动智能提取（新版）
@router.post("/api/sources/{source_id}/extract-smart")
def start_smart_extraction(source_id: str, mode: str = "full"):
    """启动智能提取流程（分层Chunking + 多轮Pipeline + 质量评分）"""
    if not SMART_EXTRACTION_AVAILABLE:
        raise HTTPException(400, "智能提取模块未加载，请检查依赖")

    conn = get_db()
    src = conn.execute("SELECT * FROM sources WHERE id=%s", (source_id,)).fetchone()
    if not src:
        conn.close()
        raise HTTPException(404, "来源不存在")

    task_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tasks VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (task_id, source_id, "pending", 0, "等待智能提取...", None, now(), now())
    )
    conn.commit()
    conn.close()

    enqueue_task(task_id, source_id, "smart")

    return {
        "task_id": task_id,
        "source_id": source_id,
        "mode": "smart",
        "message": "智能提取任务已创建（分层Chunking+多轮Pipeline+质量评分）"
    }


# 对比新旧提取方式
@router.post("/api/sources/{source_id}/extract-compare")
def compare_extraction_methods(source_id: str):
    """对比原版和智能版提取效果（测试用）"""
    conn = get_db()
    src = conn.execute("SELECT * FROM sources WHERE id=%s", (source_id,)).fetchone()
    if not src:
        conn.close()
        raise HTTPException(404, "来源不存在")

    # 原版任务
    task1_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tasks VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (task1_id, source_id, "pending", 0, "原版提取", None, now(), now())
    )

    # 智能版任务
    task2_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tasks VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (task2_id, source_id, "pending", 0, "智能提取", None, now(), now())
    )
    conn.commit()
    conn.close()

    # 启动任务
    enqueue_task(task1_id, source_id, "full")
    enqueue_task(task2_id, source_id, "full")

    return {
        "classic_task_id": task1_id,
        "smart_task_id": task2_id,
        "message": "对比任务已创建，请分别查看结果"
    }
