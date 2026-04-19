# -*- coding: utf-8 -*-
"""routes/ip_tools.py - IP打造工具：风格学习/话题预告/平台适配/差异化检测"""
from __future__ import annotations

import json
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import IP_DIRECTION
from db import get_db, now
from ai import ai_extract

router = APIRouter(tags=["ip_tools"])

# ─── 辅助函数 ───────────────────────────────────────────────────────────
_SURROGATE_RANGE = {i: None for i in range(0xD800, 0xE000)}

def _clean(obj):
    if isinstance(obj, str):
        return obj.translate(_SURROGATE_RANGE)
    elif isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean(item) for item in obj]
    return obj

# ─── Request Models ──────────────────────────────────────────────────

class StyleProfileRequest(BaseModel):
    name: str
    samples: List[str] = []
    keywords: List[str] = []
    banned_words: List[str] = []
    tone: str = ""
    char_count_range: str = ""

class WeeklyPlanRequest(BaseModel):
    week_start: str
    monday: str = ""
    tuesday: str = ""
    wednesday: str = ""
    thursday: str = ""
    friday: str = ""
    saturday: str = ""
    sunday: str = ""
    status: str = "planning"

class PlatformAdaptRequest(BaseModel):
    content: str
    style_id: Optional[str] = None
    target_platforms: List[str] = ["公众号"]

class DiffCheckRequest(BaseModel):
    content: str
    topic: str = ""

class TopicSplitRequest(BaseModel):
    content: str
    count: int = 10

# ═══════════════════════════════════════════════════════════════════════════
# 风格学习 API
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/style-profiles")
def create_style_profile(req: StyleProfileRequest):
    """创建风格配置"""
    pid = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO style_profiles VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (pid, req.name, json.dumps(req.samples), json.dumps(req.keywords),
         json.dumps(req.banned_words), req.tone, req.char_count_range, now(), now())
    )
    conn.commit()
    conn.close()
    return {"id": pid, "name": req.name}

@router.get("/api/style-profiles")
def list_style_profiles():
    """获取所有风格配置"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM style_profiles ORDER BY created_at DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["samples"] = json.loads(d.get("samples") or "[]")
        d["keywords"] = json.loads(d.get("keywords") or "[]")
        d["banned_words"] = json.loads(d.get("banned_words") or "[]")
        result.append(d)
    return _clean(result)

@router.get("/api/style-profiles/{pid}")
def get_style_profile(pid: str):
    """获取单个风格配置"""
    conn = get_db()
    row = conn.execute("SELECT * FROM style_profiles WHERE id=%s", (pid,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "风格配置不存在")
    d = dict(row)
    d["samples"] = json.loads(d.get("samples") or "[]")
    d["keywords"] = json.loads(d.get("keywords") or "[]")
    d["banned_words"] = json.loads(d.get("banned_words") or "[]")
    return _clean(d)

@router.delete("/api/style-profiles/{pid}")
def delete_style_profile(pid: str):
    """删除风格配置"""
    conn = get_db()
    conn.execute("DELETE FROM style_profiles WHERE id=%s", (pid,))
    conn.commit()
    conn.close()
    return {"ok": True}

# ═══════════════════════════════════════════════════════════════════════════
# 话题预告/周计划 API
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/weekly-plans")
def create_weekly_plan(req: WeeklyPlanRequest):
    """创建周计划"""
    wid = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO weekly_plans VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (wid, req.week_start, req.monday, req.tuesday, req.wednesday,
         req.thursday, req.friday, req.saturday, req.sunday, req.status, now(), now())
    )
    conn.commit()
    conn.close()
    return {"id": wid, "week_start": req.week_start}

@router.get("/api/weekly-plans")
def list_weekly_plans():
    """获取所有周计划"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM weekly_plans ORDER BY week_start DESC").fetchall()
    conn.close()
    return _clean([dict(r) for r in rows])

@router.get("/api/weekly-plans/current")
def get_current_week_plan():
    """获取当前周的的计划"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.strftime("%Y-%m-%d")
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM weekly_plans WHERE week_start=%s", (week_start,)
    ).fetchone()
    conn.close()
    if not row:
        # 自动创建空计划
        wid = str(uuid.uuid4())
        conn = get_db()
        conn.execute(
            "INSERT INTO weekly_plans VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (wid, week_start, "", "", "", "", "", "", "", "planning", now(), now())
        )
        conn.commit()
        conn.close()
        return _clean({"id": wid, "week_start": week_start, "monday": "", "tuesday": "", "wednesday": "", "thursday": "", "friday": "", "saturday": "", "sunday": "", "status": "planning"})
    return _clean(dict(row))

@router.put("/api/weekly-plans/{wid}")
def update_weekly_plan(wid: str, req: WeeklyPlanRequest):
    """更新周计划"""
    conn = get_db()
    conn.execute(
        "UPDATE weekly_plans SET monday=%s, tuesday=%s, wednesday=%s, thursday=%s, friday=%s, saturday=%s, sunday=%s, status=%s, updated_at=%s WHERE id=%s",
        (req.monday, req.tuesday, req.wednesday, req.thursday, req.friday, req.saturday, req.sunday, req.status, now(), wid)
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@router.delete("/api/weekly-plans/{wid}")
def delete_weekly_plan(wid: str):
    """删除周计划"""
    conn = get_db()
    conn.execute("DELETE FROM weekly_plans WHERE id=%s", (wid,))
    conn.commit()
    conn.close()
    return {"ok": True}

@router.post("/api/weekly-plans/generate")
def generate_weekly_plan():
    """AI 自动生成本周选题计划"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.strftime("%Y-%m-%d")

    system_prompt = f"""你是一个资深的内容策划专家，擅长为个人IP打造系列选题。

IP方向：{IP_DIRECTION}
目标：生成一周7天的内容选题，每天一个主题，形成系列感。

要求：
1. 每个选题要有差异化，覆盖不同角度（情绪共鸣/认知升级/实操干货/故事案例等）
2. 考虑时效性，结合近期热点
3. 每期标题要吸引人，有记忆点
4. 直接输出，不要废话"""

    user_prompt = f"""请为{week_start}这一周生成7天每天的内容选题计划。

输出格式（严格按这个格式）：
周一：【选题标题】- 30字内的一句话描述
周二：【选题标题】- 30字内的一句话描述
周三：【选题标题】- 30字内的一句话描述
周四：【选题标题】- 30字内的一句话描述
周五：【选题标题】- 30字内的一句话描述
周六：【选题标题】- 30字内的一句话描述
周日：【选题标题】- 30字内的一句话描述

直接输出7行，不要其他文字。"""

    try:
        result, model_used = ai_extract(system_prompt, user_prompt, max_tokens=2000, temperature=0.8)
        # 解析结果填充到各天
        lines = [l.strip() for l in result.strip().split("\n") if l.strip()]
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        plan = {d: "" for d in days}
        for i, line in enumerate(lines[:7]):
            if i < 7:
                plan[days[i]] = line

        # 保存或更新
        conn = get_db()
        existing = conn.execute("SELECT id FROM weekly_plans WHERE week_start=%s", (week_start,)).fetchone()
        if existing:
            wid = existing["id"]
            conn.execute(
                "UPDATE weekly_plans SET monday=%s, tuesday=%s, wednesday=%s, thursday=%s, friday=%s, saturday=%s, sunday=%s, updated_at=%s WHERE id=%s",
                (plan["monday"], plan["tuesday"], plan["wednesday"], plan["thursday"],
                 plan["friday"], plan["saturday"], plan["sunday"], now(), wid)
            )
        else:
            wid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO weekly_plans VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (wid, week_start, plan["monday"], plan["tuesday"], plan["wednesday"],
                 plan["thursday"], plan["friday"], plan["saturday"], plan["sunday"], "planning", now(), now())
            )
        conn.commit()
        conn.close()
        return _clean({"week_start": week_start, "plan": plan, "model": model_used})
    except Exception as e:
        raise HTTPException(500, f"生成失败：{str(e)}")

# ═══════════════════════════════════════════════════════════════════════════
# 平台适配改写 API
# ═══════════════════════════════════════════════════════════════════════════

PLATFORM_HINTS = {
    "公众号": "适合深度长文，有目录结构，金句加粗，适当留白",
    "抖音": "口语化强，前3秒要有钩子，分段简洁，每段一两句话",
    "小红书": "标题党风格，emoji 丰富，干货清单体，结尾有互动问题",
    "知乎": "结构化思考，先说结论，有数据支撑，引用要标注",
    "微博": "140字内，一句话金句配图，热点话题标签",
    "视频号": "口播脚本格式，前3秒留悬念，结尾引导点赞关注",
}

@router.post("/api/rewrite/platform-adapt")
async def platform_adapt(req: PlatformAdaptRequest):
    """一键生成多平台适配内容"""
    if not req.content:
        raise HTTPException(400, "内容不能为空")

    style_profile = None
    if req.style_id:
        conn = get_db()
        row = conn.execute("SELECT * FROM style_profiles WHERE id=%s", (req.style_id,)).fetchone()
        conn.close()
        if row:
            style_profile = dict(row)
            style_profile["samples"] = json.loads(style_profile.get("samples") or "[]")
            style_profile["keywords"] = json.loads(style_profile.get("keywords") or "[]")
            style_profile["banned_words"] = json.loads(style_profile.get("banned_words") or "[]")

    async def adapt_one(platform: str) -> dict:
        """在后台线程中调用 AI"""
        hint = PLATFORM_HINTS.get(platform, "")

        system_parts = [f"""你是一个顶尖的新媒体内容改写专家，擅长将同一内容改写成不同平台风格。
目标平台：{platform}
{hint}

改写要求：
1. 保留核心观点和关键信息
2. 完全适配目标平台的语言风格和格式
3. 长度适中（符合平台用户习惯）"""]

        if style_profile:
            samples = style_profile.get("samples", [])
            if samples:
                system_parts.append(f"\n\n【风格参考样本】\n" + "\n---\n".join(samples[:3]))
            banned = style_profile.get("banned_words", [])
            if banned:
                system_parts.append(f"\n\n【禁用词】{' '.join(banned)}")
            tone = style_profile.get("tone", "")
            if tone:
                system_parts.append(f"\n\n【语气要求】{tone}")

        system_prompt = "\n".join(system_parts)

        loop = asyncio.get_event_loop()
        result, model = await loop.run_in_executor(
            None,
            lambda: ai_extract(system_prompt, req.content, max_tokens=4000, temperature=0.8)
        )
        return {"platform": platform, "content": result, "model": model}

    try:
        tasks = [adapt_one(p) for p in req.target_platforms]
        results = await asyncio.gather(*tasks)
        return _clean({"versions": results, "style_id": req.style_id})
    except Exception as e:
        raise HTTPException(500, f"平台适配失败：{str(e)}")

# ═══════════════════════════════════════════════════════════════════════════
# 差异化检测 API
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/content/diff-check")
async def diff_check(req: DiffCheckRequest):
    """检测内容与同类爆款的差异化程度"""
    topic = req.topic or "同类爆款内容"

    system_prompt = f"""你是一个内容差异化分析专家。

任务：分析以下内容与"{topic}"的差异化程度。

分析维度：
1. 角度差异：切入角度是否独特
2. 表达差异：语言风格是否有辨识度
3. 深度差异：是否有独特洞察
4. 价值差异：是否提供新信息或新视角

请输出：
- 差异化评分（1-10）
- 主要差异点（3条）
- 风险点（同质化风险）
- 优化建议（如何进一步差异化）"""

    try:
        loop = asyncio.get_event_loop()
        result, model = await loop.run_in_executor(
            None,
            lambda: ai_extract(system_prompt, req.content, max_tokens=2000, temperature=0.7)
        )

        import re
        score_match = re.search(r'差异化评分[：:]*\s*(\d+)', result)
        score = int(score_match.group(1)) if score_match else 5

        return _clean({
            "score": score,
            "analysis": result,
            "topic": topic,
            "model": model
        })
    except Exception as e:
        raise HTTPException(500, f"差异化检测失败：{str(e)}")

# ═══════════════════════════════════════════════════════════════════════════
# 话题裂变 API
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/content/topic-split")
async def topic_split(req: TopicSplitRequest):
    """一个核心观点自动裂变成多个角度"""
    count = req.count
    content = req.content

    system_prompt = f"""你是一个爆款标题生成专家。

任务：将以下核心观点裂变成{count}个不同切入角度的标题/开头。

要求：
1. 覆盖不同情绪类型：焦虑型/治愈型/认知型/行动型/共鸣型
2. 每个标题要吸引人，有钩子
3. 角度要有差异，不能同质化
4. 直接输出，不要废话

输出格式（每行一个）：
标题1 | 情绪类型 | 一句话说明切入点"""

    try:
        loop = asyncio.get_event_loop()
        result, model = await loop.run_in_executor(
            None,
            lambda: ai_extract(system_prompt, content, max_tokens=3000, temperature=0.9)
        )

        lines = [l.strip() for l in result.strip().split("\n") if l.strip() and "|" in l]
        topics = []
        for line in lines[:count]:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                topics.append({
                    "title": parts[0],
                    "emotion": parts[1],
                    "description": parts[2] if len(parts) > 2 else ""
                })

        return _clean({"topics": topics, "model": model})
    except Exception as e:
        raise HTTPException(500, f"话题裂变失败：{str(e)}")
