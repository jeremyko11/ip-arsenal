# -*- coding: utf-8 -*-
"""
IP Arsenal - 提示词模块
AI 提炼提示词构建、素材解析
"""
import json
import re
import uuid
from typing import List

from config import IP_DIRECTION, MAX_PROMPT_TEXT_CHARS
from db import now


# ── 代理字符清理 ───────────────────────────────────────────────────
# 移除 Python 代理字符范围 (U+D800 到 U+DFFF)，JSON 不支持这些字符
_SURROGATE_RANGE = {i: None for i in range(0xD800, 0xE000)}

# 钩子/情绪触发词库（用于自动打标签）
_HOOK_KEYWORDS = {
    "震撼": "shock",
    "竟然": "shock",
    "扎心": "resonance",
    "真相": "revelation",
    "揭秘": "revelation",
    "曝光": "revelation",
    "崩溃": "anxiety",
    "焦虑": "anxiety",
    "年薪": "desire",
    "变现": "desire",
    "逆袭": "desire",
    "翻盘": "desire",
    "财富": "desire",
    "秘密": "secret",
    "内幕": "secret",
    "潜规则": "secret",
    "底层逻辑": "insight",
    "本质": "insight",
    "核心": "insight",
    "必须": "authority",
    "不得不": "authority",
    "99%": "authority",
    "绝了": "emotion",
    "炸裂": "emotion",
    "泪目": "emotion",
}


def _clean_content(text: str) -> str:
    """清洗内容：移除代理字符、多余空白、清理格式"""
    if not text:
        return text
    # 移除代理字符
    text = text.translate(_SURROGATE_RANGE)
    # 移除残留的 AI 思考标签
    text = re.sub(r"<\|THINK_START\|>[\s\S]*?<\|THINK_END\|>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    # 清理多余空行（超过2个换行压缩为2个）
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 清理行首行尾空白
    text = text.strip()
    return text


def _detect_hooks(content: str) -> List[str]:
    """检测内容中的钩子类型"""
    hooks = []
    for keyword, hook_type in _HOOK_KEYWORDS.items():
        if keyword in content and hook_type not in hooks:
            hooks.append(hook_type)
    return hooks[:3]  # 最多3种钩子类型


# ── 提炼模式定义 ────────────────────────────────────────────────────
EXTRACT_MODES = {
    "full": "全量提炼（5个模块）",
    "quotes": "仅提炼金句弹药库",
    "cases": "仅提炼故事与案例",
    "viewpoints": "仅提炼认知与观点",
    "actions": "仅提炼实操行动库",
    "topics": "仅提炼IP选题映射",
    "ip_atomic": "IP原子化提取（每张卡片一个观点，适合内容生产）",
}


def build_prompt(book_name: str, text: str, mode: str = "full") -> tuple:
    """构建 AI 提炼提示词，返回 (system_prompt, user_prompt)"""
    system = f"""你是一位拥有海量知识库的"超级内容合伙人"，负责将内容彻底拆解为可安全复用、能持续爆款的"内容弹药库"。
我的IP方向是：{IP_DIRECTION}
目标受众痛点：职场焦虑、认知升级、破局成长，人性洞察。
每条素材必须附带：⚠️风险标签 + 🎯爆点场景 + ⏳改写成本 + 🕒时效熔断。
拒绝遗漏，拒绝凑数，宁可少出10条有用的，不要多出50条废话。"""

    # 限制单次 AI 调用的文本量，避免超时
    if len(text) > MAX_PROMPT_TEXT_CHARS:
        text = text[:MAX_PROMPT_TEXT_CHARS]
        truncated_note = f"\n\n【注意：原文过长，已截取前 {MAX_PROMPT_TEXT_CHARS:,} 字进行提炼】"
    else:
        truncated_note = ""

    if mode == "quotes":
        user = f"""请对《{book_name}》进行地毯式搜索，只输出【金句弹药库】{truncated_note}。

【内容】
{text}

---
## 【金句弹药库】

格式（每条必须完整）：
> [场景标签] 金句内容 【适用场景】
> ⚠️ 风险标签：✅安全 / ⚠️需语境 / ❌禁用
> 🎯 爆点场景：🔥爆款 / 💡治愈 / 📚深度
> ⏳ 改写成本：⚡0成本 / ✂️中成本 / 🛠️高成本
> 🕒 时效熔断：✅长效 / ⚠️需更新 / ❌已过期

全量提取，上限50条，不凑数。"""

    elif mode == "cases":
        user = f"""请对《{book_name}》进行地毯式搜索，只输出【故事与案例库】。

【内容】
{text}

---
## 【故事与案例库】

格式：
**案例名称：**
- 冲突：
- 动作：
- 结果：
- 启示：适合场景：
- ⚠️ 风险标签：
- 🕒 时效熔断：✅长效 / ⚠️需更新 / ❌已过期

全量提取，不限数量。"""

    elif mode == "viewpoints":
        user = f"""请对《{book_name}》进行地毯式搜索，只输出【认知与观点库】。

【内容】
{text}

---
## 【认知与观点库】

格式：
**观点名称：**
- 书中依据：[用自己的话重新表达]
- IP化角度：
- 📌 冲突预警：与[反驳观点]冲突，调和方案：
- ⚠️ 风险标签：✅安全 / ⚠️需语境 / ❌禁用
- 🕒 时效熔断：✅长效 / ⚠️需更新 / ❌已过期

全量提取，不限数量。"""

    elif mode == "actions":
        user = f"""请对《{book_name}》进行地毯式搜索，只输出【实操行动库】。

【内容】
{text}

---
## 【实操与行动库】

格式：
**行动名称：**
- 步骤：1. 2. 3.
- 适用场景：
- 风险提示：
- ⚡ 改写成本：⚡0成本 / ✂️中成本 / 🛠️高成本

全量提取，不限数量。"""

    elif mode == "topics":
        user = f"""请对《{book_name}》进行地毯式搜索，只输出【IP选题映射】。

【内容】
{text}

---
## 【IP选题映射】

列出10-20个爆款选题：
- 选题标题（能直接用的爆款标题）
- 核心素材来源
- 平台适配：抖音/小红书/公众号
- 钩子设计：开头+结尾互动"""

    elif mode == "ip_atomic":
        user = f"""请对《{book_name}》进行原子化提取，每张卡片一个独立观点。

【内容】
{text}

---
## 【IP原子笔记库】

格式（每条必须完整，JSON格式）：
```json
{{
  "atomic_notes": [
    {{
      "core_idea": "一句话核心观点（必须用自己的话重新表达，让外行能听懂）",
      "detailed_explanation": "3-5句话详细解释",
      "original_quote": "原文引用（可选）",
      "thinking_model": "所属思维模型（如：认知偏差/复利效应/机会成本/马太效应等）",
      "content_areas": ["职场", "情感", "人性", "社会", "底层逻辑"],
      "applicable_scenarios": ["短视频", "文章", "直播", "课程", "金句"],
      "emotional_resonance": ["焦虑", "希望", "愤怒", "认同", "惊讶", "好奇"],
      "target_audience": ["职场新人", "30岁焦虑", "情感困惑者", "创业者"],
      "transform_tips": "如何转化为口播稿/文章的具体建议"
    }}
  ]
}}
```

要求：
1. 每个观点一张卡片，独立完整（脱离原文也能理解）
2. 用自己的话重新表达（费曼技巧）
3. 标注思维模型（便于跨书整合）
4. 标注情感共鸣点（便于引发传播）
5. 标注适用场景（便于内容生产）
6. 放弃陈词滥调，保留反常识洞察
7. 优先提取能直接用于自媒体创作的实用观点

只输出JSON，不要有其他文字。"""

    else:  # full
        user = f"""请对《{book_name}》进行地毯式搜索，按格式完整输出"全量安全军火库"。

【内容（全书智能采样）】
{text}

---

## 【第一部分：金句弹药库】
格式（每条完整填写）：
> [场景标签] 金句内容 【适用场景】
> ⚠️ 风险标签：✅安全 / ⚠️需语境 / ❌禁用
> 🎯 爆点场景：🔥爆款 / 💡治愈 / 📚深度
> ⏳ 改写成本：⚡0成本 / ✂️中成本 / 🛠️高成本
> 🕒 时效熔断：✅长效 / ⚠️需更新 / ❌已过期
（全量提取，上限50条）

---

## 【第二部分：故事与案例库】
**案例名称：**
- 冲突：- 动作：- 结果：- 启示：- ⚠️风险：- 🕒时效：
（全量提取）

---

## 【第三部分：认知与观点库】
**观点名称：**
- 书中依据：- IP化角度：- 📌冲突预警：- ⚠️风险：- 🕒时效：
（全量提取）

---

## 【第四部分：实操与行动库】
**行动名称：**
- 步骤：- 适用场景：- 风险提示：- ⚡改写成本：
（全量提取）

---

## 【第五部分：IP选题映射】
10-20个爆款选题，每个含：标题+素材来源+平台+钩子设计

---

## 【书籍综合评级】
IP含金量/素材丰富度/可持续产出周期/跨书组合推荐"""

    return system, user


def parse_atomic_notes(source_id: str, book_title: str, raw_content: str) -> List[dict]:
    """解析IP原子笔记格式的AI输出"""
    materials = []
    now_str = now()

    try:
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_content.strip())
        cleaned = re.sub(r'\s*```\s*$', '', cleaned.strip())
        cleaned = cleaned.replace('\u201c', '"').replace('\u201d', '"')
        cleaned = cleaned.replace('\u2018', "'").replace('\u2019', "'")

        data = json.loads(cleaned)
        notes = data.get("atomic_notes", [])

        for i, note in enumerate(notes):
            content_parts = [
                f"**核心观点**：{note.get('core_idea', '')}",
                f"",
                f"**详细解释**：{note.get('detailed_explanation', '')}",
            ]
            if note.get('original_quote'):
                content_parts.extend([
                    f"",
                    f"**原文引用**：{note['original_quote']}"
                ])
            content = _clean_content("\n".join(content_parts))
            # 自动检测钩子类型
            hooks = _detect_hooks(content)
            meta = {
                "thinking_model": note.get("thinking_model", ""),
                "content_areas": note.get("content_areas", []),
                "applicable_scenarios": note.get("applicable_scenarios", []),
                "emotional_resonance": note.get("emotional_resonance", []),
                "target_audience": note.get("target_audience", []),
                "transform_tips": note.get("transform_tips", ""),
                "source_book": book_title,
                "note_index": i,
                "extraction_mode": "ip_atomic"
            }
            if hooks:
                meta["hooks"] = hooks

            materials.append({
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "category": "atomic_note",
                "content": content,
                "metadata": json.dumps(meta, ensure_ascii=False),
                "tags": json.dumps(["ip_content", note.get("thinking_model", "")], ensure_ascii=False),
                "platform": json.dumps(note.get("applicable_scenarios", []), ensure_ascii=False),
                "use_count": 0,
                "is_starred": 0,
                "created_at": now_str,
            })

    except Exception as e:
        print(f"Parse atomic notes failed: {e}")

    return materials


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
        "【金句】": "quote",
        "金句": "quote",
        "第二部分": "case",
        "故事与案例": "case",
        "案例": "case",
        "【案例】": "case",
        "第三部分": "viewpoint",
        "认知与观点": "viewpoint",
        "【观点】": "viewpoint",
        "观点": "viewpoint",
        "第四部分": "action",
        "实操与行动": "action",
        "【行动】": "action",
        "行动": "action",
        "第五部分": "topic",
        "IP选题映射": "topic",
        "【选题】": "topic",
        "选题": "topic",
        "书籍综合评级": "rating",
    }

    def flush_block():
        nonlocal current_block
        text = "\n".join(current_block).strip()
        # 清洗内容：移除代理字符、清理格式
        text = _clean_content(text)
        # 过滤垃圾素材：内容过短、纯元数据标签行（如只有"时效熔断"）
        if not text or len(text) < 50:
            current_block = []
            return
        # 过滤纯元数据标签（只有标签符号，没有实际内容）
        meta_only = all(k in text for k in ["风险标签", "爆点场景", "改写成本", "时效熔断"]) and len(text) < 100
        if meta_only:
            current_block = []
            return
        if text and len(text) > 10:
            meta = {}
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
            # 自动检测钩子类型
            hooks = _detect_hooks(text)
            if hooks:
                meta["hooks"] = hooks

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
        new_cat = None
        for key, cat in cat_map.items():
            if key in line:
                new_cat = cat
                break

        if new_cat:
            flush_block()
            current_cat = new_cat
        else:
            # quote 类型：支持 "> " 和 "- " 两种格式
            # 跳过纯元数据标签行（时效熔断等）
            if current_cat == "quote" and line.startswith("> ") and "风险标签" not in line and "爆点场景" not in line and "改写成本" not in line and "时效熔断" not in line:
                if current_block:
                    flush_block()
                current_block = [line]
            elif current_cat == "quote" and line.startswith("> "):
                # 检查是否是纯元数据行，是则跳过不追加
                if "时效熔断" not in line and "风险标签" not in line and "爆点场景" not in line and "改写成本" not in line:
                    current_block.append(line)
            elif current_cat == "quote" and (line.startswith("- ") or line.startswith("• ") or line.startswith("* ")):
                if current_block and not current_block[-1].startswith(("- ", "> ")):
                    flush_block()
                current_block.append(line)
            # case/viewpoint/action/topic 类型：支持 ** ** 和 - 格式
            elif current_cat in ("case", "viewpoint", "action", "topic") and line.startswith("**") and line.endswith("**"):
                flush_block()
                current_block = [line]
            elif current_cat in ("case", "viewpoint", "action", "topic") and line.startswith("- "):
                current_block.append(line)
            elif current_cat == "topic" and line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.")):
                flush_block()
                current_block = [line]
            elif current_block:
                current_block.append(line)

    flush_block()
    return materials
