"""
测试 IP Arsenal Extractor v2.0
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\backend")

print("=" * 70)
print("IP Arsenal Extractor v2.0 测试")
print("=" * 70)

# 测试数据
test_book = """
# 第一章：认知升级的重要性

在这个快速变化的时代，认知决定了一个人的上限。

> "你永远赚不到超出你认知范围的钱"

很多人工作十年，其实只是重复了一年的经验十次。真正的成长来自于认知的升级。

## 认知升级的三个层次

第一层次是知识的积累：
- 多读书，多学习
- 建立知识体系
- 跨界学习

第二层次是思维方式的转变：
- 从线性思维到系统思维
- 从二元对立到多元包容
- 从短期导向到长期主义

第三层次是心智模式的改变：
- 从根本上改变看待世界的方式
- 改变自我认知
- 改变与他人的关系

# 第二章：突破职场瓶颈

## 案例：张明的转型之路

张明在一家互联网公司工作了5年，从初级工程师升到高级工程师后，陷入了瓶颈。

**背景**：技术能力强，但缺乏商业思维
**挑战**：不知道如何在35岁前实现职级跃迁
**行动**：
1. 主动申请参与产品决策会议
2. 学习商业分析，考取MBA
3. 建立跨部门影响力

**结果**：两年后晋升为技术总监，薪资翻倍

**启示**：技术人突破瓶颈的关键是培养商业思维

## 核心观点

职场瓶颈的本质是能力模型的固化。突破瓶颈需要：
- 识别新的能力维度
- 主动承担挑战性任务
- 建立跨领域的人脉网络

# 第三章：人性的洞察

## 人性的弱点

1. **贪婪**：总想获得更多，不愿放弃
2. **恐惧**：对损失的恐惧大于对收益的渴望
3. **懒惰**：倾向于选择省力的方案
4. **虚荣**：在意他人的评价

## 高手如何利用人性

真正的高手不是对抗人性，而是：
- 理解人性的规律
- 设计顺应人性的系统
- 在关键节点克服人性的弱点

> "了解人性的弱点，是为了更好地保护自己和他人"
"""

# 测试 1: 文档解析
print("\n[测试 1] 文档解析")
try:
    from extractor_v2 import DocumentParser, ContentType

    parser = DocumentParser()
    elements = parser.parse(test_book)

    print(f"[OK] 解析到 {len(elements)} 个元素")

    # 统计各类型
    type_counts = {}
    for e in elements:
        type_counts[e.type.value] = type_counts.get(e.type.value, 0) + 1

    print("[OK] 元素类型分布:")
    for t, c in type_counts.items():
        print(f"  - {t}: {c}")

    # 显示标题
    headings = [e for e in elements if e.type == ContentType.HEADING]
    print(f"[OK] 检测到 {len(headings)} 个标题:")
    for h in headings:
        print(f"  - {'#' * h.level} {h.content[:30]}")

except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()

# 测试 2: 智能分块
print("\n[测试 2] 智能分块")
try:
    from extractor_v2 import SemanticChunker

    chunker = SemanticChunker()
    chunks = chunker.chunk(elements, "测试书籍")

    print(f"[OK] 生成 {len(chunks)} 个 chunks")

    for i, chunk in enumerate(chunks):
        print(f"\n  Chunk {i+1}: {chunk.chunk_id}")
        print(f"    章节: {chunk.chapter_title}")
        print(f"    长度: {len(chunk.text)} 字符")
        print(f"    预览: {chunk.text[:60]}...")
        if chunk.prev_chunk:
            print(f"    前向: {chunk.prev_chunk}")
        if chunk.next_chunk:
            print(f"    后向: {chunk.next_chunk}")

except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()

# 测试 3: 质量验证
print("\n[测试 3] 质量验证")
try:
    from extractor_v2 import QualityValidator, ExtractedMaterial

    validator = QualityValidator()

    # 测试素材
    test_materials = [
        ExtractedMaterial(
            id="test1",
            category="quote",
            content="认知决定上限",
            context="第一章",
            source_chapter="第一章",
            source_chunk="ch001",
            metadata={},
            quality_score={}
        ),
        ExtractedMaterial(
            id="test2",
            category="case",
            content='{"name": "张明转型", "challenge": "职场瓶颈", "action": "学习商业", "result": "晋升总监"}',
            context="第二章",
            source_chapter="第二章",
            source_chunk="ch002",
            metadata={},
            quality_score={}
        ),
        ExtractedMaterial(
            id="test3",
            category="viewpoint",
            content="职场瓶颈的本质是能力模型的固化",
            context="第二章",
            source_chapter="第二章",
            source_chunk="ch002",
            metadata={},
            quality_score={}
        )
    ]

    for m in test_materials:
        result = validator.validate(m)
        print(f"\n  [OK] {m.category}: {m.content[:30]}...")
        print(f"      完整度: {result['scores']['completeness']:.2f}")
        print(f"      IP契合: {result['scores']['ip_fit']:.2f}")
        print(f"      可执行: {result['scores']['actionable']:.2f}")
        print(f"      综合分: {result['overall']:.2f}")
        print(f"      状态: {result['status']}")

except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()

# 测试 4: 完整流程（需要 API key）
print("\n[测试 4] 完整流程")
print("[SKIP] 需要配置 API key，跳过实际提取测试")
print("  (如需测试，请配置 OpenAI API key)")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
print("\nv2.0 特性概览:")
print("  ✓ 文档解析 - 识别标题、列表、引用等多种元素")
print("  ✓ 智能分块 - 按章节语义切分，保持上下文关联")
print("  ✓ 结构化提取 - JSON Schema 约束，输出稳定")
print("  ✓ 知识图谱 - 实体关系提取")
print("  ✓ 质量验证 - 多维度评分，智能路由")
