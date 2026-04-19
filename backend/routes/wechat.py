# -*- coding: utf-8 -*-
"""routes/wechat.py - 公众号排版 / 内容改写 / 预览相关 API"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(tags=["wechat"])

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

# ─── 标准库 ────────────────────────────────────────────────────────────
import re
import sys
import uuid as _uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── 项目导入 ─────────────────────────────────────────────────────────
from config import BASE_DIR, DATA_DIR
from db import get_db, now
from ai import ai_extract

# ─── 常量 ─────────────────────────────────────────────────────────────
WECHAT_THEMES = [
    # 深度长文
    {"id": "newspaper",    "label": "报纸风",    "group": "深度长文", "desc": "《纽约时报》蓝灰，适合新闻/分析"},
    {"id": "magazine",     "label": "杂志风",    "group": "深度长文", "desc": "高端杂志版式，适合品质内容"},
    {"id": "coffee-house", "label": "咖啡馆",    "group": "深度长文", "desc": "咖啡色暖调，适合随笔/日记"},
    {"id": "ink",          "label": "水墨",      "group": "深度长文", "desc": "极简黑白，适合文学/散文"},
    # 科技产品
    {"id": "bytedance",    "label": "字节风",    "group": "科技产品", "desc": "蓝绿渐变，现代科技感"},
    {"id": "github",       "label": "GitHub",    "group": "科技产品", "desc": "开发者风格，代码友好"},
    {"id": "sspai",        "label": "少数派",    "group": "科技产品", "desc": "少数派橙色，适合效率/工具"},
    {"id": "midnight",     "label": "深夜",      "group": "科技产品", "desc": "深色背景，赛博朋克感"},
    # 文艺随笔
    {"id": "terracotta",   "label": "陶土",      "group": "文艺随笔", "desc": "暖橙圆角，轻松活泼"},
    {"id": "mint-fresh",   "label": "薄荷绿",    "group": "文艺随笔", "desc": "清新绿色，适合生活/美食"},
    {"id": "sunset-amber", "label": "琥珀",      "group": "文艺随笔", "desc": "琥珀暖色，情感/故事"},
    {"id": "lavender-dream","label": "薰衣草",   "group": "文艺随笔", "desc": "紫色梦幻，适合情感内容"},
    # 活力动态
    {"id": "sports",       "label": "运动",      "group": "活力动态", "desc": "渐变条纹，活力满满"},
    {"id": "bauhaus",      "label": "包豪斯",    "group": "活力动态", "desc": "几何色块，大胆设计感"},
    {"id": "chinese",      "label": "朱红国风",  "group": "活力动态", "desc": "朱红古典，传统文化"},
    {"id": "wechat-native","label": "微信原生",  "group": "活力动态", "desc": "微信绿，官方/通用推荐"},
    # 简约模板
    {"id": "minimal-gold", "label": "极简金",    "group": "简约模板", "desc": "金色点缀，商务简洁"},
    {"id": "focus-blue",   "label": "专注蓝",    "group": "简约模板", "desc": "蓝色聚焦，适合知识分享"},
    {"id": "elegant-green","label": "优雅绿",    "group": "简约模板", "desc": "绿色雅致，清新正式"},
    {"id": "bold-blue",    "label": "粗体蓝",    "group": "简约模板", "desc": "蓝色粗体标题，醒目"},
]

GALLERY_THEMES = [
    # 经典主题（8）
    "newspaper", "magazine", "ink", "coffee-house",
    "terracotta", "lavender-dream", "sunset-amber", "mint-fresh",
    # 科技产品（4）
    "bytedance", "github", "sspai", "midnight",
    # 活力动态（4）
    "sports", "bauhaus", "chinese", "wechat-native",
    # Bold 系列组合（12）
    "bold-ocean", "bold-sunset", "bold-forest", "bold-rose",
    "bold-midnight", "bold-gold", "bold-emerald", "bold-coral",
    "bold-lavender", "bold-mint", "bold-berry", "bold-steel",
    # Modern 系列组合（12）
    "modern-ocean", "modern-sunset", "modern-forest", "modern-rose",
    "modern-midnight", "modern-gold", "modern-emerald", "modern-coral",
    "modern-lavender", "modern-mint", "modern-berry", "modern-steel",
    # Elegant 系列组合（12）
    "elegant-ocean", "elegant-sunset", "elegant-forest", "elegant-rose",
    "elegant-midnight", "elegant-gold", "elegant-emerald", "elegant-coral",
    "elegant-lavender", "elegant-mint", "elegant-berry", "elegant-steel",
    # Gradient 系列组合（8）
    "gradient-ocean", "gradient-sunset", "gradient-forest", "gradient-rose",
    "gradient-midnight", "gradient-gold", "gradient-emerald", "gradient-coral",
    # Minimal 系列组合（8）
    "minimal-ocean", "minimal-sunset", "minimal-forest", "minimal-rose",
    "minimal-midnight", "minimal-gold", "minimal-emerald", "minimal-coral",
    # Focus 系列（3）
    "focus-blue", "focus-gold", "focus-red",
]

GALLERY_DEMO_MARKDOWN = """\
## 主要功能

在数字化时代，**内容创作**变得越来越重要。一款好的排版工具，能让你的文章在众多内容中**脱颖而出**。

> 好的排版不只是视觉享受，更是对读者的尊重。

### 核心亮点

- 完整的 Markdown 语法支持
- 精美的主题样式
- 一键复制到微信发布

1. 撰写你的内容
2. 选择喜欢的风格
3. 一键复制粘贴

---

### 代码示例

`inline code` 也是支持的。

```python
def hello():
    print("Hello, World!")
```

| 功能 | 状态 |
|------|------|
| 实时预览 | 已支持 |
| 主题选择 | 已支持 |

> [!tip] 小技巧
> 选择适合你文章风格的主题，效果更佳。
"""

# ─── 预览缓存 ─────────────────────────────────────────────────────────
_preview_cache: dict = {}  # token -> full_html


# ─── Request Models ──────────────────────────────────────────────────
class RewriteRequest(BaseModel):
    content: str
    mode: str = "口语化"       # 爆款化/口语化/精简/深度展开/加开头钩子/互动结尾
    platform: str = ""         # 抖音脚本/小红书图文/公众号文章/微博段子/通用正文


class RewriteEnsembleRequest(BaseModel):
    content: str
    mode: str = "口语化"
    platform: str = ""


class WechatFormatRequest(BaseModel):
    content: str
    theme: str = "wechat-native"


class PreviewStoreRequest(BaseModel):
    content: str
    theme: str = "default"


# ─── Routes ─────────────────────────────────────────────────────────

def _build_wechat_themes():
    """动态构建主题列表：从 themes/ 目录加载独立主题 + layout×palette 组合"""
    import sys, json
    from pathlib import Path
    # __file__ = backend/routes/wechat.py → parent.parent = backend/ → 往上两级到项目根目录
    format_dir = Path(__file__).parent.parent.parent / "wechat-format"
    themes_dir = format_dir / "themes"
    layouts_dir = themes_dir / "layouts"
    palettes_dir = themes_dir / "palettes"

    themes = []
    # 1. 独立主题文件
    for f in sorted(themes_dir.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            themes.append({
                "id": f.stem,
                "label": data.get("name", f.stem),
                "group": "经典主题",
                "desc": data.get("description", f.stem)
            })
        except Exception:
            pass

    # 2. Layout × Palette 组合
    if layouts_dir.exists() and palettes_dir.exists():
        layouts = sorted(layouts_dir.glob("*.json"))
        palettes = sorted(palettes_dir.glob("*.json"))
        for layout in layouts:
            for palette in palettes:
                combo_id = f"{layout.stem}-{palette.stem}"
                try:
                    with open(palette, encoding="utf-8") as fp:
                        palette_data = json.load(fp)
                    palette_name = palette_data.get("name", palette.stem)
                except Exception:
                    palette_name = palette.stem
                themes.append({
                    "id": combo_id,
                    "label": f"{layout.stem.capitalize()}·{palette_name}",
                    "group": "组合模板",
                    "desc": f"{layout.stem}布局 × {palette_name}配色"
                })
    return themes


# 预计算主题列表（启动时生成一次）
WECHAT_THEMES = _build_wechat_themes()


@router.get("/api/wechat-themes")
def get_wechat_themes():
    """返回可用的公众号主题列表"""
    return WECHAT_THEMES


@router.post("/api/rewrite")
def rewrite_content(req: RewriteRequest):
    """AI 改写：对输入内容按指定模式和平台进行改写，直接返回结果文本"""
    # ── 模式指令 ──────────────────────────────────────────────
    mode_tasks = {
        "爆款化":    "将以下内容改写为爆款风格：标题吸睛、开头抓人、节奏感强、情绪饱满，适合在社交媒体刷屏传播。",
        "口语化":    "将以下内容改写为轻松口语化风格：去掉书面腔，像和朋友聊天一样自然流畅，有温度感。",
        "精简":      "将以下内容精简压缩：去掉废话和重复表达，保留核心观点，控制在原文 40%-60% 的字数。",
        "深度展开":  "将以下内容深度展开：补充案例、数据、逻辑链，使论点更有说服力和深度，适合长文内容。",
        "加开头钩子": "保持正文不变，在开头加一个强力钩子（疑问/数据冲击/反常识/场景感）吸引读者继续读。",
        "互动结尾":  "保持正文不变，在结尾加一个互动引导结尾（提问/投票/引发讨论），提升评论和互动率。",
    }

    # ── 平台字数要求 ─────────────────────────────────────────
    WORD_MIN = {
        "抖音脚本":   200,
        "小红书图文": 300,
        "公众号文章": 800,
        "微博段子":   100,
        "通用正文":   150,
    }
    platform_hint = {
        "抖音脚本":   "（目标平台：抖音脚本，口语化强，适合配音朗读，每句话简短有力）",
        "小红书图文": "（目标平台：小红书，标题加emoji，段落短，多用感叹号，种草氛围）",
        "公众号文章": "（目标平台：微信公众号，文字更正式，可以稍长，注重排版节奏）",
        "微博段子":   "（目标平台：微博，精炼幽默，100-300字，结尾留金句或反转）",
        "通用正文":   "（通用平台格式，不限制风格）",
    }

    base_task    = mode_tasks.get(req.mode, f"将以下内容进行【{req.mode}】改写。")
    plat_hint    = platform_hint.get(req.platform, f"（目标平台：{req.platform}）" if req.platform else "")
    min_words    = WORD_MIN.get(req.platform, 150)

    # ── Few-Shot 示例库 ──────────────────────────────────────
    EXAMPLES = {
        '爆款化': '''
【示例1】
输入：「婚姻需要双方共同努力经营，遇到矛盾时要互相理解包容，这样才能走得更长远。」
输出：「婚姻这东西，最怕的不是吵架，是两个人都憋着不说。我见过太多夫妻，表面上和和气气，背地里各过各的。其实啊，吵一架把话说开，比什么都强。」

【示例2】
输入：「根据研究表明，长期熬夜会导致免疫力下降，对身体健康产生严重影响。」
输出：「熬夜这事，偶尔问题不大，长期真的要命。我不是吓你，是有研究数据撑着的——连续熬夜一周，你身体的免疫力直接拉胯。」''',

        '口语化': '''
【示例1】
输入：「成功的关键在于持续学习和不断实践，只有不断提升自己才能适应环境变化。」
输出：「说白了，你想混得好，就两件事：学和干。不是看书感动自己，是真的下场去练。我见过太多人学了一脑子道理，一做事就抓瞎。」

【示例2】
输入：「该产品具有高效、便捷、环保等多项优势，深受消费者青睐。」
输出：「这东西用起来是真的顺手。我第一次上手的时候就感觉，这设计者是真的懂啊，不像某些产品反人类。」''',

        '精简': '''
【示例1】
输入：「在我们日常生活和工作中，时间管理是一个非常重要的话题，一个人如果能够很好地管理自己的时间，那么他就能够更加高效地完成各种任务，从而有更多的时间去做自己喜欢的事情。」
输出：「会管理时间的人，效率能甩普通人几条街。说白了就是：先想清楚什么重要，什么次要，然后把时间花在刀刃上。」

【示例2】
输入：「在当今社会，互联网技术的发展日新月异，改变了人们的生活方式和工作模式，越来越多的人开始选择远程办公，这种工作方式不仅节省了通勤时间，还提高了工作的灵活性。」
输出：「互联网这东西，彻底改变了我们上班的方式。远程办公越来越常见，省了通勤时间，工作也更灵活了。」''',

        '深度展开': '''
【示例1】
输入：「要学会拒绝别人。」
输出：「不懂拒绝的人，活得有多累？同事找你帮忙，你明明忙得脚不沾地，还是咬牙接下；朋友借钱，你心里一百个不愿意，嘴上还是说"行"。结果呢？自己的事没办好，别人的事也没办好，两头不讨好。学会拒绝不是自私，是对自己负责，也是对别人负责——你帮不了的事硬接，最后搞砸了，对方才真的难受。」

【示例2】
输入：「坚持很重要。」
输出：「为什么有些人做事三分钟热度，有些人能咬牙死磕？我观察下来，差别不在意志力，在于你是不是真的想要。我有个朋友减肥说了三年，每次都失败，不是他不努力，是他其实没那么想瘦——嘴上说说而已。你呢？你想做的事，是真想要，还是只是觉得应该想要？」''',

        '加开头钩子': '''
【示例1】
输入：「职场中要学会与不同性格的人相处...」
输出：「你有没有遇到过那种人？表面上笑眯眯，背后捅刀子。职场三年，我踩过的坑比你听过的道理还多。今天说点真的。」

【示例2】
输入：「健康的饮食习惯对每个人都至关重要...」
输出：「中国有4亿人每天吃的这个，正在慢慢杀死你。不是外卖，是你自己都意识不到的那个习惯。」''',

        '互动结尾': '''
【示例1】
输入：「...以上就是我对这个话题的全部看法」
输出：「...你觉得呢？你有没有类似的经历？欢迎评论区说出来，觉得有用的转给朋友。」

【示例2】
输入：「...这就是我的建议」
输出：「以上，完。觉得有用的话，点个赞；想知道更多，评论区抛出你的问题，我来答。」''',
    }

    few_shot = EXAMPLES.get(req.mode, "")

    # ── AI 禁止词清单（持续补充）───────────────────────────────
    BANNED_WORDS = [
        "此外", "总之", "综上所述", "值得注意的是", "至关重要", "深入探讨",
        "深刻的启示", "引人深省", "不禁让人", "持久的", "格局", "赋能",
        "洞见", "值得深思", "由此可见", "不可磨灭", "见证了", "标志着",
        "体现了", "不言而喻", "毋庸置疑", "而言之", "显然", "无疑",
        "可以看出", "不难发现", "至关重要", "核心", "关键", "本质",
        "层面上", "角度来看", "层面上讲", "从这个意义上",
    ]

    # ── 组装 System Prompt ────────────────────────────────────
    system_prompt = f"""你是一位顶级内容创作者，擅长把素材改写成有灵魂、有温度的真人内容。

【第一步：提炼灵魂——必须先完成】
在改写之前，先从原文中提炼出"3个必须保留的信息点"：
1. 一句话概括核心观点或故事
2. 一个具体细节（数字/名字/场景/案例）
3. 一种核心情绪或态度

格式：【灵魂1】...【灵魂2】...【灵魂3】...

【第二步：执行改写】
{base_task}{plat_hint}

【字数要求】
输出内容必须 ≥ {min_words} 汉字（不含标点符号）。字数不够=任务失败。

【第三步：自检清单】
改写完成后，对照以下清单检查是否通过：
□ 原文3个灵魂信息点是否全部保留？
□ 有没有出现禁用词（此外、总之、关键、核心、赋能、洞见...）？
□ 有没有三段论（首先/其次/最后）？
□ 有没有"这不仅仅是…而是…"结构？
□ 句子长度是否有变化（不是每句都一样长）？
□ 有没有具体数字/名字/场景（不是说"长期"而是说"3年"）？
□ 有没有态度（不是中立报道，而是"我喜欢/我讨厌/我觉得"）？

如果自检不通过，重新改写。

【Few-Shot 参考示例】
{few_shot}

【去AI化规则】

▌词汇红线：以下词出现必须替换
{', '.join(BANNED_WORDS)}
→ 替换示例：此外→还有、总之→说白了、关键→重点、核心→最要紧的、赋能→帮忙、洞见→发现

▌结构红线：
- 禁用三段论（首先→其次→最后）→ 改成自然叙述
- 禁用"这不仅仅是…而是…" → 直接说结论
- 禁用"标志着…" → 删掉，说具体事实
- 禁用金句式收尾 → 换成有态度的话

▌真人写法（给方向，不是禁止清单）：
✅ 句子长短交错——短句打节奏，长句偶尔来一句
✅ 有你明确的态度——喜欢就是喜欢，不爽就是不爽
✅ 说具体的——"3年"好过"长期"，"第一个月"好过"初期"
✅ 允许有点毛边——真人说话就是有点散，不是每句都对仗
✅ 像给朋友发消息那样写——自然、亲切、有画面感

直接输出【改写结果】，不要输出自检过程、不要前言后记。"""

    user_prompt = req.content

    try:
        # 先估算输入字数，用于判断"精简"模式的目标
        input_len = len(re.sub(r'\s+', '', req.content))
        if req.mode == "精简":
            user_prompt = f"【原文约{input_len}字，目标输出{int(input_len * 0.4)}-{int(input_len * 0.6)}字】\n\n" + req.content

        result, model_used = ai_extract(system_prompt, user_prompt, max_tokens=8000, temperature=0.85)
        return _clean_surrogate({"result": result, "model": model_used})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI改写失败：{str(e)}")


def _humanize_pass(text: str) -> str:
    """4-Pass Humanization 后处理"""
    # Pass 1: 移除 AI 高频词（扩展清单）
    AI_WORDS = [
        '此外', '总之', '综上所述', '值得注意的是', '至关重要', '深入探讨',
        '深刻的启示', '引人深省', '不禁让人', '持久的', '格局', '赋能',
        '洞见', '值得深思', '由此可见', '不可磨灭', '见证了', '标志着',
        '体现了', '不言而喻', '毋庸置疑', '而言之', '显然', '无疑',
        '可以看出', '不难发现', '核心', '关键', '本质', '层面上',
        '角度来看', '层面上讲', '从这个意义上', '值得注意的是',
        '值得注意的是', '不难发现', '由此可见', '可以说',
    ]
    for w in AI_WORDS:
        replacements = {
            '此外': '还有', '总之': '说白了', '综上所述': '归根结底',
            '值得注意的是': '要我说', '至关重要': '特别重要', '深入探讨': '细说',
            '深刻的启示': '挺有启发的', '引人深省': '值得想想', '不禁让人': '让人',
            '持久的': '长期的', '格局': '眼界', '赋能': '帮忙', '洞见': '发现',
            '值得深思': '值得想想', '由此可见': '可见', '不可磨灭': '不会消失的',
            '见证了': '看到了', '标志着': '说明', '体现了': '反映了',
            '不言而喻': '不用说', '毋庸置疑': '不用怀疑', '而言之': '总之',
            '显然': '很明显', '无疑': '不用说', '可以看出': '可见',
            '不难发现': '容易看到', '核心': '最核心', '关键': '最关键',
            '本质': '最本质', '层面上': '方面',
        }
        text = text.replace(w, replacements.get(w, '很'))

    # Pass 2: 打破均匀句长——在连续3个短句后插入一个较长句子
    sentences = re.split(r'([。！？；\n])', text)
    result = []
    short_count = 0
    for i in range(0, len(sentences), 2):
        s = sentences[i]
        punct = sentences[i+1] if i+1 < len(sentences) else ''
        if not s.strip():
            continue
        word_count = len(s.strip())
        if word_count < 15:
            short_count += 1
        else:
            short_count = 0
        result.append(s + punct)
        # 连续短句过多时，强制合并
        if short_count >= 3 and i+2 < len(sentences):
            next_s = sentences[i+2].strip() if i+2 < len(sentences) else ''
            if next_s:
                result[-1] = result[-1].rstrip('。！？；') + '，' + next_s
                short_count = 0

    text = ''.join(result)

    # Pass 3: 移除"可引用金句结尾"——如果结尾像格言，加一句口语化吐槽
    text = text.strip()
    if text and len(text) > 20:
        last_sentence = re.split(r'[。！？；\n]', text)[-2] if len(re.split(r'[。！？；\n]', text)) > 1 else ''
        if last_sentence and (len(last_sentence) < 30 and ('。' not in last_sentence[-10:])):
            text = text.rstrip('。！？') + '。说完了，就这样。'

    # Pass 4: 注入自我引用（只在合适位置加一句）
    if '我认为' not in text and '我觉得' not in text and len(text) > 100:
        mid = len(text) // 2
        text = text[:mid] + '我自己的想法是，' + text[mid:]

    return text


@router.post("/api/rewrite-ensemble")
async def rewrite_ensemble(req: RewriteEnsembleRequest):
    """多版本改写——用两种不同风格并行生成2个版本，让用户选择更好的"""
    mode_tasks = {
        "爆款化":    "将以下内容改写为爆款风格：标题吸睛、开头抓人、节奏感强、情绪饱满，适合在社交媒体刷屏传播。",
        "口语化":    "将以下内容改写为轻松口语化风格：去掉书面腔，像和朋友聊天一样自然流畅，有温度感。",
        "精简":      "将以下内容精简压缩：去掉废话和重复表达，保留核心观点，控制在原文 40%-60% 的字数。",
        "深度展开":  "将以下内容深度展开：补充案例、数据、逻辑链，使论点更有说服力和深度，适合长文内容。",
        "加开头钩子": "保持正文不变，在开头加一个强力钩子（疑问/数据冲击/反常识/场景感）吸引读者继续读。",
        "互动结尾":  "保持正文不变，在结尾加一个互动引导结尾（提问/投票/引发讨论），提升评论和互动率。",
    }
    WORD_MIN = {
        "抖音脚本":   200, "小红书图文": 300, "公众号文章": 800, "微博段子": 100, "通用正文": 150,
    }
    platform_hint = {
        "抖音脚本":   "（目标平台：抖音脚本，口语化强，适合配音朗读，每句话简短有力）",
        "小红书图文": "（目标平台：小红书，标题加emoji，段落短，多用感叹号，种草氛围）",
        "公众号文章": "（目标平台：微信公众号，文字更正式，可以稍长，注重排版节奏）",
        "微博段子":   "（目标平台：微博，精炼幽默，100-300字，结尾留金句或反转）",
        "通用正文":   "（通用平台格式，不限制风格）",
    }

    base_task = mode_tasks.get(req.mode, f"将以下内容进行【{req.mode}】改写。")
    plat_hint = platform_hint.get(req.platform, f"（目标平台：{req.platform}）" if req.platform else "")
    min_words = WORD_MIN.get(req.platform, 150)

    system_base = f"""你是一位顶级内容创作者，擅长把素材改写成有灵魂、有温度的真人内容。

【本次任务】
{base_task}{plat_hint}
【输出字数要求】≥ {min_words} 汉字。
【去AI化】禁用词：此外、总之、关键、核心、赋能、洞见、值得注意的是、深入探讨。替换：此外→还有、总之→说白了。
【真人写法】✅ 句子长短交错 ✅ 有态度 ✅ 说具体的（"3年"好过"长期"）✅ 像给朋友发消息
直接输出改写结果，不要前言后记。"""

    def _do_rewrite(temp: float, label: str):
        """在后台线程执行 AI 改写"""
        try:
            text, model = ai_extract(system_base, req.content, max_tokens=8000, temperature=temp)
            text = _humanize_pass(text)
            char_count = len(re.sub(r'\s+', '', text))
            return {"label": label, "text": text, "chars": char_count, "model": model, "temp": temp}
        except Exception as e:
            return {"label": label, "error": str(e), "text": ""}

    # 并行执行两个版本的改写
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            loop.run_in_executor(pool, _do_rewrite, temp, label)
            for temp, label in [(0.7, "稳重版"), (0.95, "创意版")]
        ]
        results = await asyncio.gather(*futures)

    return _clean_surrogate({"versions": list(results)})


@router.post("/api/wechat-format")
def wechat_format(req: WechatFormatRequest):
    """将 Markdown 排版为微信公众号兼容的内联样式 HTML"""
    format_dir = BASE_DIR / "wechat-format"
    if str(format_dir) not in sys.path:
        sys.path.insert(0, str(format_dir))

    try:
        import format as wfmt
    except ImportError as e:
        raise HTTPException(500, f"排版模块加载失败：{e}")

    # 验证主题存在
    valid_ids = {t["id"] for t in WECHAT_THEMES}
    theme_name = req.theme if req.theme in valid_ids else "wechat-native"

    try:
        theme = wfmt.load_theme(theme_name)

        # 直接执行核心处理流程，绕开 vault_root os.walk（Windows 根目录遍历会卡死）
        content = req.content
        input_path = Path("article.md")
        output_dir = BASE_DIR / "data" / "wechat-output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 通用预处理（与 format_for_output 一致，跳过 wikilinks/本地图片）
        title = wfmt.extract_title(content, input_path)
        word_count = wfmt.count_words(content)
        content = wfmt.strip_frontmatter(content)
        content = wfmt.fix_cjk_spacing(content)
        content = wfmt.fix_cjk_bold_punctuation(content)
        content = wfmt.process_callouts(content)
        content = wfmt.process_manual_footnotes(content)
        content = wfmt.process_fenced_containers(content)
        content = re.sub(r'~~(.+?)~~', r'<del>\1</del>', content)
        # 跳过 convert_wikilinks（需要遍历本地文件系统，Windows 上 vault_root='/' 会崩溃）
        # 跳过 copy_markdown_images（用户粘贴的是纯文字，无本地图片）

        html = wfmt.md_to_html(content)
        html, footnote_html = wfmt.extract_links_as_footnotes(html)
        html = wfmt.inject_inline_styles(html, theme)
        if footnote_html:
            footnote_html = wfmt.inject_inline_styles(footnote_html, theme, skip_wrapper=True)
        html = wfmt.convert_image_captions(html)

        full_html = html + ("\n" + footnote_html if footnote_html else "")
        return _clean_surrogate({
            "html": full_html,
            "title": title,
            "word_count": word_count,
            "theme": theme_name,
        })
    except Exception as e:
        import traceback
        raise HTTPException(500, f"排版失败：{e}\n{traceback.format_exc()}")


def _build_preview_page(body_html: str) -> str:
    base_style = (
        "*{box-sizing:border-box}"
        "html,body{margin:0;padding:0;background:#fff}"
        "body{padding:16px 24px;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;"
        "font-size:15px;line-height:1.75;color:#333}"
        "img{max-width:100%;display:block;margin:8px auto}"
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{base_style}</style>
</head>
<body>{body_html}</body>
</html>"""


@router.post("/api/wechat-preview")
def wechat_preview(req: WechatFormatRequest):
    """返回完整可渲染的 HTML 页面（旧接口保留兼容）"""
    result = wechat_format(req)
    body_html = result["html"]
    full_page = _build_preview_page(body_html)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=full_page, media_type="text/html; charset=utf-8")


def _render_gallery_theme(tid: str, theme_data: dict, html: str, footnote_html: str) -> tuple:
    """渲染单个主题（用于并行 gallery）"""
    import sys
    from pathlib import Path
    format_dir = Path(__file__).parent.parent / "wechat-format"
    if str(format_dir) not in sys.path:
        sys.path.insert(0, str(format_dir))
    import format as wfmt
    rendered = wfmt.inject_inline_styles(html, theme_data)
    fn_rendered = ""
    if footnote_html:
        fn_rendered = wfmt.inject_inline_styles(footnote_html, theme_data, skip_wrapper=True)
    return tid, rendered + ("\n" + fn_rendered if fn_rendered else "")


def generate_gallery_html(rendered_map: dict, theme_map: dict,
                         theme_ids: list, title: str, word_count: int,
                         recommended: list = None) -> str:
    """生成主题画廊页面 HTML"""
    if recommended is None:
        recommended = []

    base_style = (
        "*{box-sizing:border-box}"
        "html,body{margin:0;padding:0;background:#fff}"
        "body{padding:16px 24px;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;"
        "font-size:15px;line-height:1.75;color:#333}"
        "img{max-width:100%;display:block;margin:8px auto}"
    )

    GROUPS = [
        ("经典主题", ["newspaper", "magazine", "ink", "coffee-house", "terracotta", "lavender-dream", "sunset-amber", "mint-fresh"]),
        ("科技产品", ["bytedance", "github", "sspai", "midnight"]),
        ("活力动态", ["sports", "bauhaus", "chinese", "wechat-native"]),
        ("Bold醒目", ["bold-ocean", "bold-sunset", "bold-forest", "bold-rose", "bold-midnight", "bold-gold", "bold-emerald", "bold-coral"]),
        ("Modern摩登", ["modern-ocean", "modern-sunset", "modern-forest", "modern-rose", "modern-midnight", "modern-gold", "modern-emerald", "modern-coral"]),
        ("Elegant优雅", ["elegant-ocean", "elegant-sunset", "elegant-forest", "elegant-rose", "elegant-midnight", "elegant-gold", "elegant-emerald", "elegant-coral"]),
        ("Gradient渐变", ["gradient-ocean", "gradient-sunset", "gradient-forest", "gradient-rose", "gradient-midnight", "gradient-gold", "gradient-emerald", "gradient-coral"]),
        ("Minimal简约", ["minimal-ocean", "minimal-sunset", "minimal-forest", "minimal-rose", "minimal-midnight", "minimal-gold", "minimal-emerald", "minimal-coral"]),
        ("Focus专注", ["focus-blue", "focus-gold", "focus-red"]),
    ]

    buttons_html = ""
    btn_index = 0
    for group_name, group_ids in GROUPS:
        group_tids = [t for t in group_ids if t in theme_ids]
        if not group_tids:
            continue
        buttons_html += f'<div class="theme-group"><span class="group-label">{group_name}</span>'
        for tid in group_tids:
            theme = theme_map[tid]
            accent = theme.get("colors", {}).get("accent", "#333")
            active = " active" if btn_index == 0 else ""
            is_recommended = " recommended" if tid in recommended else ""
            name = theme.get("name", tid)
            rec_label = '<span class="rec-badge">推荐</span>' if tid in recommended else ""
            buttons_html += (
                f'<button class="theme-btn{active}{is_recommended}" data-theme="{tid}" '
                f'onclick="switchTheme(\'{tid}\')">'
                f'<span class="theme-dot" style="background:{accent}"></span>'
                f'{name}{rec_label}</button>'
            )
            btn_index += 1
        buttons_html += '</div>\n'

    previews_html = ""
    for i, tid in enumerate(theme_ids):
        display = "block" if i == 0 else "none"
        previews_html += (
            f'<div class="theme-preview" data-theme="{tid}" '
            f'style="display:{display}">{rendered_map[tid]}</div>\n'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} - 主题选择</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; background: #f5f5f7; min-height: 100vh; }}
.toolbar {{ position: fixed; top: 0; left: 0; right: 0; background: rgba(255,255,255,0.92); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-bottom: 1px solid #e0e0e0; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; z-index: 200; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
.toolbar-left {{ display: flex; align-items: center; gap: 16px; }}
.toolbar-title {{ font-size: 15px; font-weight: 600; color: #1d1d1f; }}
.toolbar-meta {{ font-size: 13px; color: #86868b; }}
.toolbar-hint {{ font-size: 13px; color: #07c160; font-weight: 500; }}
.main-container {{ max-width: 700px; margin: 80px auto 40px; padding: 0 20px; display: flex; flex-direction: column; align-items: center; gap: 24px; }}
.theme-buttons {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; max-width: 600px; }}
.theme-group {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }}
.group-label {{ font-size: 12px; color: #86868b; font-weight: 600; min-width: 60px; letter-spacing: 0.5px; }}
.theme-btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; background: #fff; border: 2px solid #e0e0e0; border-radius: 20px; font-size: 13px; font-weight: 500; color: #333; cursor: pointer; transition: all 0.2s; font-family: inherit; }}
.theme-btn:hover {{ border-color: #ccc; background: #fafafa; }}
.theme-btn.active {{ border-color: #07c160; background: rgba(7,193,96,0.06); color: #07c160; }}
.theme-btn.recommended {{ position: relative; }}
.theme-btn.recommended .rec-badge {{ position: absolute; top: -8px; right: -6px; background: #ff9500; color: #fff; font-size: 10px; line-height: 1; padding: 2px 5px; border-radius: 6px; font-weight: 600; pointer-events: none; }}
.theme-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
.phone-frame {{ width: 100%; max-width: 415px; background: #fff; border-radius: 16px; box-shadow: 0 8px 40px rgba(0,0,0,0.12); overflow: hidden; }}
.phone-header {{ background: #ededed; padding: 12px 16px; display: flex; align-items: center; justify-content: center; font-size: 13px; color: #999; border-bottom: 1px solid #e0e0e0; }}
.preview-scroll {{ max-height: 600px; overflow-y: auto; padding: 20px; }}
.theme-preview {{ font-family: -apple-system, "PingFang SC", sans-serif; }}
.action-btn {{ width: 100%; max-width: 415px; padding: 14px 0; background: #07c160; color: #fff; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.2s; letter-spacing: 0.5px; font-family: inherit; }}
.action-btn:hover {{ background: #06ae56; }}
.action-btn:active {{ transform: scale(0.99); }}
.action-btn.copied {{ background: #34c759; }}
.font-size-selector {{ display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 16px; padding: 8px 0; }}
.fs-label {{ font-size: 13px; color: #999; }}
.fs-btn {{ padding: 4px 12px; border: 1px solid #ddd; border-radius: 16px; background: #fff; font-size: 13px; color: #666; cursor: pointer; transition: all 0.2s; font-family: inherit; }}
.fs-btn:hover {{ border-color: #07C160; color: #07C160; }}
.fs-btn.active {{ background: #07C160; border-color: #07C160; color: #fff; }}
@media (max-width: 600px) {{ .toolbar {{ padding: 10px 14px; }} .toolbar-hint {{ display: none; }} .main-container {{ margin-top: 68px; padding: 0 12px; }} .theme-buttons {{ display: grid; grid-template-columns: 1fr 1fr; width: 100%; }} .theme-btn {{ justify-content: center; }} .phone-frame {{ border-radius: 0; box-shadow: none; }} .preview-scroll {{ max-height: 500px; }} }}
</style>
</head>
<body>
<div class="toolbar">
    <div class="toolbar-left">
        <span class="toolbar-title">{title}</span>
        <span class="toolbar-meta">{word_count} 字</span>
    </div>
    <span class="toolbar-hint">选一个你喜欢的风格</span>
</div>
<div class="main-container">
    <div class="font-size-selector">
        <span class="fs-label">字号</span>
        <button class="fs-btn active" data-size="15" onclick="switchFontSize(15)">15px</button>
        <button class="fs-btn" data-size="16" onclick="switchFontSize(16)">16px</button>
    </div>
    <div class="theme-buttons">
{buttons_html}
    </div>
    <div class="phone-frame">
        <div class="phone-header">微信公众号预览</div>
        <div class="preview-scroll" id="previewScroll">
{previews_html}
        </div>
    </div>
    <button class="action-btn" id="copyBtn" onclick="applyTheme()">复制内容到剪贴板 → 公众号粘贴</button>
</div>
<script>
var selectedTheme = '{theme_ids[0] if theme_ids else ""}';
function switchTheme(themeId) {{
    var previews = document.querySelectorAll('.theme-preview');
    for (var i = 0; i < previews.length; i++) {{ previews[i].style.display = 'none'; }}
    var target = document.querySelector('.theme-preview[data-theme="' + themeId + '"]');
    if (target) {{ target.style.display = 'block'; }}
    var btns = document.querySelectorAll('.theme-btn');
    for (var i = 0; i < btns.length; i++) {{
        if (btns[i].getAttribute('data-theme') === themeId) {{ btns[i].classList.add('active'); }} else {{ btns[i].classList.remove('active'); }}
    }}
    selectedTheme = themeId;
    document.getElementById('previewScroll').scrollTop = 0;
}}
function applyTheme() {{
    var target = document.querySelector('.theme-preview[data-theme="' + selectedTheme + '"]');
    if (!target) return;
    var range = document.createRange();
    range.selectNodeContents(target);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    try {{ document.execCommand('copy'); }} catch(e) {{}}
    sel.removeAllRanges();
    var btn = document.getElementById('copyBtn');
    var activeBtn = document.querySelector('.theme-btn.active');
    var themeName = activeBtn ? activeBtn.textContent.trim().replace('推荐','').trim() : selectedTheme;
    btn.textContent = '已复制「' + themeName + '」 ✓';
    btn.classList.add('copied');
    setTimeout(function() {{ btn.textContent = '复制内容到剪贴板 → 公众号粘贴'; btn.classList.remove('copied'); }}, 3000);
}}
function switchFontSize(size) {{
    document.querySelectorAll('.fs-btn').forEach(function(btn) {{
        if (parseInt(btn.dataset.size) === size) {{ btn.classList.add('active'); }} else {{ btn.classList.remove('active'); }}
    }});
    document.querySelectorAll('.theme-preview').forEach(function(preview) {{
        preview.querySelectorAll('p, span, section').forEach(function(el) {{
            var fs = parseInt(el.style.fontSize);
            if (fs >= 14 && fs <= 18) {{ el.style.fontSize = size + 'px'; }}
        }});
    }});
}}
document.addEventListener('DOMContentLoaded', function() {{}});
</script>
</body>
</html>"""


@router.post("/api/wechat-gallery")
def wechat_gallery(req: WechatFormatRequest):
    """返回主题画廊页面，可一次预览所有主题"""
    from fastapi.responses import HTMLResponse

    format_dir = BASE_DIR / "wechat-format"
    if str(format_dir) not in sys.path:
        sys.path.insert(0, str(format_dir))

    try:
        import format as wfmt
    except ImportError as e:
        raise HTTPException(500, f"排版模块加载失败：{e}")

    content = req.content or GALLERY_DEMO_MARKDOWN

    # 预处理（与 wechat_format 一致，跳过 wikilinks/本地图片）
    title = wfmt.extract_title(content, Path("article.md"))
    word_count = wfmt.count_words(content)
    content = wfmt.strip_frontmatter(content)
    content = wfmt.fix_cjk_spacing(content)
    content = wfmt.fix_cjk_bold_punctuation(content)
    content = wfmt.process_callouts(content)
    content = wfmt.process_manual_footnotes(content)
    content = wfmt.process_fenced_containers(content)
    content = re.sub(r'~~(.+?)~~', r'<del>\1</del>', content)

    html = wfmt.md_to_html(content)
    html, footnote_html = wfmt.extract_links_as_footnotes(html)

    # 加载所有画廊主题
    theme_map = {}
    gallery_theme_ids = []
    for tid in GALLERY_THEMES:
        try:
            theme_map[tid] = wfmt.load_theme(tid)
            gallery_theme_ids.append(tid)
        except Exception:
            pass

    if not gallery_theme_ids:
        return HTMLResponse("<html><body><p>无可用主题</p></body></html>", media_type="text/html; charset=utf-8")

    # 并行渲染所有主题
    rendered_map = {}
    with ThreadPoolExecutor(max_workers=min(8, len(gallery_theme_ids))) as executor:
        futures = {
            executor.submit(_render_gallery_theme, tid, theme_map[tid], html, footnote_html): tid
            for tid in gallery_theme_ids
        }
        for future in as_completed(futures):
            tid, rendered = future.result()
            rendered_map[tid] = rendered

    gallery_html = generate_gallery_html(
        rendered_map, theme_map, gallery_theme_ids,
        title, word_count, recommended=[req.theme] if req.theme in gallery_theme_ids else []
    )

    return HTMLResponse(content=gallery_html, media_type="text/html; charset=utf-8")


@router.post("/api/preview-store")
def preview_store(req: PreviewStoreRequest):
    """生成排版并缓存到内存，返回 token；前端用 GET /api/preview/{token} 在 iframe 中展示"""
    fmt_result = wechat_format(WechatFormatRequest(content=req.content, theme=req.theme))
    token = _uuid.uuid4().hex
    _preview_cache[token] = _build_preview_page(fmt_result["html"])
    # 最多保留 20 条缓存，防止内存膨胀
    if len(_preview_cache) > 20:
        oldest = next(iter(_preview_cache))
        del _preview_cache[oldest]
    return {
        "token": token,
        "html": fmt_result["html"],       # 仍返回 html 供复制
        "word_count": fmt_result.get("word_count"),
        "theme": fmt_result.get("theme", req.theme),
    }


@router.get("/api/preview/{token}")
def preview_get(token: str):
    """GET 接口，返回缓存的完整 HTML 预览页面；可直接作为 iframe src"""
    from fastapi.responses import HTMLResponse
    html = _preview_cache.get(token)
    if not html:
        return HTMLResponse("<html><body><p style='color:#999;text-align:center;padding:40px'>预览已过期，请重新生成排版</p></body></html>")
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
