"""
测试新的智能提取模块
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\backend")

print("=" * 60)
print("测试智能提取模块")
print("=" * 60)

# 测试1: Chunking 模块
print("\n[测试1] 分层 Chunking 模块")
try:
    from chunking import BookStructureExtractor, SemanticChunker, chunk_book_text

    # 测试文本
    test_text = """
第一章 认知升级的重要性

在这个快速变化的时代，认知决定了一个人的上限。
很多人工作十年，其实只是重复了一年的经验十次。
真正的成长来自于认知的升级。

认知升级有三个层次：
第一层次是知识的积累，多读书，多学习。
第二层次是思维方式的转变，从线性思维到系统思维。
第三层次是心智模式的改变，从根本上改变看待世界的方式。

第二章 如何突破职场瓶颈

职场瓶颈是每个人都会遇到的。
突破瓶颈的关键在于主动求变。
不要等到被裁员才开始思考未来。

具体行动建议：
1. 每半年更新一次简历，了解市场行情
2. 主动承担有挑战性的项目
3. 建立跨部门的人脉网络
4. 培养可迁移的核心技能

第三章 人性的弱点与优势

了解人性是职场生存的基本功。
人性有弱点：贪婪、恐惧、懒惰、虚荣。
但也有优势：创造力、同理心、合作精神。

高手懂得利用人性的弱点来达成目标，
同时激发人性的优势来创造价值。
"""

    result = chunk_book_text(test_text, "测试书籍", max_chunk_size=500)

    print(f"[OK] 章节数: {result['chapter_count']}")
    print(f"[OK] Chunk 数: {result['chunk_count']}")
    print(f"[OK] 章节列表:")
    for ch in result["chapters"]:
        print(f"  - {ch['title']} (level={ch['level']}, chunks={ch['chunk_count']})")

except Exception as e:
    print(f"[FAIL] 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试2: 质量评分模块
print("\n[测试2] 质量评分模块")
try:
    from quality_control import MaterialQualityChecker, MaterialRouter

    checker = MaterialQualityChecker()

    # 测试素材
    test_material = {
        "category": "quote",
        "content": "真正的成长来自于认知的升级，而不是简单的重复劳动。",
        "metadata": {
            "risk": "safe",
            "scene": "viral",
            "cost": "zero",
            "timeliness": "long"
        }
    }

    score, suggestions = checker.check(test_material)

    print(f"[OK] 完整度: {score.completeness}")
    print(f"[OK] 唯一性: {score.uniqueness}")
    print(f"[OK] IP契合度: {score.ip_fit}")
    print(f"[OK] 可执行性: {score.actionable}")
    print(f"[OK] 风险等级: {score.risk_level}")
    print(f"[OK] 综合得分: {score.overall}")
    print(f"[OK] 改进建议: {suggestions}")

    # 路由测试
    router = MaterialRouter()
    decision, reason = router.route(test_material, score)
    print(f"[OK] 路由决策: {decision} - {reason}")

except Exception as e:
    print(f"[FAIL] 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 提取 Pipeline（需要 API key，可能失败）
print("\n[测试3] 多轮提取 Pipeline")
try:
    from extraction_pipeline import MultiRoundExtractionPipeline
    print("[OK] 模块导入成功")
    print("  (实际提取测试需要配置 API key)")
except Exception as e:
    print(f"[FAIL] 失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
