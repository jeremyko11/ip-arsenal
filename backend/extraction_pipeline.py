"""
多轮迭代提取 Pipeline - 深度书籍内容提取

核心流程：
Round 1: 结构理解（轻量模型）- 提取大纲、核心论点
Round 2: 逐章深度提取（强模型）- 金句/案例/观点/行动
Round 3: 跨章节关联分析（强模型）- 主题关联、观点演变
Round 4: IP化选题生成（创意模型）- 爆款选题、平台适配
"""

import json
import re
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class ExtractionResult:
    """提取结果数据结构"""
    round_name: str
    model_used: str
    content: str
    structured_data: Dict
    confidence: float = 0.0

    def to_dict(self):
        return {
            "round_name": self.round_name,
            "model_used": self.model_used,
            "content": self.content,
            "structured_data": self.structured_data,
            "confidence": self.confidence
        }


class MultiRoundExtractionPipeline:
    """多轮迭代提取流程"""

    def __init__(
        self,
        primary_client,
        fallback_client,
        fallback2_client,
        primary_model: str,
        fallback_model: str,
        fallback2_model: str,
        ip_direction: str = "职场认知升级 / 人性洞察 / 个人成长破局"
    ):
        self.clients = {
            "primary": (primary_client, primary_model),
            "fallback": (fallback_client, fallback_model),
            "fallback2": (fallback2_client, fallback2_model)
        }
        self.ip_direction = ip_direction

    def _call_ai(
        self,
        system_prompt: str,
        user_prompt: str,
        model_tier: str = "primary",
        max_tokens: int = 4000,
        temperature: float = 0.7,
        timeout_secs: int = 180
    ) -> tuple[str, str]:
        """调用 AI，支持降级"""
        import concurrent.futures

        client, model_id = self.clients[model_tier]

        def _do_call():
            resp = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return resp.choices[0].message.content or ""

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_call)
            try:
                result = future.result(timeout=timeout_secs)
                # 清理 think 标签
                result = self._strip_think_tags(result)
                return result, model_id
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"AI接口超过{timeout_secs}秒未响应")

    def _strip_think_tags(self, text: str) -> str:
        """过滤推理过程标签"""
        text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[思考\][\s\S]*?\[/思考\]', '', text, flags=re.IGNORECASE)
        return text.strip()

    def _try_all_models(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> tuple[str, str]:
        """三级模型自动降级"""
        errors = []

        for tier in ["primary", "fallback", "fallback2"]:
            try:
                result, model = self._call_ai(
                    system_prompt, user_prompt, tier, max_tokens, temperature
                )
                if result and len(result.strip()) > 50:
                    return result, model
            except Exception as e:
                errors.append(f"{tier}: {str(e)[:100]}")
                continue

        raise RuntimeError(f"所有模型失败: {' | '.join(errors)}")

    # =========================================================================
    # Round 1: 结构理解
    # =========================================================================

    ROUND1_SYSTEM_PROMPT = """你是一位专业的书籍结构分析师。
你的任务是快速理解一本书的整体结构，提取核心框架信息。

输出要求：
1. 只输出结构分析，不输出详细内容
2. 使用简洁的 JSON 格式
3. 确保信息准确，宁缺毋滥

禁止：
- 不要输出总结性文字
- 不要输出思考过程
- 不要输出 markdown 代码块标记"""

    ROUND1_USER_TEMPLATE = """请分析《{book_name}》的整体结构。

【文本内容（前30%采样）】
{text_sample}

请输出以下 JSON 格式：
{{
    "core_thesis": "本书核心论点（1-2句话）",
    "target_audience": "目标读者画像",
    "problem_solved": "本书解决的核心问题",
    "chapters": [
        {{
            "title": "章节标题",
            "core_idea": "该章核心观点（1句话）",
            "key_concepts": ["关键概念1", "关键概念2"]
        }}
    ],
    "book_structure": "整体结构类型：问题解决型/故事叙事型/理论框架型/实践指南型",
    "author_stance": "作者立场/态度"
}}"""

    def round1_structure_understanding(
        self,
        book_name: str,
        text_sample: str,
        progress_callback: Optional[Callable] = None
    ) -> ExtractionResult:
        """
        第一轮：结构理解（轻量快速）

        Args:
            book_name: 书名
            text_sample: 文本采样（前30%）
            progress_callback: 进度回调函数

        Returns:
            ExtractionResult
        """
        if progress_callback:
            progress_callback("round1", 10, "正在理解书籍整体结构...")

        user_prompt = self.ROUND1_USER_TEMPLATE.format(
            book_name=book_name,
            text_sample=text_sample[:15000]  # 限制长度
        )

        content, model = self._try_all_models(
            self.ROUND1_SYSTEM_PROMPT,
            user_prompt,
            max_tokens=2000,
            temperature=0.3  # 低温度，更确定
        )

        # 解析 JSON
        structured = self._extract_json(content)

        if progress_callback:
            progress_callback("round1", 25, f"结构理解完成（使用 {model}）")

        return ExtractionResult(
            round_name="structure_understanding",
            model_used=model,
            content=content,
            structured_data=structured,
            confidence=0.85
        )

    # =========================================================================
    # Round 2: 逐章深度提取
    # =========================================================================

    ROUND2_SYSTEM_PROMPT = """你是一位专业的内容提取专家。
你的任务是从书籍章节中提取高质量的素材，分类整理。

提取原则：
1. 忠实原文，不编造内容
2. 优先提取具体、可操作的素材
3. 每个素材必须标注风险等级和适用场景
4. 宁缺毋滥，质量优先

输出格式：按指定 JSON 格式输出"""

    ROUND2_USER_TEMPLATE = """请深度提取《{book_name}》第{chapter_index}章《{chapter_title}》的素材。

【本章内容】
{chapter_content}

【全书背景】
核心论点：{core_thesis}
目标读者：{target_audience}

请提取以下内容（JSON格式）：
{{
    "quotes": [
        {{
            "text": "金句原文",
            "context": "上下文/出处",
            "risk": "safe/context/forbidden",
            "scene": "viral/heal/deep",
            "cost": "zero/mid/high",
            "timeliness": "long/update/expired"
        }}
    ],
    "cases": [
        {{
            "name": "案例名称",
            "conflict": "冲突/背景",
            "action": "关键行动",
            "result": "结果",
            "insight": "启示",
            "risk": "safe/context/forbidden",
            "timeliness": "long/update/expired"
        }}
    ],
    "viewpoints": [
        {{
            "title": "观点标题",
            "evidence": "书中依据",
            "angle": "IP化角度",
            "conflict_warning": "可能的反驳观点",
            "risk": "safe/context/forbidden",
            "timeliness": "long/update/expired"
        }}
    ],
    "actions": [
        {{
            "name": "行动名称",
            "steps": ["步骤1", "步骤2", "步骤3"],
            "scenario": "适用场景",
            "risk_hint": "风险提示",
            "cost": "zero/mid/high"
        }}
    ]
}}"""

    def round2_chapter_extraction(
        self,
        book_name: str,
        chapter: Dict,
        book_structure: Dict,
        progress_callback: Optional[Callable] = None
    ) -> ExtractionResult:
        """
        第二轮：逐章深度提取

        Args:
            book_name: 书名
            chapter: 章节信息（含 content）
            book_structure: Round 1 的结构信息
            progress_callback: 进度回调

        Returns:
            ExtractionResult
        """
        chapter_title = chapter.get("title", "未知章节")
        chapter_index = chapter.get("index", 0)

        if progress_callback:
            progress_callback(
                "round2",
                30 + int((chapter_index / max(1, chapter.get("total_chapters", 1))) * 40),
                f"正在提取第{chapter_index+1}章《{chapter_title}》..."
            )

        user_prompt = self.ROUND2_USER_TEMPLATE.format(
            book_name=book_name,
            chapter_index=chapter_index + 1,
            chapter_title=chapter_title,
            chapter_content=chapter.get("content", "")[:20000],
            core_thesis=book_structure.get("core_thesis", ""),
            target_audience=book_structure.get("target_audience", "")
        )

        content, model = self._try_all_models(
            self.ROUND2_SYSTEM_PROMPT,
            user_prompt,
            max_tokens=4000,
            temperature=0.5
        )

        structured = self._extract_json(content)

        return ExtractionResult(
            round_name=f"chapter_extraction_{chapter_index}",
            model_used=model,
            content=content,
            structured_data=structured,
            confidence=0.80
        )

    def round2_all_chapters(
        self,
        book_name: str,
        chapters: List[Dict],
        book_structure: Dict,
        progress_callback: Optional[Callable] = None,
        max_workers: int = 3
    ) -> List[ExtractionResult]:
        """并行处理所有章节（最多 max_workers 并发）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = []

        def process_chapter(chapter):
            try:
                return self.round2_chapter_extraction(
                    book_name, chapter, book_structure, progress_callback
                )
            except Exception as e:
                print(f"Chapter {chapter.get('title')} extraction failed: {e}")
                return None

        # 有限并行执行，避免 API 限流
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_chapter, ch): ch for ch in chapters}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        # 按章节顺序排序（保持与输入一致）
        results.sort(key=lambda r: r.structured_data.get('chapter_index', 0) if r.structured_data else 0)
        return results

    # =========================================================================
    # Round 3: 跨章节关联分析
    # =========================================================================

    ROUND3_SYSTEM_PROMPT = """你是一位深度的内容分析师。
你的任务是发现书籍中跨章节的关联和深层结构。

分析维度：
1. 贯穿全书的主题线索
2. 观点的演变和递进
3. 章节之间的逻辑关联
4. 潜在的矛盾或张力
5. 可跨章节组合的内容

输出要求：分析性洞察，而非简单罗列"""

    ROUND3_USER_TEMPLATE = """请对《{book_name}》进行跨章节关联分析。

【全书结构】
{book_structure}

【各章核心观点】
{chapter_ideas}

【提取到的关键素材概览】
- 金句数量：{quote_count}
- 案例数量：{case_count}
- 观点数量：{viewpoint_count}

请输出以下分析（JSON格式）：
{{
    "cross_chapter_themes": [
        {{
            "theme": "主题名称",
            "chapters_involved": ["章节1", "章节2"],
            "evolution": "该主题在各章的演变",
            "key_insight": "核心洞察"
        }}
    ],
    "viewpoint_tensions": [
        {{
            "tension": "观点张力/矛盾",
            "viewpoint_a": "观点A",
            "viewpoint_b": "观点B",
            "resolution": "可能的调和方案"
        }}
    ],
    "combinable_content": [
        {{
            "combination": "可组合的内容",
            "sources": ["来源1", "来源2"],
            "synergy": "组合后的增强效果"
        }}
    ],
    "hidden_gems": [
        {{
            "content": "被忽视的宝藏内容",
            "location": "所在章节",
            "value": "为什么有价值"
        }}
    ]
}}"""

    def round3_cross_chapter_analysis(
        self,
        book_name: str,
        book_structure: Dict,
        chapter_results: List[ExtractionResult],
        progress_callback: Optional[Callable] = None
    ) -> ExtractionResult:
        """第三轮：跨章节关联分析"""
        if progress_callback:
            progress_callback("round3", 75, "正在进行跨章节关联分析...")

        # 统计素材
        quote_count = sum(
            len(r.structured_data.get("quotes", []))
            for r in chapter_results
        )
        case_count = sum(
            len(r.structured_data.get("cases", []))
            for r in chapter_results
        )
        viewpoint_count = sum(
            len(r.structured_data.get("viewpoints", []))
            for r in chapter_results
        )

        # 构建各章核心观点摘要
        chapter_ideas = []
        for i, ch in enumerate(book_structure.get("chapters", [])):
            chapter_ideas.append(f"第{i+1}章《{ch.get('title')}》：{ch.get('core_idea', '')}")

        user_prompt = self.ROUND3_USER_TEMPLATE.format(
            book_name=book_name,
            book_structure=json.dumps(book_structure, ensure_ascii=False)[:3000],
            chapter_ideas="\n".join(chapter_ideas),
            quote_count=quote_count,
            case_count=case_count,
            viewpoint_count=viewpoint_count
        )

        content, model = self._try_all_models(
            self.ROUND3_SYSTEM_PROMPT,
            user_prompt,
            max_tokens=4000,
            temperature=0.6
        )

        structured = self._extract_json(content)

        if progress_callback:
            progress_callback("round3", 85, "跨章节分析完成")

        return ExtractionResult(
            round_name="cross_chapter_analysis",
            model_used=model,
            content=content,
            structured_data=structured,
            confidence=0.75
        )

    # =========================================================================
    # Round 4: IP化选题生成
    # =========================================================================

    ROUND4_SYSTEM_PROMPT = """你是一位资深的 IP 内容策划专家。
你的任务是将书籍内容转化为爆款选题，适配不同平台特性。

IP方向：{ip_direction}

平台特性：
- 抖音：3秒抓人，情绪共鸣，视觉化表达
- 视频号：深度与温度并存，适合35+人群
- 小红书：实用干货，高颜值排版，女性向
- 公众号：深度长文，逻辑严密，金句频出

选题原则：
1. 每个选题必须有明确的受众痛点
2. 标题要让人忍不住点击
3. 内容角度要新颖，避免陈词滥调
4. 必须基于书中真实内容，不编造"""

    ROUND4_USER_TEMPLATE = """请为《{book_name}》生成 IP 化爆款选题。

【全书核心信息】
核心论点：{core_thesis}
目标受众：{target_audience}

【提取到的优质素材】
金句精选：
{quotes_sample}

案例精选：
{cases_sample}

观点精选：
{viewpoints_sample}

请输出以下选题（JSON格式）：
{{
    "topics": [
        {{
            "title": "爆款标题（可直接使用）",
            "platform": "抖音/视频号/小红书/公众号",
            "content_type": "口播/图文/短视频/长文",
            "hook": {{
                "opening": "开头钩子（前3秒/前50字）",
                "ending": "结尾互动设计"
            }},
            "source_materials": ["引用的素材1", "引用的素材2"],
            "angle": "内容角度/切入点",
            "target_pain": "解决的受众痛点",
            "estimated_viral_score": "预估爆款指数 1-10"
        }}
    ],
    "content_series": [
        {{
            "series_name": "系列名称",
            "episodes": ["第1集标题", "第2集标题", "第3集标题"],
            "theme": "系列主题",
            "platform": "主要发布平台"
        }}
    ],
    "repurposing_plan": {{
        "one_to_many": [
            {{
                "source_content": "原始素材",
                "derivatives": ["衍生形式1", "衍生形式2"]
            }}
        ]
    }}
}}"""

    def round4_ip_topic_generation(
        self,
        book_name: str,
        book_structure: Dict,
        chapter_results: List[ExtractionResult],
        progress_callback: Optional[Callable] = None
    ) -> ExtractionResult:
        """第四轮：IP化选题生成"""
        if progress_callback:
            progress_callback("round4", 90, "正在生成 IP 化选题...")

        # 收集优质素材样本
        all_quotes = []
        all_cases = []
        all_viewpoints = []

        for r in chapter_results:
            data = r.structured_data
            all_quotes.extend([q.get("text", "") for q in data.get("quotes", [])])
            all_cases.extend([c.get("name", "") for c in data.get("cases", [])])
            all_viewpoints.extend([v.get("title", "") for v in data.get("viewpoints", [])])

        # 限制样本数量
        quotes_sample = "\n".join([f"- {q}" for q in all_quotes[:10]])
        cases_sample = "\n".join([f"- {c}" for c in all_cases[:5]])
        viewpoints_sample = "\n".join([f"- {v}" for v in all_viewpoints[:5]])

        system_prompt = self.ROUND4_SYSTEM_PROMPT.format(ip_direction=self.ip_direction)

        user_prompt = self.ROUND4_USER_TEMPLATE.format(
            book_name=book_name,
            core_thesis=book_structure.get("core_thesis", ""),
            target_audience=book_structure.get("target_audience", ""),
            quotes_sample=quotes_sample,
            cases_sample=cases_sample,
            viewpoints_sample=viewpoints_sample
        )

        content, model = self._try_all_models(
            system_prompt,
            user_prompt,
            max_tokens=4000,
            temperature=0.8  # 高温度，更有创意
        )

        structured = self._extract_json(content)

        if progress_callback:
            progress_callback("round4", 100, "选题生成完成")

        return ExtractionResult(
            round_name="ip_topic_generation",
            model_used=model,
            content=content,
            structured_data=structured,
            confidence=0.70
        )

    # =========================================================================
    # 工具方法
    # =========================================================================

    def _extract_json(self, text: str) -> Dict:
        """从 AI 输出中提取 JSON"""
        # 清理 markdown 代码块
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```\s*$', '', text, flags=re.MULTILINE)

        # 替换中文引号
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        text = text.replace('\u2018', "'").replace('\u2019', "'")

        # 尝试提取 JSON
        try:
            # 直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试找最外层的大括号
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # 失败返回原始文本包装
        return {"raw_content": text, "parse_error": True}

    # =========================================================================
    # 完整流程
    # =========================================================================

    def extract_full(
        self,
        book_name: str,
        text: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        执行完整的多轮提取流程

        Args:
            book_name: 书名
            text: 完整文本
            progress_callback: 进度回调 (stage, progress, message)

        Returns:
            完整的提取结果
        """
        from chunking import chunk_book_text

        print(f"[Pipeline] 开始多轮提取《{book_name}》")

        # 步骤0: 文本分块
        if progress_callback:
            progress_callback("prepare", 5, "正在分析文本结构...")

        chunked = chunk_book_text(text, book_name, max_chunk_size=4000)
        chapters = chunked["chapters"]

        print(f"[Pipeline] 文本分块完成: {len(chapters)} 章节")

        # Round 1: 结构理解
        text_sample = text[:int(len(text) * 0.3)]  # 前30%
        round1_result = self.round1_structure_understanding(
            book_name, text_sample, progress_callback
        )

        book_structure = round1_result.structured_data

        # Round 2: 逐章提取
        # 为每个 chunk 补充 content
        flat_chunks = []
        for ch in chunked["chunks"]:
            flat_chunks.append({
                "title": ch["chapter_title"],
                "index": ch["chapter_index"],
                "content": ch["text"],
                "total_chapters": len(chapters)
            })

        round2_results = self.round2_all_chapters(
            book_name, flat_chunks, book_structure, progress_callback, max_workers=5
        )

        # Round 3: 跨章节分析
        round3_result = self.round3_cross_chapter_analysis(
            book_name, book_structure, round2_results, progress_callback
        )

        # Round 4: IP选题
        round4_result = self.round4_ip_topic_generation(
            book_name, book_structure, round2_results, progress_callback
        )

        # 合并结果
        final_result = {
            "book_name": book_name,
            "extraction_pipeline": {
                "round1_structure": round1_result.to_dict(),
                "round2_chapters": [r.to_dict() for r in round2_results],
                "round3_cross_analysis": round3_result.to_dict(),
                "round4_ip_topics": round4_result.to_dict()
            },
            "summary": {
                "total_quotes": sum(
                    len(r.structured_data.get("quotes", []))
                    for r in round2_results
                ),
                "total_cases": sum(
                    len(r.structured_data.get("cases", []))
                    for r in round2_results
                ),
                "total_viewpoints": sum(
                    len(r.structured_data.get("viewpoints", []))
                    for r in round2_results
                ),
                "total_topics": len(
                    round4_result.structured_data.get("topics", [])
                )
            }
        }

        return final_result


# 便捷函数
def extract_book_content(
    book_name: str,
    text: str,
    primary_client,
    fallback_client,
    fallback2_client,
    primary_model: str,
    fallback_model: str,
    fallback2_model: str,
    ip_direction: str = "职场认知升级 / 人性洞察 / 个人成长破局",
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    便捷函数：执行完整的书籍内容提取流程

    Args:
        book_name: 书名
        text: 完整文本
        primary_client: 主 AI 客户端
        fallback_client: 备用 AI 客户端
        fallback2_client: 备用2 AI 客户端
        primary_model: 主模型 ID
        fallback_model: 备用模型 ID
        fallback2_model: 备用2模型 ID
        ip_direction: IP 方向
        progress_callback: 进度回调

    Returns:
        完整的提取结果
    """
    pipeline = MultiRoundExtractionPipeline(
        primary_client=primary_client,
        fallback_client=fallback_client,
        fallback2_client=fallback2_client,
        primary_model=primary_model,
        fallback_model=fallback_model,
        fallback2_model=fallback2_model,
        ip_direction=ip_direction
    )

    return pipeline.extract_full(book_name, text, progress_callback)
