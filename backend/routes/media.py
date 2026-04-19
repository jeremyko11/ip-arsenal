# -*- coding: utf-8 -*-
"""routes/media.py - 媒体爬虫 / MediaCrawler 相关 API"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import httpx
from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

from config import BASE_DIR, DB_PATH
from db import get_db, now

router = APIRouter(tags=["media"])

# ═══════════════════════════════════════════════════════════════════════════
# MediaCrawler 数据目录配置
# ═══════════════════════════════════════════════════════════════════════════

_MEDIA_CRAWLER_LOCAL_DATA = BASE_DIR / "media_crawler" / "data"
_CONFIG_PATH = BASE_DIR / "config.json"
if _CONFIG_PATH.exists():
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _cfg = json.load(f)
            _ext_path = _cfg.get("media_crawler", {}).get("data_dir", "")
            MEDIA_CRAWLER_DATA_DIR = Path(_ext_path) if _ext_path else _MEDIA_CRAWLER_LOCAL_DATA
    except Exception:
        MEDIA_CRAWLER_DATA_DIR = _MEDIA_CRAWLER_LOCAL_DATA
else:
    MEDIA_CRAWLER_DATA_DIR = _MEDIA_CRAWLER_LOCAL_DATA

# 平台 ID → 中文名映射
PLATFORM_NAMES = {
    "douyin": "抖音",
    "xhs": "小红书",
    "weibo": "微博",
    "kuaishou": "快手",
    "bili": "B站",
    "tieba": "贴吧",
    "zhihu": "知乎",
}

MEDIACRAWLER_BASE = "http://localhost:8080"

# ═══════════════════════════════════════════════════════════════════════════
# 请求模型
# ═══════════════════════════════════════════════════════════════════════════


class MediaImportRequest(BaseModel):
    records: List[dict]  # 每条记录包含 platform, content, metadata


# ═══════════════════════════════════════════════════════════════════════════
# 媒体数据接入 API（本地文件方式）
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/api/media/platforms")
def list_media_platforms():
    """返回 MediaCrawler 已采集的平台列表"""
    if not MEDIA_CRAWLER_DATA_DIR.exists():
        return {"platforms": []}

    platforms = []
    for subdir in MEDIA_CRAWLER_DATA_DIR.iterdir():
        if subdir.is_dir() and subdir.name != "wechat-output":
            pid = subdir.name
            platforms.append({
                "id": pid,
                "name": PLATFORM_NAMES.get(pid, pid),
                "path": str(subdir),
            })

    return {"platforms": platforms}


@router.get("/api/media/files")
def list_media_files(platform: str = ""):
    """返回指定平台的数据文件列表"""
    if not platform:
        return {"files": []}

    platform_dir = MEDIA_CRAWLER_DATA_DIR / platform
    if not platform_dir.exists():
        return {"files": []}

    files = []
    for subdir in platform_dir.iterdir():
        if subdir.is_dir():
            for f in subdir.iterdir():
                if f.suffix in (".json", ".jsonl", ".csv"):
                    files.append({
                        "name": f.name,
                        "path": str(f.relative_to(MEDIA_CRAWLER_DATA_DIR)).replace("\\", "/"),
                        "size": f.stat().st_size,
                    })

    # 也检查顶层文件
    for f in platform_dir.iterdir():
        if f.is_file() and f.suffix in (".json", ".jsonl", ".csv"):
            files.append({
                "name": f.name,
                "path": str(f.relative_to(MEDIA_CRAWLER_DATA_DIR)).replace("\\", "/"),
                "size": f.stat().st_size,
            })

    return {"files": files}


@router.get("/api/media/data")
def get_media_data(platform: str = "", file: str = "", offset: int = 0, limit: int = 20):
    """读取指定文件的数据，支持分页"""
    if not platform or not file:
        return {"records": [], "total": 0, "offset": offset, "limit": limit}

    file_path = MEDIA_CRAWLER_DATA_DIR / file
    if not file_path.exists():
        return {"records": [], "total": 0, "offset": offset, "limit": limit}

    records = []
    try:
        if file_path.suffix == ".jsonl":
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            total = len(lines)
            for line in lines[offset:offset + limit]:
                try:
                    records.append(json.loads(line))
                except:
                    pass
        elif file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                total = len(data)
                records = data[offset:offset + limit]
            else:
                total = 1
                records = [data] if offset == 0 else []
    except Exception as e:
        return {"records": [], "total": 0, "offset": offset, "limit": limit, "error": str(e)}

    return {"records": records, "total": total, "offset": offset, "limit": limit}


@router.post("/api/media/import")
def import_media_records(req: MediaImportRequest):
    """将选中的 MediaCrawler 记录导入到 ip-arsenal 素材库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    imported = 0
    failed = 0
    today = datetime.now().strftime("%Y-%m-%d")

    for record in req.records:
        try:
            platform = record.get("platform", "unknown")
            content = record.get("content", "") or record.get("desc", "") or ""
            if not content:
                failed += 1
                continue

            metadata = record.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            # 从 record 直接提取有用字段放入 metadata
            for key in ("nickname", "liked_count", "comment_count", "share_count",
                        "collect_count", "user_id", "avatar", "ip_location",
                        "source_keyword", "create_time", "note_id", "aweme_id",
                        "note_url", "aweme_url"):
                if key in record and key not in metadata:
                    metadata[key] = record[key]

            source_id = f"media_crawler_{platform}_{today}"

            # 插入 materials 表
            mid = str(uuid.uuid4())
            c.execute("""
                INSERT INTO materials (id, source_id, category, content, metadata, tags, platform, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                mid,
                source_id,
                "topic",  # 默认分类，可后续 AI 重新分类
                content,
                json.dumps(metadata, ensure_ascii=False),
                "[]",
                platform,
                datetime.now().isoformat(),
            ))
            imported += 1
        except Exception as e:
            failed += 1
            print(f"[MediaImport] 导入失败: {e}")

    conn.commit()
    conn.close()

    return {"imported": imported, "failed": failed}


# ═══════════════════════════════════════════════════════════════════════════
# MediaCrawler API 代理（方案B：深度融合）
# ip-arsenal 后端作为网关，转发请求到 MediaCrawler (port 8080)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/api/mediacrawler/health")
async def mc_health():
    """转发到 MediaCrawler /api/health"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{MEDIACRAWLER_BASE}/api/health")
        return r.json()


@router.get("/api/mediacrawler/config/platforms")
async def mc_config_platforms():
    """转发到 MediaCrawler /api/config/platforms"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{MEDIACRAWLER_BASE}/api/config/platforms")
        return r.json()


@router.get("/api/mediacrawler/config/options")
async def mc_config_options():
    """转发到 MediaCrawler /api/config/options"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{MEDIACRAWLER_BASE}/api/config/options")
        return r.json()


@router.post("/api/mediacrawler/crawler/start")
async def mc_crawler_start(req: dict):
    """转发到 MediaCrawler /api/crawler/start"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{MEDIACRAWLER_BASE}/api/crawler/start", json=req)
        return r.json()


@router.post("/api/mediacrawler/crawler/stop")
async def mc_crawler_stop():
    """转发到 MediaCrawler /api/crawler/stop"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{MEDIACRAWLER_BASE}/api/crawler/stop")
        return r.json()


@router.get("/api/mediacrawler/crawler/status")
async def mc_crawler_status():
    """转发到 MediaCrawler /api/crawler/status"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{MEDIACRAWLER_BASE}/api/crawler/status")
        return r.json()


@router.get("/api/mediacrawler/crawler/logs")
async def mc_crawler_logs(limit: int = 100):
    """转发到 MediaCrawler /api/crawler/logs"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{MEDIACRAWLER_BASE}/api/crawler/logs", params={"limit": limit})
        return r.json()


@router.get("/api/mediacrawler/data/files")
def mc_data_files(platform: str = ""):
    """返回本地 MediaCrawler 数据目录的文件（不走代理，避免跨域问题）"""
    return list_media_files(platform=platform)


@router.get("/api/mediacrawler/data/files/{file_path:path}")
def mc_data_file_preview(file_path: str, preview: bool = True, limit: int = 50):
    """从本地 MediaCrawler 数据目录读取文件内容"""
    # file_path 格式：douyin/jsonl/search_contents_2026-03-30.jsonl
    fp = MEDIA_CRAWLER_DATA_DIR / file_path
    if not fp.exists():
        return {"records": [], "total": 0, "offset": 0, "limit": limit, "error": "file not found: " + str(fp)}

    if preview:
        # 直接读取文件内容，避免调用 get_media_data 的 platform/file 拼接逻辑
        records = []
        total = 0
        try:
            if fp.suffix == ".jsonl":
                with open(fp, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                total = len(lines)
                for line in lines[0:limit]:
                    try:
                        records.append(json.loads(line))
                    except:
                        pass
            elif fp.suffix == ".json":
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    total = len(data)
                    records = data[0:limit]
                else:
                    total = 1
                    records = [data]
        except Exception as e:
            return {"records": [], "total": 0, "offset": 0, "limit": limit, "error": str(e)}
        return {"records": records, "total": total, "offset": 0, "limit": limit}
    else:
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}


@router.websocket("/api/mediacrawler/ws/status")
async def mc_ws_status(websocket: WebSocket):
    """WebSocket 转发：/api/ws/status"""
    await websocket.accept()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("GET", f"{MEDIACRAWLER_BASE}/api/ws/status") as resp:
                async for text in resp.aiter_text():
                    if text:
                        await websocket.send_text(text)
    except Exception as e:
        print(f"[mc_ws_status] error: {e}")
    finally:
        await websocket.close()
