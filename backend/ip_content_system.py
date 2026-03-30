"""
IP Arsenal 个人IP内容生产系统
================================

基于顶级知识管理方法论：
- Tiago Forte: Building a Second Brain + CODE方法
- Zettelkasten: 卡片笔记法
- PARA: 项目/领域/资源/归档
- 费曼学习法: 输出倒逼输入
- 查理·芒格: 跨学科思维模型

核心目标：将书籍转化为可直接使用的IP内容
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════
# 数据模型 - 专为IP内容生产设计
# ═══════════════════════════════════════════════════════════════════════════

class ContentType(Enum):
    """内容类型 - 对应不同输出场景"""
    SHORT_VIDEO = "短视频"      # 抖音/视频号 60秒内
    LONG_VIDEO = "长视频"       # 中视频 3-10分钟
    ARTICLE = "文章"            # 公众号/知乎
    LIVE = "直播"               # 直播脚本
    COURSE = "课程"             # 付费课程
    QUOTE = "金句"              # 单独传播的金句


class ThinkingModel(Enum):
    """思维模型 - 跨学科分类"""
    # 心理学
    COGNITIVE_BIAS = "认知偏差"
    BEHAVIORAL_PSYCHOLOGY = "行为心理学"
    EMOTIONAL_INTELLIGENCE = "情商"
    # 社会
    SOCIAL_DYNAMICS = "社会动力学"
    GROUP_BEHAVIOR = "群体行为"
    POWER_RELATIONS = "权力关系"
    # 人性
    HUMAN_NATURE = "人性本质"
    MOTIVATION = "动机驱动"
    SELF_DECEPTION = "自我欺骗"
    # 职场
    CAREER_STRATEGY = "职场策略"
    COMMUNICATION = "沟通技巧"
    LEADERSHIP = "领导力"
    # 情感
    RELATIONSHIP_DYNAMICS = "关系动力学"
    ATTACHMENT_THEORY = "依恋理论"
    CONFLICT_RESOLUTION = "冲突解决"
    # 底层逻辑
    SYSTEMS_THINKING = "系统思维"
    FIRST_PRINCIPLES = "第一性原理"
    OPPORTUNITY_COST = "机会成本"
    COMPOUND_EFFECT = "复利效应"


class EmotionalResonance(Enum):
    """情感共鸣点"""
    ANXIETY = "焦虑"            # 引发焦虑（问题意识）
    HOPE = "希望"               # 给予希望（解决方案）
    ANGER = "愤怒"              # 不公现象（情绪共鸣）
    RECOGNITION = "认同"        # "我也是这样"
    SURPRISE = "惊讶"           # 反常识观点
    CURIOSITY = "好奇"          # 悬念钩子
    EMPOWERMENT = " empowerment" # 能力感（学了就能用）


@dataclass
class AtomicNote:
    """
    原子笔记 - Zettelkasten核心
    每个观点一张卡片，独立完整
    """
    id: str
    source_book: str
    source_chapter: str
    source_page: str

    # 内容层
    core_idea: str              # 一句话核心观点（必须用自己的话）
    detailed_explanation: str   # 3-5句话详细解释
    original_quote: str         # 原文引用（可选）

    # 分类层
    thinking_model: str         # 所属思维模型
    content_areas: List[str]    # 适用领域 [职场,情感,人性...]

    # 应用层
    applicable_scenarios: List[str]  # 适用场景 [口播,文章,直播...]
    emotional_resonance: List[str]   # 情感共鸣点
    target_audience: List[str]       # 目标受众

    # 连接层
    related_notes: List[str]    # 关联的笔记ID
    contradictions: List[str]   # 矛盾的观点ID

    # 元数据
    created_at: str
    used_count: int = 0         # 被使用次数
    last_used: Optional[str] = None
    quality_rating: int = 3     # 1-5星评分

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_content_prompt(self) -> str:
        """转化为内容生成Prompt"""
        return f"""
核心观点：{self.core_idea}
详细解释：{self.detailed_explanation}
思维模型：{self.thinking_model}
适用领域：{', '.join(self.content_areas)}
情感共鸣：{', '.join(self.emotional_resonance)}
目标受众：{', '.join(self.target_audience)}
"""


@dataclass
class ContentPiece:
    """
    内容成品 - 可直接发布的IP内容
    """
    id: str
    content_type: str           # 短视频/文章/直播等
    platform: str               # 抖音/视频号/公众号等

    # 结构层
    hook: str                   # 开头钩子（前3秒/50字）
    core_content: str           # 核心内容
    story_case: str             # 故事/案例
    actionable_advice: str      # 行动建议
    ending_interaction: str     # 结尾互动

    # 来源层
    source_notes: List[str]     # 引用的原子笔记ID
    source_books: List[str]     # 引用的书籍

    # 数据层
    created_at: str
    published: bool = False
    publish_date: Optional[str] = None
    performance_data: Dict = field(default_factory=dict)  # 播放量/点赞/评论等


@dataclass
class MentalModel:
    """
    思维模型 - 查理·芒格方法
    跨学科的核心概念
    """
    name: str
    category: str               # 心理学/经济学/生物学等
    definition: str             # 定义
    examples: List[str]         # 具体例子
    related_notes: List[str]    # 关联的原子笔记
    application_scenarios: List[str]  # 应用场景


# ═══════════════════════════════════════════════════════════════════════════
# 专用Prompt模板 - 针对IP内容生产优化
# ═══════════════════════════════════════════════════════════════════════════

class IPContentPrompts:
    """IP内容生产专用Prompt"""

    # Prompt 1: 原子化提取
    ATOMIC_EXTRACTION = """你是一位知识管理专家，使用Zettelkasten方法为个人IP博主处理书籍内容。

任务：将以下文本转化为"原子笔记"（每张卡片一个独立观点）

要求：
1. 每条笔记必须是完整的、独立的观点（脱离原文也能理解）
2. 用自己的话重新表达（费曼技巧，让外行能懂）
3. 标注思维模型（如：认知偏差、职场策略、人性本质等）
4. 标注适用领域（职场/情感/人性/社会/底层逻辑）
5. 标注情感共鸣点（会引发什么情绪：焦虑/希望/愤怒/认同/惊讶/好奇）
6. 标注适用场景（短视频/长视频/文章/直播/课程/金句）
7. 标注目标受众（职场新人/中年焦虑/情感困惑/创业者等）

输出格式（JSON）：
{
  "atomic_notes": [
    {
      "core_idea": "一句话核心观点（必须原创表达）",
      "detailed_explanation": "3-5句话详细解释",
      "original_quote": "原文引用（可选）",
      "thinking_model": "所属思维模型",
      "content_areas": ["职场", "人性"],
      "applicable_scenarios": ["口播", "文章"],
      "emotional_resonance": ["焦虑", "希望"],
      "target_audience": ["职场新人", "30岁焦虑"]
    }
  ]
}

重要：
- 只输出JSON，不要有其他文字
- 每个观点必须独立成卡
- 优先提取能引发情感共鸣的实用观点
- 放弃陈词滥调，保留反常识洞察

【待处理文本】
{content}
"""

    # Prompt 2: 内容转化生成
    CONTENT_TRANSFORMATION = """你是一位资深自媒体内容策划，专门为知识博主创作爆款内容。

博主定位：{ip_position}
目标平台：{platform}
目标受众：{target_audience}
受众痛点：{audience_pain}

任务：将以下知识卡片转化为可直接使用的{content_type}内容

【知识卡片】
{atomic_note}

输出要求：

1. **开头钩子**（前3秒/前50字必须抓住注意力）
   - 禁止："今天给大家分享..." / "这本书讲的是..."
   - 推荐：痛点共鸣 / 反常识观点 / 悬念提问 / 数据冲击

2. **核心观点**（书中理论+博主解读）
   - 先讲观点，再解释
   - 加入博主的个人态度（赞成/质疑/补充）
   - 用"人话"解释专业概念

3. **故事/案例**（让观点具象化）
   - 真实案例 > 书中案例 > 虚构案例
   - 有冲突、有转折、有结果
   - 让读者能代入

4. **行动建议**（观众能做什么）
   - 具体、可执行、立即可做
   - 分步骤（第一步...第二步...）
   - 强调改变后的好处

5. **结尾互动**（引导评论/转发）
   - 提问式结尾
   - 争议性观点邀请讨论
   - 承诺后续内容

风格要求：
- 口语化，像朋友聊天（"你有没有发现..." / "说实话..."）
- 有态度，不中立（"我认为..." / "说白了..."）
- 金句频出，易传播（适合截图发朋友圈）
- 避免"AI味"词汇：深刻、启示、值得深思、引人深省、综上所述

输出格式：
{
  "hook": "开头钩子",
  "core_content": "核心观点+解读",
  "story_case": "故事/案例",
  "actionable_advice": "行动建议",
  "ending_interaction": "结尾互动",
  "quotable_lines": ["金句1", "金句2"]  // 适合单独传播的金句
}
"""

    # Prompt 3: 跨书整合洞察
    CROSS_BOOK_INSIGHT = """你是一位跨学科思想家，擅长从不同书籍中发现深层联系。

任务：分析以下多本书籍的原子笔记，发现跨领域的通用规律

【输入笔记】
{atomic_notes}

输出要求：

1. **共同主题**（这些书都在回答什么核心问题）
   - 找出底层的人性/社会规律
   - 提炼成一句话洞察

2. **矛盾观点**（哪些观点相互冲突）
   - 不同作者对同一问题的不同看法
   - 如何调和或选择立场

3. **跨领域模型**（可以应用于多个领域的底层逻辑）
   - 如：复利效应（财富/知识/关系）
   - 如：马太效应（职场/教育/社会）

4. **系列内容建议**（基于这些洞察，可以做什么系列内容）
   - 主题系列（如"人性弱点系列"）
   - 对比系列（如"东西方思维差异"）
   - 应用系列（如"职场心理学30讲"）

5. **IP定位强化建议**
   - 基于这些洞察，如何强化个人品牌
   - 独特的观点组合是什么
   - 与同类博主的差异化

输出格式：可直接用于直播/深度文章的洞察报告（Markdown格式）
"""

    # Prompt 4: 情感共鸣优化
    EMOTIONAL_OPTIMIZATION = """你是一位情感文案专家，专门优化内容的情绪感染力。

任务：优化以下内容，增强情感共鸣

【原始内容】
{content}

【目标情感】{target_emotion}

优化要求：
1. 找到受众的"情绪开关"（他们最在意什么）
2. 用具体的细节代替抽象的概念
3. 创造"我也是这样"的认同感
4. 让读者感到被理解、被看见
5. 在痛点和希望之间找到平衡

技巧：
- 使用"你"字，直接对话
- 描述具体场景（时间、地点、动作）
- 加入感官细节（看到、听到、感受到）
- 使用对比（过去vs现在，别人vs自己）

输出：优化后的内容 + 优化说明
"""


# ═══════════════════════════════════════════════════════════════════════════
# IP内容生产引擎
# ═══════════════════════════════════════════════════════════════════════════

class IPContentEngine:
    """
    IP内容生产引擎
    将书籍转化为个人IP内容的完整流程
    """

    def __init__(self, ai_client, model_id: str):
        self.ai_client = ai_client
        self.model_id = model_id
        self.prompts = IPContentPrompts()

    # ─────────────────────────────────────────────────────────────────────
    # STEP 1: 原子化提取 (Capture)
    # ─────────────────────────────────────────────────────────────────────

    def extract_atomic_notes(
        self,
        book_title: str,
        chapter_title: str,
        content: str,
        page: str = ""
    ) -> List[AtomicNote]:
        """
        将书籍内容转化为原子笔记
        这是整个流程的输入端
        """
        prompt = self.prompts.ATOMIC_EXTRACTION.format(content=content)

        response = self.ai_client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": "你是专业的知识管理专家"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )

        result = response.choices[0].message.content
        parsed = self._parse_json(result)

        notes = []
        for i, note_data in enumerate(parsed.get("atomic_notes", [])):
            note = AtomicNote(
                id=f"{book_title}_{chapter_title}_{i}",
                source_book=book_title,
                source_chapter=chapter_title,
                source_page=page,
                core_idea=note_data.get("core_idea", ""),
                detailed_explanation=note_data.get("detailed_explanation", ""),
                original_quote=note_data.get("original_quote", ""),
                thinking_model=note_data.get("thinking_model", ""),
                content_areas=note_data.get("content_areas", []),
                applicable_scenarios=note_data.get("applicable_scenarios", []),
                emotional_resonance=note_data.get("emotional_resonance", []),
                target_audience=note_data.get("target_audience", []),
                related_notes=[],
                contradictions=[],
                created_at=datetime.now().isoformat(),
                used_count=0,
                quality_rating=3
            )
            notes.append(note)

        return notes

    # ─────────────────────────────────────────────────────────────────────
    # STEP 2: 内容转化 (Express)
    # ─────────────────────────────────────────────────────────────────────

    def transform_to_content(
        self,
        note: AtomicNote,
        content_type: ContentType,
        platform: str,
        ip_position: str,
        target_audience: str,
        audience_pain: str
    ) -> ContentPiece:
        """
        将原子笔记转化为可直接发布的内容
        """
        prompt = self.prompts.CONTENT_TRANSFORMATION.format(
            atomic_note=note.to_content_prompt(),
            content_type=content_type.value,
            platform=platform,
            ip_position=ip_position,
            target_audience=target_audience,
            audience_pain=audience_pain
        )

        response = self.ai_client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": "你是资深自媒体内容策划"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2500,
            temperature=0.8
        )

        result = response.choices[0].message.content
        parsed = self._parse_json(result)

        content = ContentPiece(
            id=f"content_{note.id}_{content_type.value}",
            content_type=content_type.value,
            platform=platform,
            hook=parsed.get("hook", ""),
            core_content=parsed.get("core_content", ""),
            story_case=parsed.get("story_case", ""),
            actionable_advice=parsed.get("actionable_advice", ""),
            ending_interaction=parsed.get("ending_interaction", ""),
            source_notes=[note.id],
            source_books=[note.source_book],
            created_at=datetime.now().isoformat()
        )

        # 更新笔记使用记录
        note.used_count += 1
        note.last_used = datetime.now().isoformat()

        return content

    # ─────────────────────────────────────────────────────────────────────
    # STEP 3: 跨书整合 (Distill)
    # ─────────────────────────────────────────────────────────────────────

    def generate_cross_book_insights(
        self,
        notes: List[AtomicNote]
    ) -> str:
        """
        从多本书的笔记中发现跨领域洞察
        """
        notes_text = "\n\n".join([
            f"笔记{i+1}:\n{note.to_content_prompt()}"
            for i, note in enumerate(notes[:20])  # 限制数量
        ])

        prompt = self.prompts.CROSS_BOOK_INSIGHT.format(atomic_notes=notes_text)

        response = self.ai_client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": "你是跨学科思想家"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7
        )

        return response.choices[0].message.content

    # ─────────────────────────────────────────────────────────────────────
    # STEP 4: 情感优化
    # ─────────────────────────────────────────────────────────────────────

    def optimize_emotion(
        self,
        content: str,
        target_emotion: EmotionalResonance
    ) -> str:
        """
        优化内容的情感共鸣
        """
        prompt = self.prompts.EMOTIONAL_OPTIMIZATION.format(
            content=content,
            target_emotion=target_emotion.value
        )

        response = self.ai_client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": "你是情感文案专家"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.8
        )

        return response.choices[0].message.content

    # ─────────────────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────────────────

    def _parse_json(self, text: str) -> Dict:
        """安全解析JSON"""
        import re

        # 清理markdown
        text = re.sub(r'^```(?:json)?\s*', '', text.strip())
        text = re.sub(r'\s*```\s*$', '', text.strip())

        # 替换中文引号
        text = text.replace('\u201c', '"').replace('\u201d', '"')

        try:
            return json.loads(text)
        except:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {}


# ═══════════════════════════════════════════════════════════════════════════
# PARA组织系统
# ═══════════════════════════════════════════════════════════════════════════

class PARAOrganizer:
    """
    PARA方法组织系统
    Projects - Areas - Resources - Archives
    """

    def __init__(self):
        self.projects = {}      # 当前进行中的内容项目
        self.areas = {          # 持续关注的领域
            "职场": [],
            "情感": [],
            "人性": [],
            "社会": [],
            "底层逻辑": []
        }
        self.resources = {}     # 资源库（原子笔记）
        self.archives = {}      # 归档

    def add_note_to_area(self, note: AtomicNote):
        """将笔记按领域分类"""
        for area in note.content_areas:
            if area in self.areas:
                self.areas[area].append(note)

    def create_content_project(
        self,
        title: str,
        content_type: str,
        target_areas: List[str],
        note_count: int = 5
    ) -> Dict:
        """
        创建内容项目
        从相关领域提取笔记，组合成系列内容
        """
        project_notes = []

        for area in target_areas:
            if area in self.areas:
                # 按质量和使用次数排序
                sorted_notes = sorted(
                    self.areas[area],
                    key=lambda n: (n.quality_rating, -n.used_count),
                    reverse=True
                )
                project_notes.extend(sorted_notes[:note_count])

        return {
            "title": title,
            "content_type": content_type,
            "target_areas": target_areas,
            "notes": project_notes,
            "status": "draft"
        }

    def get_recommendations(self, area: str) -> List[AtomicNote]:
        """
        推荐可用于内容的笔记
        策略：高质量 + 低使用次数
        """
        if area not in self.areas:
            return []

        notes = self.areas[area]
        # 按 (质量 × 新鲜度) 排序
        scored_notes = [
            (n, n.quality_rating * (1 / (1 + n.used_count)))
            for n in notes
        ]
        scored_notes.sort(key=lambda x: x[1], reverse=True)

        return [n for n, _ in scored_notes[:10]]


# ═══════════════════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════════════════

def create_ip_content_system(ai_client, model_id: str = "gpt-4") -> Tuple[IPContentEngine, PARAOrganizer]:
    """
    创建完整的IP内容生产系统

    Returns:
        (内容引擎, PARA组织器)
    """
    engine = IPContentEngine(ai_client, model_id)
    organizer = PARAOrganizer()
    return engine, organizer
