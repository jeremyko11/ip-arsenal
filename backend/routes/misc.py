# -*- coding: utf-8 -*-
"""routes/misc.py - 创作管理 / 跨书整合 / 前端 Serve 路由"""
from __future__ import annotations

import json, uuid
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ─── 核心模块导入 ─────────────────────────────────────────────────────
from config import BASE_DIR, FRONT_DIR
from db import get_db, now
from ai import ai_extract

router = APIRouter(tags=["misc"])

# ─── 缓存 ─────────────────────────────────────────────────────────────
from cache import get as _cache_get, set as _cache_set, CACHE_KEYS

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

# ═══════════════════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════════════════


class SaveCreationRequest(BaseModel):
    title: str
    content: str
    platform: str = ""
    source_ids: list = []
    material_ids: list = []


class CrossIntegrateRequest(BaseModel):
    content: str          # 用户输入的素材拼合内容（多本书素材拼在一起）
    mode: str = "主题关联"  # 发现主题关联 / 生成系列策划 / 提炼思维模型


# ═══════════════════════════════════════════════════════════════════════════
# 创作管理 API
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/api/creations")
def save_creation(req: SaveCreationRequest):
    cid = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO creations VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (cid, req.title, req.content,
         json.dumps(req.source_ids), json.dumps(req.material_ids),
         req.platform, now(), now())
    )
    conn.commit()
    conn.close()
    return {"id": cid}


@router.get("/api/creations")
def list_creations(q: str = ""):
    conn = get_db()
    sql = "SELECT * FROM creations"
    params = []
    if q:
        sql += " WHERE title LIKE %s OR content LIKE %s"
        params = [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY updated_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return _clean_surrogate([dict(r) for r in rows])


# ═══════════════════════════════════════════════════════════════════════════
# 跨书整合 API
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/api/studio/cross-integrate")
def cross_integrate(req: CrossIntegrateRequest):
    """
    跨书整合：对来自多本书的素材进行跨书深度分析。
    三种模式：
      - 主题关联：发现多本书共同的深层规律与底层逻辑
      - 系列策划：基于共同主题生成可执行的系列内容策划
      - 思维模型：从多本书中提炼可复用的思维模型框架
    """
    mode_prompts = {
        "主题关联": """你是一位顶级知识整合专家。
用户输入了来自多本不同书籍的素材片段，请完成以下分析：

【任务：发现跨书主题关联】

1. **共同主题识别**（3-5个）
   - 找出这些素材中反复出现的核心主题词或概念
   - 每个主题用一句话点明其在所有书中的共同表达方式

2. **底层规律提炼**
   - 这些书在某个更深的层面上，都在说同一件事是什么？
   - 用"它们都在说：……"的句式表达

3. **视角差异**
   - 不同书从什么不同角度切入这个共同主题？（一句话概括各书视角）

4. **IP创作价值**
   - 基于这个跨书共同主题，可以做什么内容（一句话给出方向）

输出格式：直接按上述4个标题输出，不要废话，不要总结段落。""",

        "系列策划": """你是一位顶级内容策划专家，擅长打造系列化IP内容。
用户输入了来自多本书的素材，请基于这些素材策划一套系列内容。

【任务：生成系列内容策划】

1. **系列主题**
   - 系列名称（5-10字，有记忆点）
   - 一句话定位（这个系列为谁解决什么问题）

2. **系列结构**（5-8期）
   - 每期标题（能独立传播，又形成系列感）
   - 每期核心观点（一句话）
   - 对应使用哪本书的哪个核心素材

3. **推送节奏建议**
   - 建议发布频率和顺序逻辑（为什么这样排）

4. **爆款切入点**
   - 哪一期最适合作为首发（理由）

直接输出策划内容，不要有任何前言和废话。""",

        "思维模型": """你是一位知识萃取专家，擅长从书籍素材中提炼可复用的思维框架。
用户输入了多本书的核心素材，请从中提炼思维模型。

【任务：提炼跨书思维模型】

1. **核心模型命名**
   - 给这个思维模型起一个好记的名字（可以是"XX法则""XX模型""XX框架"等）
   - 一句话说明这个模型解决什么问题

2. **模型结构**
   - 用2-4个步骤或维度描述这个模型的运作逻辑
   - 每个步骤/维度：名称 + 一句话解释 + 来自哪本书的什么概念

3. **适用场景**
   - 这个思维模型在哪3个场景下最有用？（具体场景，不要抽象）

4. **记忆口诀**（可选）
   - 如果能用一句顺口的话记住这个模型，是什么？

5. **内容创作切入**
   - 用这个思维模型，可以写什么选题？（给出3个具体标题）

直接输出，不要废话，要让人看完立刻能用。"""
    }

    system_prompt = f"""你是一位顶级IP内容创作专家，专注于职场认知升级、人性洞察和个人成长破局三大方向。

{mode_prompts.get(req.mode, mode_prompts['主题关联'])}

【去AI化规则——必须执行】
- 禁止"综上所述""值得注意""深刻启示""引人深省""不言而喻"等AI高频词
- 用真实直接的语言，有判断有态度，不说官话
- 说具体的，不说抽象的"""

    user_prompt = f"以下是来自多本书的素材内容，请按要求分析：\n\n{req.content}"

    try:
        result, model_used = ai_extract(system_prompt, user_prompt, max_tokens=3000, temperature=0.75)
        return _clean_surrogate({"result": result, "model": model_used, "mode": req.mode})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"跨书整合失败：{str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# 其他杂项 API
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/api/stats")
def get_stats():
    """获取统计信息：来源总数、素材总数、星标数、分类统计（缓存5分钟）"""
    # 尝试从缓存获取
    cached = _cache_get(CACHE_KEYS["stats"])
    if cached is not None:
        return cached
    conn = get_db()
    sources_total = conn.execute("SELECT COUNT(*) FROM sources WHERE status='done'").fetchone()['count']
    materials_total = conn.execute("SELECT COUNT(*) FROM materials").fetchone()['count']
    cat_rows = conn.execute(
        "SELECT category, COUNT(*) FROM materials GROUP BY category"
    ).fetchall()
    cat_counts = {row['category']: row['count'] for row in cat_rows}
    starred = conn.execute("SELECT COUNT(*) FROM materials WHERE is_starred=1").fetchone()['count']
    conn.close()
    result = {
        "sources": sources_total,
        "materials": materials_total,
        "starred": starred,
        "by_category": cat_counts,
    }
    _cache_set(CACHE_KEYS["stats"], result, ttl=300)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 前端静态文件 Serve（必须是最后一个路由）
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/{path:path}")
async def serve_frontend(path: str):
    """前端 SPA 路由：所有未匹配路径返回 index.html"""
    index_path = FRONT_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(404, "前端未找到")
