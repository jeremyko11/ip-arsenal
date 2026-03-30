"""
IP Arsenal 个人IP内容生产系统 - 完整演示

演示场景：从一本书到IP内容的完整流程
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\backend")

print("=" * 80)
print("IP Arsenal 个人IP内容生产系统 - 完整演示")
print("=" * 80)
print("\n本演示展示：从书籍 → 原子笔记 → IP内容的完整流程")
print("基于：Zettelkasten + PARA + 费曼学习法 + 跨学科思维")

# 模拟书籍内容（实际使用时从PDF提取）
sample_book_content = """
第三章：职场中的认知偏差

很多人在职场上混不好，不是因为能力不行，而是因为陷入了认知偏差。

【现状偏差】

人们倾向于维持现状，即使改变会带来更好的结果。

比如，很多人明明不喜欢现在的工作，但因为"已经做了这么多年"，
就不愿意转行。这就是被现状偏差困住了。

实际上，转行成本没有你想象的那么高，
而继续留在不喜欢的行业，机会成本才是巨大的。

【幸存者偏差】

我们只看到成功的人，却看不到失败的人。

看到别人创业成功就辞职创业，
却没看到99%的创业者都失败了。

这种偏差让我们高估了成功的概率，做出不理性的决策。

【确认偏误】

人们只相信自己愿意相信的，对相反的证据视而不见。

在职场上，这意味着：
- 觉得自己被低估的人，会不断寻找"领导针对我"的证据
- 而忽略了自己确实能力不足的事实

打破确认偏误的方法是：主动寻找反面证据。

【行动建议】

1. 定期审视自己的职业选择，问自己：如果我现在没做这份工作，我还会选择它吗？
2. 做重大决策时，主动寻找反面案例
3. 建立一个"我可能错了"的思维习惯

记住：认知偏差不是你笨，而是大脑的默认设置。
意识到它们的存在，就是改变的开始。
"""

# ═══════════════════════════════════════════════════════════════════════════
# 演示 1: 原子化提取
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("【演示 1】原子化提取 - 将书籍转化为知识卡片")
print("=" * 80)

from ip_content_system import AtomicNote, ContentType, EmotionalResonance, ThinkingModel

# 模拟提取结果（实际使用时调用AI）
mock_atomic_notes = [
    AtomicNote(
        id="book1_ch3_001",
        source_book="职场心理学",
        source_chapter="第三章：职场中的认知偏差",
        source_page="45",
        core_idea="现状偏差让人困在不喜欢的工作中，机会成本比转行成本更高",
        detailed_explanation="人们因为'已经做了这么多年'而不愿改变，但实际上继续留在错误赛道的代价远大于转行的代价。",
        original_quote="转行成本没有你想象的那么高，而继续留在不喜欢的行业，机会成本才是巨大的",
        thinking_model="认知偏差",
        content_areas=["职场", "心理学", "底层逻辑"],
        applicable_scenarios=["短视频", "文章", "直播"],
        emotional_resonance=["焦虑", "希望", "认同"],
        target_audience=["职场迷茫者", "30岁焦虑", "想转行的人"],
        related_notes=[],
        contradictions=[],
        created_at="2024-01-15T10:00:00",
        used_count=0,
        quality_rating=5
    ),
    AtomicNote(
        id="book1_ch3_002",
        source_book="职场心理学",
        source_chapter="第三章：职场中的认知偏差",
        source_page="47",
        core_idea="幸存者偏差让我们高估成功概率，因为失败的人不会被看见",
        detailed_explanation="我们看到创业成功的人发的朋友圈，却看不到失败者的沉默。这种选择性观察导致我们做出不理性的决策。",
        original_quote="看到别人创业成功就辞职创业，却没看到99%的创业者都失败了",
        thinking_model="认知偏差",
        content_areas=["职场", "底层逻辑", "社会"],
        applicable_scenarios=["短视频", "文章"],
        emotional_resonance=["惊讶", "焦虑"],
        target_audience=["创业者", "职场新人", "冲动决策者"],
        related_notes=[],
        contradictions=[],
        created_at="2024-01-15T10:05:00",
        used_count=0,
        quality_rating=5
    ),
    AtomicNote(
        id="book1_ch3_003",
        source_book="职场心理学",
        source_chapter="第三章：职场中的认知偏差",
        source_page="49",
        core_idea="确认偏误让人只相信自己愿意相信的，主动寻找反面证据才能打破",
        detailed_explanation="觉得自己被低估的人会不断寻找'领导针对我'的证据，而忽略自己能力不足的事实。打破的方法是主动质疑自己。",
        original_quote="打破确认偏误的方法是：主动寻找反面证据",
        thinking_model="认知偏差",
        content_areas=["职场", "心理学", "人性"],
        applicable_scenarios=["文章", "直播", "课程"],
        emotional_resonance=["认同", "empowerment"],
        target_audience=["职场困惑者", "自我提升者"],
        related_notes=[],
        contradictions=[],
        created_at="2024-01-15T10:10:00",
        used_count=0,
        quality_rating=4
    )
]

print(f"\n[OK] 从书籍中提取了 {len(mock_atomic_notes)} 张原子笔记\n")

for i, note in enumerate(mock_atomic_notes, 1):
    print(f"卡片 {i}: {note.id}")
    print(f"  核心观点: {note.core_idea}")
    print(f"  思维模型: {note.thinking_model}")
    print(f"  适用领域: {', '.join(note.content_areas)}")
    print(f"  情感共鸣: {', '.join(note.emotional_resonance)}")
    print(f"  目标受众: {', '.join(note.target_audience)}")
    print(f"  适用场景: {', '.join(note.applicable_scenarios)}")
    print()

# ═══════════════════════════════════════════════════════════════════════════
# 演示 2: PARA组织
# ═══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("【演示 2】PARA组织 - 按领域分类知识")
print("=" * 80)

from ip_content_system import PARAOrganizer

organizer = PARAOrganizer()

# 将笔记分类到不同领域
for note in mock_atomic_notes:
    organizer.add_note_to_area(note)

print("\n[OK] 笔记已按PARA方法分类:\n")

for area, notes in organizer.areas.items():
    if notes:
        print(f"领域: {area}")
        for note in notes:
            print(f"  - {note.core_idea[:40]}...")
        print()

# 推荐可用于内容的笔记
print("[推荐] 职场领域可优先使用的笔记（高质量+低使用次数）:")
recommendations = organizer.get_recommendations("职场")
for note in recommendations:
    print(f"  - {note.core_idea[:50]}... (质量:{note.quality_rating}星)")

# ═══════════════════════════════════════════════════════════════════════════
# 演示 3: 内容项目创建
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("【演示 3】创建内容项目 - 系列内容策划")
print("=" * 80)

project = organizer.create_content_project(
    title="职场认知偏差系列",
    content_type="短视频",
    target_areas=["职场", "心理学"],
    note_count=3
)

print(f"\n[OK] 创建内容项目: {project['title']}")
print(f"  内容类型: {project['content_type']}")
print(f"  目标领域: {', '.join(project['target_areas'])}")
print(f"  包含笔记: {len(project['notes'])} 条")
print("\n  项目笔记列表:")
for note in project['notes']:
    print(f"    - {note.core_idea[:40]}...")

# ═══════════════════════════════════════════════════════════════════════════
# 演示 4: 内容转化示例
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("【演示 4】内容转化 - 原子笔记 → 口播稿")
print("=" * 80)

# 模拟生成的口播稿
sample_content = {
    "hook": "你有没有发现，很多人明明不喜欢现在的工作，却因为'已经做了这么多年'就不敢转行？",
    "core_content": """这叫做'现状偏差'——我们的大脑天生倾向于维持现状，即使改变会带来更好的结果。

说实话，转行成本没有你想象的那么高。真正可怕的是机会成本——你继续留在错误赛道上的每一天，都在浪费成为更好的自己的可能。""",
    "story_case": "我认识一个做财务的朋友，30岁那年从零开始学编程。所有人都说她疯了。三年后，她在一家AI公司做产品经理，收入是原来的三倍。她说：'后悔的不是转行，而是转得太晚。'",
    "actionable_advice": "如果你也在纠结要不要改变，问自己一个问题：如果我现在没做这份工作，明天还会选择它吗？如果答案是否定的，那你知道该怎么做了。",
    "ending_interaction": "你现在的工作，是你真正想要的吗？评论区说说你的想法。",
    "quotable_lines": [
        "转行成本没有你想象的那么高，机会成本才是巨大的",
        "后悔的不是转行，而是转得太晚"
    ]
}

print("\n[OK] 生成的口播稿结构:\n")
print(f"【开头钩子】\n{sample_content['hook']}\n")
print(f"【核心观点】\n{sample_content['core_content']}\n")
print(f"【故事案例】\n{sample_content['story_case']}\n")
print(f"【行动建议】\n{sample_content['actionable_advice']}\n")
print(f"【结尾互动】\n{sample_content['ending_interaction']}\n")
print(f"【传播金句】")
for line in sample_content['quotable_lines']:
    print(f"  - {line}")

# ═══════════════════════════════════════════════════════════════════════════
# 演示 5: 跨书整合
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("【演示 5】跨书整合 - 发现深层洞察")
print("=" * 80)

cross_book_insight = """
## 跨书洞察报告

### 共同主题
多本心理学和职场书籍都在回答同一个问题：
**为什么聪明人也会做傻事？**

答案是：认知偏差是大脑的默认设置，与智商无关。

### 跨领域模型："认知偏差-决策失误"模型

这个模型可以解释：
- **职场**：为什么有能力的人升不上去（现状偏差）
- **情感**：为什么明知道对方不合适还是放不下（沉没成本）
- **投资**：为什么散户总是高买低卖（追涨杀跌的认知偏差）
- **社会**：为什么谣言传播得比真相快（确认偏误）

### 系列内容建议

**系列1：「认知偏差坑了你多少次」**
- 每期讲一个认知偏差
- 结合职场/情感/投资场景
- 给出具体的破解方法

**系列2：「高手如何思考」**
- 对比普通人和高手的思维模式
- 展示如何绕过认知偏差
- 可做成付费课程

### IP定位强化

你的独特价值：
- 不是简单罗列心理学概念
- 而是用"认知偏差"这个 lens 解读职场、情感、社会现象
- 帮普通人 upgrade 自己的思维模式

**一句话定位**：帮你识别大脑里的bug，升级认知系统。
"""

print(cross_book_insight)

# ═══════════════════════════════════════════════════════════════════════════
# 总结
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("系统总结")
print("=" * 80)

print("""
【IP Arsenal 个人IP内容生产系统】

核心流程：
  书籍 → 原子笔记 → PARA组织 → 内容项目 → IP内容 → 发布变现

关键方法：
  1. Zettelkasten（卡片笔记法）
     - 每个观点一张卡片，独立完整
     - 卡片间建立链接，形成知识网络

  2. PARA组织法
     - Projects: 当前进行的内容项目
     - Areas: 持续关注的领域（职场/情感/人性/社会）
     - Resources: 原子笔记库
     - Archives: 已完成的项目

  3. 费曼学习法
     - 用自己的话重新表达
     - 让外行也能听懂
     - 输出倒逼输入

  4. 跨学科思维
     - 建立思维模型库（认知偏差、复利效应等）
     - 不同书籍的观点归入同一模型
     - 发现跨领域的通用规律

你的IP定位建议：
  "认知升级教练" - 用心理学、底层逻辑解读职场/情感/社会现象
  帮助普通人识别认知偏差，升级思维模式

变现路径：
  短视频（引流）→ 直播（建立信任）→ 课程（变现）→ 社群（持续收入）
""")

print("=" * 80)
print("演示完成")
print("=" * 80)
