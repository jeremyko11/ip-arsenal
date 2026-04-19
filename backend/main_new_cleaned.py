# ─── UTF-8 编码 ──────────────────────────────────────────────────────────
import sys, os
os.environ.setdefault('PYTHONUTF8', '1')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

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

# ─── 路由模块 ─────────────────────────────────────────────────────────
from routes import sources, materials, wechat, pushutree, media, misc

# ─── 标准库（供路由和 process_source_task 使用）──────────────────────
import json, sqlite3, uuid, time, asyncio, base64, io, threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ─── FastAPI 应用 ────────────────────────────────────────────────────
from fastapi.responses import ORJSONResponse
try:
    import orjson
    class _UnicodeJSONResponse(ORJSONResponse):
        pass
    _json_response_class = _UnicodeJSONResponse
except ImportError:
    from fastapi.responses import Response as _Resp
    class _UnicodeJSONResponse(_Resp):
        media_type = 'application/json; charset=utf-8'
        def render(self, content) -> bytes:
            return json.dumps(content, ensure_ascii=False, allow_nan=False).encode('utf-8')
    _json_response_class = _UnicodeJSONResponse

app = FastAPI(title='IP Arsenal API', version='1.0.0', default_response_class=_json_response_class)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

# ─── 路由注册 ─────────────────────────────────────────────────────────
app.include_router(sources.router)
app.include_router(materials.router)
app.include_router(wechat.router)
app.include_router(pushutree.router)
app.include_router(media.router)
app.include_router(misc.router)

@app.on_event('startup')
def on_startup():
    _start_workers()
    _recover_stuck_tasks()

# ─── Worker 队列引用（已迁移到 tasks.py）────────────────────────────
from tasks import _task_queue, WORKER_COUNT, TASK_MAX_SECONDS, _worker_threads, _worker_heartbeats
from tasks import _worker_loop, _spawn_worker, _watchdog_loop

# ─── 以下为占位说明 ──────────────────────────────────────────────────
# config.py    → 常量、AI客户端初始化
# db.py        → 数据库初始化 (init_db, migrate_db, get_db, now)
# ai.py        → AI调用链 (ai_extract)
# tasks.py     → Worker线程池 (enqueue_task, _start_workers, _recover_stuck_tasks)
# extraction.py → PDF/EPUB/TXT/DOCX/URL 文本提取
# prompts.py   → 提示词构建 (build_prompt, parse_materials, EXTRACT_MODES)


def parse_materials(source_id: str, raw_content: str) -> List[dict]:
    """将AI输出解析为结构化素材条目"""
    materials = []
    now_str = now()

    lines = raw_content.split("\n")
    current_cat = "quote"
    current_block = []

    cat_map = {
        "第一部分": "quote",
        "金句弹药库": "quote",
        "第二部分": "case",
        "故事与案例": "case",
        "第三部分": "viewpoint",
        "认知与观点": "viewpoint",
        "第四部分": "action",
        "实操与行动": "action",
        "第五部分": "topic",
        "IP选题映射": "topic",
        "书籍综合评级": "rating",
    }

    def flush_block():
        nonlocal current_block
        text = "\n".join(current_block).strip()
        if text and len(text) > 10:
            meta = {}
            # 提取风险标签
            for line in current_block:
                if "风险标签" in line:
                    if "✅安全" in line: meta["risk"] = "safe"
                    elif "⚠️需语境" in line: meta["risk"] = "context"
                    elif "❌禁用" in line: meta["risk"] = "forbidden"
                if "爆点场景" in line:
                    if "🔥爆款" in line: meta["scene"] = "viral"
                    elif "💡治愈" in line: meta["scene"] = "heal"
                    elif "📚深度" in line: meta["scene"] = "deep"
                if "改写成本" in line:
                    if "⚡0成本" in line: meta["cost"] = "zero"
                    elif "✂️中成本" in line: meta["cost"] = "mid"
                    elif "🛠️高成本" in line: meta["cost"] = "high"
                if "时效熔断" in line:
                    if "✅长效" in line: meta["timeliness"] = "long"
                    elif "⚠️需更新" in line: meta["timeliness"] = "update"
                    elif "❌已过期" in line: meta["timeliness"] = "expired"

            materials.append({
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "category": current_cat,
                "content": text,
                "metadata": json.dumps(meta, ensure_ascii=False),
                "tags": "[]",
                "platform": "[]",
                "use_count": 0,
                "is_starred": 0,
                "created_at": now_str,
            })
        current_block = []

    for line in lines:
        # 检测分类标题
        new_cat = None
        for key, cat in cat_map.items():
            if key in line and ("##" in line or "【" in line):
                new_cat = cat
                break

        if new_cat:
            flush_block()
            current_cat = new_cat
        else:
            # 金句单条切割（以 > 开头的引用块）
            if current_cat == "quote" and line.startswith("> ") and "风险标签" not in line and "爆点场景" not in line and "改写成本" not in line and "时效熔断" not in line:
                if current_block:
                    flush_block()
                current_block = [line]
            elif current_cat == "quote" and line.startswith("> "):
                current_block.append(line)
            # 案例/观点/行动 — 以 ** 开头新条目
            elif current_cat in ("case","viewpoint","action","topic") and line.startswith("**") and line.endswith("**"):
                flush_block()
                current_block = [line]
            elif current_cat in ("case","viewpoint","action","topic") and line.startswith("- ") and current_block:
                current_block.append(line)
            elif current_cat == "topic" and line.strip().startswith(("1.","2.","3.","4.","5.","6.","7.","8.","9.","10.","11.","12.","13.","14.","15.")):
                flush_block()
                current_block = [line]
            elif current_block:
                current_block.append(line)

    flush_block()
    return materials


# ─── process_source_task 和 process_source_task_smart 已迁移到 services/process.py ─────
# ─── API 路由已拆分到 routes/ 目录（sources.py / materials.py / wechat.py / pushutree.py / media.py / misc.py）─────


    import uvicorn, sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    print("IP Arsenal starting on http://localhost:8766")
    print(f"[SmartExtraction] 智能提取模块: {'可用' if _SMART_EXTRACTION_AVAILABLE else '不可用'}")
    # Worker 线程和任务恢复由 @app.on_event("startup") 统一处理
    uvicorn.run("main:app", host="0.0.0.0", port=8766, reload=False)

