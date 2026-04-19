# -*- coding: utf-8 -*-
"""routes/pushutree.py - 朴树之道书籍推荐视频脚本相关 API"""
from __future__ import annotations

import json, sqlite3, uuid, time, asyncio, base64, io, threading
import re
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

router = APIRouter(tags=["pushutree"])

# ─── 辅助函数 ───────────────────────────────────────────────────────────
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

# ─── 常量 ─────────────────────────────────────────────────────────────

PUSHUTREE_SYSTEM_PROMPT = """你是一个真正读过无数书的人，现在做书籍推荐视频/文案。

【你的核心定位】
你不是在写读书笔记，不是在写书评，也不是在讲故事。
你是在做"推荐词"——你要让一个完全不了解这本书的观众，在看完你这期内容之后：
1. 得到一个对他生活真正有用的认知/方法/感悟
2. 心里有点被触动（情绪共鸣）
3. 产生想去读这本书的冲动

每一期内容都是独立完整的。观众不需要看前一期，也不需要看后一期。
这不是连续剧，是系列推荐词——每期讲书里一个核心点，从不同角度打动人。

【什么是好的推荐词——学董宇辉/朴树之道】

董宇辉推荐书的方式：
- 先说一个让人心里一颤的问题或生活场景（开头抓人）
- 然后说书里怎么回答这个问题，或者这本书给了他什么新的认知
- 说自己的感受，不是复述书的内容
- 金句多，但不是鸡汤，是真实的洞察
- 让人觉得：这个人是真的读过，而且真的有感悟

朴树之道的感觉：
- 不装，不端，真实
- 说话像跟朋友聊天，不像在开讲座
- 有自己的判断和态度，不是中立的介绍

【硬性禁止】
❌ 叙事型写法："这本书讲了一个故事……""在书的第X章，作者提到……"
❌ 读书报告结构："这本书共分三部分，首先……其次……最后……"
❌ AI废话：深刻、启示、洞见、值得深思、引人深省、综上所述、由此可见
❌ 连续剧式开头："上一期我们讲到……""今天我们继续……"
❌ 讲述书的情节，像在讲故事

【每期推荐词的正确结构】
① 开头钩子（1-3句）：一个让人停下来的问题、反常识判断、或真实生活场景
   - 要打中观众的某个真实困惑或痛点
   - 前三句决定观众走不走

② 核心认知（2-3段）：
   - 书里给出的答案/方法/视角——但用你自己的话说
   - 要具体，用书里真实的案例/数据/故事支撑
   - 让人有"原来如此"的感觉

③ 为什么你/观众需要这本书（1-2段）：
   - 这个认知能帮观众解决什么真实问题
   - 读完这本书，观众的某一件事会变得不同

④ 结尾推荐句（1-2句）：
   - 不是"这本书值得一读"这种废话
   - 是一句让人想截图或转发的话
   - 带情绪，带态度，真实

【字数要求】：600-900字，干货密度高，不要凑字数

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【去AI化——写作灵魂规则，让文字像真人说出来的】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

这是口播稿，更不能有AI味。观众一眼就能听出来那种"机器人感"。

▌绝对禁止的AI词汇：
此外、总之、综上所述、值得注意的是、至关重要、深入探讨、深刻的启示、引人深省、
不禁让人、持久的影响、格局、赋能、洞见、值得深思、由此可见、不可磨灭、
见证了、标志着、体现了、不言而喻、毋庸置疑、可以说、某种程度上

▌禁止的AI写作结构（口播特别注意）：
- 三段论公式开头："有三个方面……" → 直接讲第一个，自然带出下一个
- 否定排比："这不仅仅是……而是……" → 直接说结论
- 宣传性形容词："深刻的""颠覆性的""令人震撼的" → 删掉，让事实本身说话
- 过长的句子（超过25字）→ 拆成两句，口播要短句

▌真人口播的写法：
- 多用"你"，少用"我们"——直接跟观众说话
- 允许说"说实话""我觉得""坦白说"——口语感
- 举的例子要具体，有数字有细节（"三年""每天早上6点""第87页"比"长期""坚持""书中"更真实）
- 句子有轻有重，有长有短——模拟真人说话的节奏
- 偶尔留一个问句让观众心里有点颤——不需要他回答，但他会停下来想"""


# ─── Helper Functions ─────────────────────────────────────────────────

def _fix_json_bare_quotes(json_str: str) -> str:
    """修复 JSON 字符串值内部的裸双引号（AI 常见输出错误）。

    逐字符扫描：在字符串值内遇到未转义的双引号时替换为单引号。
    这样 {"key": "he said "hello""} 会被修复为 {"key": "he said 'hello'"}
    """
    result = []
    in_string = False
    i = 0
    prev_was_key = False  # 上一个字符串是键（不在值里）

    while i < len(json_str):
        c = json_str[i]

        if not in_string:
            if c == '"':
                in_string = True
                result.append(c)
            else:
                result.append(c)
        else:
            if c == '\\' and i + 1 < len(json_str):
                # 合法转义序列，原样保留
                result.append(c)
                result.append(json_str[i + 1])
                i += 2
                continue
            elif c == '"':
                # 字符串结束，检查下一个非空白字符是否为 JSON 合法后续符
                j = i + 1
                while j < len(json_str) and json_str[j] in ' \t\r\n':
                    j += 1
                next_c = json_str[j] if j < len(json_str) else ''
                if next_c in ',:}]':
                    # 这是合法的字符串结束引号
                    in_string = False
                    result.append(c)
                else:
                    # 这是字符串内部的裸引号，替换为单引号
                    result.append("'")
            else:
                result.append(c)
        i += 1

    return ''.join(result)


def pushutree_plan(book_name: str, text: str, episode_count: int, style: str) -> list[dict]:
    """第一步：策划——分析全书找痛点，生成标题+大纲"""
    user_prompt = f"""请仔细阅读《{book_name}》的内容，用你作为一个真正读过这本书的人的眼光，找出{episode_count}个最值得分享的核心主题。

不要找那种"第X章讲了什么"的表面总结，要找：
- 让你看完会停下来想一想的观点
- 打破常见认知误区的内容
- 能帮普通人解决真实生活困惑的道理
- 书里藏着但很少人注意到的深层规律

【书籍内容】
{text[:60000]}

【输出要求】
请严格按照以下JSON格式输出，不要输出其他任何内容：
{{
  "episodes": [
    {{
      "ep_no": 1,
      "title": "标题（15字以内，有反差感或冲击力，不用你不知道的XX这类老套标题）",
      "angle": "这期的切入角度（一句话，说清楚从哪个生活场景或困惑切入）",
      "core_insight": "这期最核心的认知或规律（不是金句，是一个真实的洞察）",
      "pain_point": "击中的读者真实痛点（要具体，不要写迷茫这种大词）",
      "source_hint": "书中哪个章节或故事或案例或数据可以支撑",
      "why_useful": "读者看完能学到什么，能用在哪里（一句话）"
    }}
  ]
}}

重要：JSON字段的值必须是合法字符串，不能包含未转义的双引号（如需引用，请用书名号《》或单引号'代替）。
风格要求：{style}
共需{episode_count}期，每期角度不重复，要覆盖全书的精华，不要只集中在前几章。"""

    raw, _model = ai_extract(
        system_prompt=PUSHUTREE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=4000,
        temperature=0.7,
    )
    raw = raw.strip()
    # 提取JSON（容错：处理AI在JSON前后输出废话、markdown代码块、中文引号等）
    import re
    # 去掉 markdown 代码块包裹 ```json ... ```
    raw = re.sub(r'^```(%s:json)%s\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```\s*$', '', raw, flags=re.MULTILINE)
    # 替换中文引号为英文引号（常见AI输出错误）
    raw = raw.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
    # 提取最外层 JSON 对象
    m = re.search(r'\{[\s\S]*\}', raw)
    if m:
        json_str = m.group()
        # 第一次尝试：直接解析
        try:
            data = json.loads(json_str)
            return data.get("episodes", [])
        except json.JSONDecodeError as je:
            print(f"[pushutree_plan] 第一次JSON解析失败: {je}，尝试修复裸引号...")
        # 第二次尝试：修复字段值内的裸双引号
        # 思路：逐字扫描，在字符串值内部遇到裸双引号时替换为单引号
        try:
            fixed = _fix_json_bare_quotes(json_str)
            data = json.loads(fixed)
            print(f"[pushutree_plan] 修复裸引号后解析成功")
            return data.get("episodes", [])
        except Exception as je2:
            print(f"[pushutree_plan] 修复后仍失败: {je2}\n原始内容(前800): {json_str[:800]}")
            return []
    print(f"[pushutree_plan] 未找到JSON结构，原始内容(前500): {raw[:500]}")
    return []


def pushutree_write(book_name: str, text: str, episode: dict, style: str) -> str:
    """第二步：撰写——写一篇独立的书籍推荐词"""
    user_prompt = f"""现在为《{book_name}》写第{episode['ep_no']}期书籍推荐词。

【本期要传递的核心内容】
- 这期聚焦的角度：{episode['angle']}
- 核心认知：{episode.get('core_insight', episode.get('core_quote',''))}
- 观众痛点：{episode['pain_point']}
- 书中支撑：{episode['source_hint']}
- 观众能得到什么：{episode.get('why_useful','一个对生活有用的新认知')}

【书籍原文（供参考提取真实内容）】
{text[:50000]}

---

【写作任务】
写一篇让观众不想划走、看完有收获、想去读这本书的推荐词。

这不是读书笔记，不是书评，不是连续剧的某一集。
这是一篇独立完整的推荐词，观众看了这一期，不需要看其他期。

【必须做到的三件事】

第一：开头要抓人（前3句）
不要从"这本书讲了……"开始。
要从观众的真实感受/困惑/生活场景开始。
比如：
- 直接抛出一个让人心里一紧的问题
- 说一个很多人有但没说出来的感受
- 说一个和常识相反的判断

第二：干货要真实（中间部分）
用书里真实的案例、数据、观点来说话。
不要只说结论，要说"书里是怎么说的"——但用你自己的话，不是复制粘贴。
每个认知点要对应一个"观众能用在哪里"。

第三：结尾要有力量
不是"这本书值得一读"。
是一句让人想截图的话——有点哲学，有点反常识，或者说出了很多人想说又说不出来的话。

【风格】：{style}
【字数】：600-900字
【格式】：自然段落，口语化，短句为主，不用序号标题

【去AI化——写的时候就不能有AI味，不要等到精修再改】
✅ 用"你"开头或在关键句里直接和观众说话
✅ 举具体例子（书里的真实数字、细节、场景），不说空话
✅ 句子长短交错——3-5个短句打节奏，偶尔一句长句讲道理
✅ 有自己的态度——"我觉得这书有一点特别重要""说实话这个观点很少有人能做到"
❌ 绝对不写：此外、总之、由此可见、深刻的、至关重要、值得注意的是
❌ 绝对不用三段论公式：首先……其次……最后……"""

    draft, _model = ai_extract(
        system_prompt=PUSHUTREE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=3000,
        temperature=0.85,
    )
    return draft.strip()


def pushutree_polish(book_name: str, draft: str, episode: dict) -> str:
    """第三步：精修——观众视角终审 + 去AI化深度清洗"""
    user_prompt = f"""对下面这篇《{book_name}》书籍推荐词做最终精修。

【精修标准——你是一个极度挑剔的观众】

先以观众身份看一遍，问自己：

❶ 开头三句，我会不会划走？
   - 如果开头是"这本书讲了……" → 必须重写，从观众痛点切入
   - 如果开头是废话过渡 → 删掉，直接进正文

❷ 中间内容，我学到了什么？
   - 有没有一个对我日常生活真正有用的认知？
   - 说的是书里真实的东西，还是泛泛而谈？

❸ 这像推荐词还是读书报告？
   - 推荐词：说人话，有态度，让我想读这本书
   - 读书报告：复述内容，中立无感，让我想睡觉
   - 如果是读书报告味道 → 砍掉复述段落，换成"这对你意味着什么"

❹ 结尾金句，我会不会截图？
   - 不截图 → 重写

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【去AI化深度清洗——逐项检查，必须全部通过】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

这是口播稿，观众一听就知道是不是AI写的。把所有AI味彻底洗掉。

▌词汇层清查（发现即替换）：
❌ AI高频词：此外、总之、综上所述、值得注意的是、至关重要、深入探讨、深刻的启示、
   引人深省、不禁让人、持久的影响、格局、赋能、洞见、值得深思、由此可见、
   不可磨灭、见证了、标志着、体现了、不言而喻、毋庸置疑
→ 直接删除或换成口语表达

❌ 宣传性空话：充满活力的、丰富的、令人叹为观止的、深刻的、颠覆性的
→ 删掉形容词，用具体事实替代

▌结构层清查：
❌ 三段论公式（首先……其次……最后……）→ 打破，改成自然流动的口语叙述
❌ 否定排比（"这不仅仅是……而是……"）→ 直接说结论
❌ 以"这本书"或"作者"开头的句子（超过2句）→ 换成"你""我"的视角

▌节奏层清查：
❌ 超过30字的长句 → 拆成两句
❌ 连续3句以上相同句型（都是陈述句/都是问句）→ 换节奏
✅ 检查：有没有几个短句打节奏的段落？（好的口播稿一定有）

▌真实感注入：
- 如果全文没有一个具体数字或细节 → 补上（从书中找）
- 如果全文没有"你"字 → 至少加3处，直接和观众说话
- 如果结尾感觉是"总结"而不是"留白/回味" → 改成一句有态度的话

【原稿】
{draft}

【输出要求】
直接输出修改后的完整推荐词。不要说"已修改如下"，不要有任何前缀。
保留原有信息量，让语言更自然、更有力、更像真人在说话。
这篇文章应该让人读完觉得：这是一个真正读过这本书、有自己想法的人写的。"""

    polished, _model = ai_extract(
        system_prompt=PUSHUTREE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=3000,
        temperature=0.6,
    )
    return polished.strip()


def run_pushutree_task(script_id: str, source_id: str, episode_count: int,
                       platform: str, style: str, direct_text: str = "", direct_book_name: str = ""):
    """后台任务：朴树之道三步流程
    支持两种模式：
    1. 书库模式：source_id 非空，从数据库读取书籍
    2. 独立模式：source_id 为空，用 direct_text + direct_book_name
    """
    conn = get_db()

    def upd(status, progress, message, episodes=None, plan=None, error_msg=None):
        fields = "status=%s,progress=%s,message=%s,updated_at=%s"
        vals = [status, progress, message, now()]
        if episodes is not None:
            fields += ",episodes=%s"
            vals.append(json.dumps(episodes, ensure_ascii=False))
        if plan is not None:
            fields += ",plan=%s"
            vals.append(json.dumps(plan, ensure_ascii=False))
        if error_msg is not None:
            fields += ",error_msg=%s"
            vals.append(error_msg)
        vals.append(script_id)
        conn.execute(f"UPDATE scripts SET {fields} WHERE id=%s", vals)
        conn.commit()

    try:
        upd("processing", 5, "准备书籍内容...")

        text = ""
        book_name = direct_book_name

        if direct_text:
            # 独立模式：直接用传入的文本
            text = direct_text
            upd("processing", 15, f"已获取书籍文本，共{len(text)}字...")
        elif source_id:
            # 书库模式：从数据库读取
            upd("processing", 8, "读取书籍信息...")
            src = conn.execute("SELECT * FROM sources WHERE id=%s", (source_id,)).fetchone()
            if not src:
                upd("error", 0, "找不到书籍", error_msg="source not found")
                return
            book_name = src["title"]

            # 从PDF文件提取文本（任意状态的书籍都可以，不必须提炼完成）
            print(f"[DEBUG] pushutree source: type={src['type']}, file_path={src['file_path']}, url={src['url']}")
            if src["type"] == "book" and src["file_path"]:
                upd("processing", 10, "提取PDF文本...")
                text, _, _ = extract_text_from_pdf(src["file_path"])
                upd("processing", 15, f"PDF文本提取完成（{len(text)}字）...")
            elif src["type"] == "epub" and src["file_path"]:
                # epub 类型
                upd("processing", 10, "解析EPUB文件...")
                text, _, _ = extract_text_from_epub(src["file_path"])
                if isinstance(text, list):
                    text = "\n".join(text)
                upd("processing", 15, f"EPUB解析完成（{len(text)}字）...")
            elif src["type"] == "txt" and src["file_path"]:
                # txt 类型
                upd("processing", 10, "读取文本文件...")
                text, _, _ = extract_text_from_txt(src["file_path"])
                if isinstance(text, list):
                    text = "\n".join(text)
                upd("processing", 15, f"文本文件读取完成（{len(text)}字）...")
            elif src["type"] == "text":
                # text类型：文本存在url字段
                text = src["url"] or ""
                upd("processing", 15, f"已获取文本内容（{len(text)}字）...")
            elif src["type"] == "url":
                # url类型：需要从URL抓取内容
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    upd("processing", 10, "正在从URL抓取内容...")
                    text = loop.run_until_complete(extract_text_from_url(src["url"]))
                    upd("processing", 15, f"URL内容获取完成（{len(text)}字）...")
                finally:
                    loop.close()
            elif src["url"]:
                # book类型但没有file_path，有url字段——尝试当作URL处理
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    upd("processing", 10, "正在从URL抓取内容...")
                    text = loop.run_until_complete(extract_text_from_url(src["url"]))
                    upd("processing", 15, f"URL内容获取完成（{len(text)}字）...")
                finally:
                    loop.close()
            else:
                # 兜底：尝试从素材库获取内容
                mat_rows = conn.execute("SELECT content FROM materials WHERE source_id=%s LIMIT 1", (source_id,)).fetchall()
                if mat_rows:
                    text = " ".join([m["content"] for m in mat_rows])
                    upd("processing", 15, f"从素材库获取内容（{len(text)}字）...")
                else:
                    upd("error", 0, "无法获取书籍内容", error_msg="no content found")
                    return
        else:
            upd("error", 0, "缺少书籍内容", error_msg="no source")
            return

        if not text or len(text.strip()) < 50:
            print(f"[DEBUG] text too short: len={len(text) if text else 0}, first 100 chars: {text[:100] if text else 'empty'}")
            # 文本太短，尝试从素材库获取内容作为兜底
            if source_id:
                mat_rows = conn.execute("SELECT content FROM materials WHERE source_id=%s", (source_id,)).fetchall()
                print(f"[DEBUG] materials from DB: {len(mat_rows)} rows")
                if mat_rows:
                    text = " ".join([m["content"] for m in mat_rows])
                    upd("processing", 15, f"从素材库获取内容（{len(text)}字）...")
            if not text or len(text.strip()) < 50:
                upd("error", 0, "书籍文本太少，无法生成", error_msg="text too short")
                return

        if not book_name:
            book_name = "本书"

        # 第一步：策划
        upd("processing", 20, f"第一步：分析《{book_name}》，生成{episode_count}期策划...")
        plan = pushutree_plan(book_name, text, episode_count, style)
        if not plan:
            upd("error", 0, "策划生成失败，请重试", error_msg="plan empty")
            return
        upd("processing", 35, f"策划完成，共{len(plan)}期，开始撰写...", plan=plan)

        # 第二步+第三步：逐期撰写+精修
        episodes = []
        for i, ep in enumerate(plan):
            ep_no = ep.get("ep_no", i + 1)
            title = ep.get("title", f"第{ep_no}期")

            progress = 35 + int((i / len(plan)) * 55)
            upd("processing", progress, f"撰写第{ep_no}/{len(plan)}期：{title}...")

            try:
                draft = pushutree_write(book_name, text, ep, style)
                upd("processing", progress + 3, f"精修第{ep_no}期...")
                final = pushutree_polish(book_name, draft, ep)
            except Exception as e:
                final = f"（生成失败：{e}）"

            episodes.append({
                "ep_no": ep_no,
                "title": title,
                "content": final,
                "pain_point": ep.get("pain_point", ""),
                "angle": ep.get("angle", ""),
            })
            upd("processing", progress + 5, f"第{ep_no}期完成", episodes=episodes)

        upd("done", 100, f"全部{len(episodes)}期生成完毕！", episodes=episodes)

    except Exception as e:
        import traceback
        upd("error", 0, f"生成失败：{e}", error_msg=traceback.format_exc())
    finally:
        conn.close()


# ─── Request Models ──────────────────────────────────────────────────

class PushutreeRequest(BaseModel):
    source_id: str = ""           # 可选：已有书籍ID
    book_name: str = ""           # 可选：直接传书名（独立模式）
    book_text: str = ""           # 可选：直接传书籍文本（独立模式）
    episode_count: int = 8
    platform: str = "抖音/视频号"
    style: str = "犀利、接地气、直击痛点"


# ─── Routes ─────────────────────────────────────────────────────────

@router.post("/api/pushutree/create")
def create_pushutree(req: PushutreeRequest):
    """创建朴树之道分享任务
    支持两种模式：
    1. 书库模式：传 source_id（任意状态的书籍都可以，不必须提炼完成）
    2. 独立模式：传 book_name + book_text（直接输入书名和文本）
    """
    conn = get_db()

    # 确定来源信息
    if req.source_id:
        src = conn.execute("SELECT * FROM sources WHERE id=%s", (req.source_id,)).fetchone()
        if not src:
            conn.close()
            raise HTTPException(404, "书籍不存在")
        source_id = req.source_id
        source_title = src["title"]
    elif req.book_name:
        # 独立模式：没有对应的 sources 记录，用 book_name 作标题，source_id 为空
        source_id = ""
        source_title = req.book_name
    else:
        conn.close()
        raise HTTPException(400, "请提供书籍ID或书名")

    script_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO scripts VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (script_id, source_id, source_title,
         req.episode_count, req.platform, req.style,
         "pending", 0, "等待生成...",
         "[]", "[]", None, now(), now())
    )
    conn.commit()
    conn.close()

    # 后台异步执行
    threading.Thread(
        target=run_pushutree_task,
        args=(script_id, source_id, req.episode_count, req.platform, req.style, req.book_text, req.book_name),
        daemon=True
    ).start()

    return {"script_id": script_id, "status": "pending"}


@router.get("/api/pushutree/{script_id}")
def get_pushutree(script_id: str):
    """查询朴树之道任务进度和结果"""
    conn = get_db()
    row = conn.execute("SELECT * FROM scripts WHERE id=%s", (script_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "任务不存在")
    d = dict(row)
    d["episodes"] = json.loads(d["episodes"] or "[]")
    d["plan"] = json.loads(d["plan"] or "[]")
    return _clean_surrogate(d)


@router.get("/api/pushutree")
def list_pushutree(source_id: str = None):
    """获取所有朴树之道系列（可按书籍过滤）"""
    conn = get_db()
    if source_id:
        rows = conn.execute(
            "SELECT * FROM scripts WHERE source_id=%s ORDER BY created_at DESC",
            (source_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM scripts ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["episodes"] = json.loads(d["episodes"] or "[]")
        d["plan"] = json.loads(d["plan"] or "[]")
        result.append(d)
    return _clean_surrogate(result)


@router.delete("/api/pushutree/{script_id}")
def delete_pushutree(script_id: str):
    """删除朴树之道系列"""
    conn = get_db()
    conn.execute("DELETE FROM scripts WHERE id=%s", (script_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/api/pushutree/upload-and-create")
async def pushutree_upload_and_create(
    file: UploadFile = File(None),
    book_name: str = Form(...),
    book_text: str = Form(""),
    episode_count: int = Form(8),
    platform: str = Form("抖音/视频号"),
    style: str = Form("犀利、接地气、直击痛点"),
):
    """朴树之道独立上传入口：
    直接上传PDF或填入书名+文本，不依赖书库，立即生成系列分享文案。
    """
    text = book_text

    # 如果上传了PDF，提取文本
    if file and file.filename:
        file_id = str(uuid.uuid4())
        save_path = UPLOAD_DIR / f"pt_{file_id}_{file.filename}"
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        try:
            extracted, _, _ = extract_text_from_pdf(str(save_path))
            text = extracted
        except Exception as e:
            raise HTTPException(500, f"PDF解析失败：{e}")

    if not text or len(text.strip()) < 50:
        raise HTTPException(400, "请上传PDF文件或填入书籍文本（至少50字）")

    if not book_name.strip():
        raise HTTPException(400, "请填写书名")

    # 创建 script 记录
    conn = get_db()
    script_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO scripts VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (script_id, "", book_name.strip(),
         episode_count, platform, style,
         "pending", 0, "等待生成...",
         "[]", "[]", None, now(), now())
    )
    conn.commit()
    conn.close()

    # 后台异步执行
    threading.Thread(
        target=run_pushutree_task,
        args=(script_id, "", episode_count, platform, style, text, book_name.strip()),
        daemon=True
    ).start()

    return {"script_id": script_id, "status": "pending", "book_name": book_name.strip()}
