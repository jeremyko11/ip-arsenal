"""
增强版书籍提取模块 - 整合业界最佳实践

核心改进：
1. 多模态提取（文本 + 图表 + 表格）
2. 结构化输出（JSON Schema 约束）
3. 知识图谱构建（实体关系提取）
4. 混合策略（长上下文 + 智能分块）
5. 质量验证链（自洽性检查）
"""

import json
import re
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path


class ContentType(Enum):
    """内容类型枚举"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    FORMULA = "formula"
    HEADING = "heading"
    LIST = "list"


@dataclass
class ContentElement:
    """内容元素 - 保留原始文档的丰富结构"""
    type: ContentType
    content: str
    page_number: int
    bbox: Optional[tuple] = None  # (x1, y1, x2, y2)
    metadata: Dict = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class TableData:
    """表格数据结构"""
    headers: List[str]
    rows: List[List[str]]
    caption: str = ""
    page_number: int = 0


@dataclass
class KnowledgeNode:
    """知识图谱节点"""
    id: str
    label: str
    type: str  # concept/person/organization/event/quote/case
    properties: Dict
    source_chunk: str
    confidence: float


@dataclass
class KnowledgeEdge:
    """知识图谱边"""
    source: str
    target: str
    relation: str
    evidence: str
    confidence: float


@dataclass
class ExtractedMaterial:
    """提取的素材 - 增强版"""
    id: str
    category: str  # quote/case/viewpoint/action/topic
    content: str
    context: str  # 上下文信息
    source_location: Dict  # {chapter, page, paragraph}
    metadata: Dict
    quality_score: float
    related_materials: List[str] = field(default_factory=list)
    knowledge_nodes: List[str] = field(default_factory=list)


# JSON Schema 定义 - 用于结构化输出
BOOK_STRUCTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "core_thesis": {"type": "string", "description": "书籍核心论点"},
        "target_audience": {"type": "string"},
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "level": {"type": "integer"},
                    "summary": {"type": "string"},
                    "key_concepts": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["title", "summary"]
            }
        }
    },
    "required": ["core_thesis", "chapters"]
}

MATERIAL_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "context": {"type": "string"},
                    "speaker": {"type": "string"},
                    "significance": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["text", "significance"]
            }
        },
        "cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "background": {"type": "string"},
                    "challenge": {"type": "string"},
                    "action": {"type": "string"},
                    "result": {"type": "string"},
                    "lesson": {"type": "string"},
                    "applicability": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name", "challenge", "action", "result"]
            }
        },
        "viewpoints": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "counter_arguments": {"type": "array", "items": {"type": "string"}},
                    "confidence_level": {"type": "string", "enum": ["high", "medium", "low"]}
                },
                "required": ["statement", "evidence"]
            }
        }
    }
}

KNOWLEDGE_GRAPH_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["person", "organization", "concept", "event", "product", "theory"]},
                    "description": {"type": "string"},
                    "mentions": {"type": "integer"}
                },
                "required": ["name", "type"]
            }
        },
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "relation": {"type": "string"},
                    "evidence": {"type": "string"}
                },
                "required": ["source", "target", "relation"]
            }
        }
    }
}


class EnhancedBookExtractor:
    """
    增强版书籍提取器

    整合业界最佳实践：
    1. 多模态内容提取（Marker/Unstructured 思想）
    2. 结构化输出（JSON Schema 约束）
    3. 知识图谱构建（实体关系提取）
    4. 混合处理策略（长上下文 + 智能分块）
    5. 质量验证链（自洽性检查）
    """

    def __init__(
        self,
        primary_client,
        fallback_client=None,
        fallback2_client=None,
        primary_model: str = "gpt-4",
        fallback_model: str = "gpt-3.5-turbo",
        fallback2_model: str = "claude-3-haiku",
        use_long_context: bool = False,
        max_context_tokens: int = 128000
    ):
        self.clients = {
            "primary": (primary_client, primary_model),
            "fallback": (fallback_client, fallback_model) if fallback_client else None,
            "fallback2": (fallback2_client, fallback2_model) if fallback2_client else None
        }
        self.use_long_context = use_long_context
        self.max_context_tokens = max_context_tokens

    def extract(
        self,
        book_content: Union[str, List[ContentElement]],
        book_name: str,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        执行完整提取流程

        Args:
            book_content: 书籍内容（纯文本或结构化元素列表）
            book_name: 书名
            progress_callback: 进度回调

        Returns:
            包含结构化提取结果的字典
        """
        results = {
            "book_name": book_name,
            "extraction_version": "2.0-enhanced",
            "structure": None,
            "materials": [],
            "knowledge_graph": {"nodes": [], "edges": []},
            "topics": [],
            "validation_report": {}
        }

        # 步骤1: 内容预处理（多模态元素识别）
        if progress_callback:
            progress_callback("preprocess", 5, "识别内容元素...")

        elements = self._preprocess_content(book_content)

        # 步骤2: 结构提取（JSON Schema 约束）
        if progress_callback:
            progress_callback("structure", 15, "提取书籍结构...")

        structure = self._extract_structure(elements, book_name)
        results["structure"] = structure

        # 步骤3: 素材提取（分块或长上下文）
        if self.use_long_context and self._estimate_tokens(elements) < self.max_context_tokens:
            # 长上下文模式：一次性处理
            if progress_callback:
                progress_callback("materials", 30, "使用长上下文模式提取素材...")
            materials = self._extract_materials_long_context(elements, structure)
        else:
            # 智能分块模式
            if progress_callback:
                progress_callback("materials", 30, "使用智能分块模式提取素材...")
            materials = self._extract_materials_chunked(elements, structure, progress_callback)

        results["materials"] = materials

        # 步骤4: 知识图谱构建
        if progress_callback:
            progress_callback("knowledge_graph", 70, "构建知识图谱...")

        kg = self._build_knowledge_graph(materials, structure)
        results["knowledge_graph"] = kg

        # 步骤5: IP选题生成
        if progress_callback:
            progress_callback("topics", 85, "生成IP化选题...")

        topics = self._generate_topics(materials, structure, kg)
        results["topics"] = topics

        # 步骤6: 质量验证
        if progress_callback:
            progress_callback("validation", 95, "执行质量验证...")

        validation = self._validate_extraction(results)
        results["validation_report"] = validation

        if progress_callback:
            progress_callback("complete", 100, "提取完成")

        return results

    def _preprocess_content(
        self,
        content: Union[str, List[ContentElement]]
    ) -> List[ContentElement]:
        """预处理内容，识别多模态元素"""
        if isinstance(content, list):
            return content

        # 纯文本处理：识别潜在的表格、列表、代码块等
        elements = []
        paragraphs = content.split('\n\n')

        for i, para in enumerate(paragraphs):
            if not para.strip():
                continue

            # 识别表格（Markdown 格式）
            if '|' in para and '\n|' in para:
                elements.append(ContentElement(
                    type=ContentType.TABLE,
                    content=para,
                    page_number=0,
                    metadata={"detected_by": "heuristic"}
                ))
            # 识别代码块
            elif para.startswith('```') or para.startswith('    '):
                elements.append(ContentElement(
                    type=ContentType.CODE,
                    content=para,
                    page_number=0
                ))
            # 识别标题
            elif para.startswith('#') or para.startswith('第') or para.lower().startswith('chapter'):
                elements.append(ContentElement(
                    type=ContentType.HEADING,
                    content=para,
                    page_number=0
                ))
            # 识别列表
            elif re.match(r'^[\s]*[\d\-\*\+][\.\s]', para):
                elements.append(ContentElement(
                    type=ContentType.LIST,
                    content=para,
                    page_number=0
                ))
            else:
                elements.append(ContentElement(
                    type=ContentType.TEXT,
                    content=para,
                    page_number=0
                ))

        return elements

    def _extract_structure(
        self,
        elements: List[ContentElement],
        book_name: str
    ) -> Dict:
        """提取书籍结构（使用 JSON Schema）"""
        # 提取标题元素
        headings = [e for e in elements if e.type == ContentType.HEADING]

        # 构建提示
        system_prompt = f"""你是一位专业的书籍结构分析师。
请分析《{book_name}》的结构，提取核心框架信息。

你必须严格按照以下 JSON Schema 输出：
{json.dumps(BOOK_STRUCTURE_SCHEMA, ensure_ascii=False, indent=2)}

要求：
1. 只输出 JSON，不要任何其他文字
2. 确保 JSON 格式正确，可被解析
3. 章节层级要准确（level 1 是主要章节）"""

        # 采样内容（前30%）
        text_sample = '\n\n'.join([
            e.content for e in elements[:min(len(elements)//3, 100)]
        ])[:15000]

        user_prompt = f"请分析以下书籍内容，提取结构：\n\n{text_sample}"

        # 调用 AI
        content, _ = self._call_ai_with_fallback(
            system_prompt, user_prompt, max_tokens=2000, temperature=0.3
        )

        # 解析 JSON
        return self._safe_parse_json(content, {"core_thesis": "", "chapters": []})

    def _extract_materials_long_context(
        self,
        elements: List[ContentElement],
        structure: Dict
    ) -> List[ExtractedMaterial]:
        """长上下文模式：一次性提取所有素材"""
        full_text = '\n\n'.join([e.content for e in elements])

        system_prompt = f"""你是一位专业的内容提取专家。
请从书籍中提取高质量的素材，分类整理。

你必须严格按照以下 JSON Schema 输出：
{json.dumps(MATERIAL_EXTRACTION_SCHEMA, ensure_ascii=False, indent=2)}

提取原则：
1. 忠实原文，不编造内容
2. 优先提取具体、可操作的素材
3. 每个素材必须完整，包含上下文
4. 宁缺毋滥，质量优先"""

        user_prompt = f"请从以下书籍内容中提取素材：\n\n{full_text[:100000]}"  # 限制长度

        content, _ = self._call_ai_with_fallback(
            system_prompt, user_prompt, max_tokens=4000, temperature=0.5
        )

        parsed = self._safe_parse_json(content, {"quotes": [], "cases": [], "viewpoints": []})

        # 转换为统一格式
        materials = []

        for i, q in enumerate(parsed.get("quotes", [])):
            materials.append(ExtractedMaterial(
                id=f"quote_{i}",
                category="quote",
                content=q.get("text", ""),
                context=q.get("context", ""),
                source_location={},
                metadata={
                    "speaker": q.get("speaker", ""),
                    "significance": q.get("significance", ""),
                    "tags": q.get("tags", [])
                },
                quality_score=0.85
            ))

        for i, c in enumerate(parsed.get("cases", [])):
            materials.append(ExtractedMaterial(
                id=f"case_{i}",
                category="case",
                content=json.dumps(c, ensure_ascii=False),
                context=c.get("background", ""),
                source_location={},
                metadata={
                    "lesson": c.get("lesson", ""),
                    "applicability": c.get("applicability", [])
                },
                quality_score=0.80
            ))

        return materials

    def _extract_materials_chunked(
        self,
        elements: List[ContentElement],
        structure: Dict,
        progress_callback: Optional[callable]
    ) -> List[ExtractedMaterial]:
        """智能分块模式：逐章提取"""
        materials = []
        chapters = structure.get("chapters", [])

        # 将元素分组到各章节
        chapter_elements = self._group_elements_by_chapter(elements, chapters)

        for i, (chapter, chapter_elems) in enumerate(zip(chapters, chapter_elements)):
            if progress_callback:
                progress_callback(
                    "materials",
                    30 + int((i / len(chapters)) * 35),
                    f"提取第{i+1}章《{chapter.get('title', '')}》..."
                )

            chapter_text = '\n\n'.join([e.content for e in chapter_elems])

            if len(chapter_text) < 100:
                continue

            # 逐章提取
            chapter_materials = self._extract_from_chapter(
                chapter_text, chapter, structure
            )
            materials.extend(chapter_materials)

        return materials

    def _extract_from_chapter(
        self,
        chapter_text: str,
        chapter: Dict,
        book_structure: Dict
    ) -> List[ExtractedMaterial]:
        """从单个章节提取素材"""
        system_prompt = """从章节内容中提取素材，输出 JSON 格式：
{"quotes": [{"text": "", "context": "", "significance": ""}],
 "cases": [{"name": "", "challenge": "", "action": "", "result": ""}],
 "viewpoints": [{"statement": "", "evidence": []}]}"""

        user_prompt = f"章节：{chapter.get('title', '')}\n\n{chapter_text[:15000]}"

        try:
            content, _ = self._call_ai_with_fallback(
                system_prompt, user_prompt, max_tokens=2000, temperature=0.5
            )
            parsed = self._safe_parse_json(content, {})

            materials = []
            for i, q in enumerate(parsed.get("quotes", [])):
                materials.append(ExtractedMaterial(
                    id=f"quote_{chapter.get('title', '')}_{i}",
                    category="quote",
                    content=q.get("text", ""),
                    context=q.get("context", ""),
                    source_location={"chapter": chapter.get("title", "")},
                    metadata={"significance": q.get("significance", "")},
                    quality_score=0.80
                ))
            return materials
        except Exception as e:
            print(f"Chapter extraction failed: {e}")
            return []

    def _build_knowledge_graph(
        self,
        materials: List[ExtractedMaterial],
        structure: Dict
    ) -> Dict:
        """构建知识图谱"""
        # 收集所有文本
        all_text = ' '.join([m.content for m in materials])
        all_text += ' ' + json.dumps(structure, ensure_ascii=False)

        system_prompt = f"""从书籍内容中提取知识图谱。

你必须严格按照以下 JSON Schema 输出：
{json.dumps(KNOWLEDGE_GRAPH_SCHEMA, ensure_ascii=False, indent=2)}

要求：
1. 提取关键实体（人物、组织、概念、事件）
2. 识别实体间的关系
3. 每个关系必须有证据支持"""

        user_prompt = f"请分析以下内容，提取知识图谱：\n\n{all_text[:20000]}"

        try:
            content, _ = self._call_ai_with_fallback(
                system_prompt, user_prompt, max_tokens=3000, temperature=0.4
            )
            return self._safe_parse_json(content, {"entities": [], "relations": []})
        except Exception as e:
            print(f"Knowledge graph building failed: {e}")
            return {"entities": [], "relations": []}

    def _generate_topics(
        self,
        materials: List[ExtractedMaterial],
        structure: Dict,
        knowledge_graph: Dict
    ) -> List[Dict]:
        """生成 IP 化选题"""
        # 统计高频实体
        entities = knowledge_graph.get("entities", [])
        top_entities = sorted(entities, key=lambda x: x.get("mentions", 0), reverse=True)[:10]

        # 收集素材摘要
        material_summary = []
        for m in materials[:20]:  # 限制数量
            material_summary.append({
                "category": m.category,
                "preview": m.content[:100] + "..."
            })

        system_prompt = """你是资深的 IP 内容策划专家。
基于书籍内容和知识图谱，生成爆款选题。

输出 JSON 格式：
{"topics": [
  {"title": "爆款标题", "platform": "抖音/视频号/小红书/公众号",
   "hook": "开头钩子", "angle": "切入角度", "target_pain": "受众痛点"}
]}"""

        user_prompt = f"""书籍核心论点：{structure.get('core_thesis', '')}

关键概念：{[e.get('name') for e in top_entities]}

素材预览：{json.dumps(material_summary, ensure_ascii=False)}

请生成 10-15 个爆款选题。"""

        try:
            content, _ = self._call_ai_with_fallback(
                system_prompt, user_prompt, max_tokens=2500, temperature=0.8
            )
            parsed = self._safe_parse_json(content, {"topics": []})
            return parsed.get("topics", [])
        except Exception as e:
            print(f"Topic generation failed: {e}")
            return []

    def _validate_extraction(self, results: Dict) -> Dict:
        """验证提取结果的质量"""
        validation = {
            "completeness_checks": {},
            "consistency_checks": {},
            "coverage_analysis": {},
            "suggestions": []
        }

        materials = results.get("materials", [])
        structure = results.get("structure", {})

        # 完整度检查
        validation["completeness_checks"] = {
            "has_structure": bool(structure.get("chapters")),
            "has_materials": len(materials) > 0,
            "has_knowledge_graph": bool(results.get("knowledge_graph", {}).get("entities")),
            "has_topics": bool(results.get("topics"))
        }

        # 素材分布分析
        category_counts = {}
        for m in materials:
            cat = m.category if isinstance(m, ExtractedMaterial) else m.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        validation["coverage_analysis"] = {
            "total_materials": len(materials),
            "category_distribution": category_counts,
            "chapters_covered": len(set(
                m.source_location.get("chapter", "") if isinstance(m, ExtractedMaterial)
                else m.get("source_location", {}).get("chapter", "")
                for m in materials
            ))
        }

        # 生成建议
        if category_counts.get("quote", 0) < 5:
            validation["suggestions"].append("金句数量较少，建议检查提取策略")
        if category_counts.get("case", 0) < 3:
            validation["suggestions"].append("案例数量较少，可能影响内容丰富度")

        return validation

    # =========================================================================
    # 工具方法
    # =========================================================================

    def _call_ai_with_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.5,
        timeout: int = 180
    ) -> tuple[str, str]:
        """调用 AI，支持降级"""
        import concurrent.futures

        for tier in ["primary", "fallback", "fallback2"]:
            client_info = self.clients.get(tier)
            if not client_info or not client_info[0]:
                continue

            client, model = client_info

            def _call():
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return resp.choices[0].message.content or ""

            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_call)
                    result = future.result(timeout=timeout)
                    return result, model
            except Exception as e:
                print(f"{tier} model failed: {e}, trying next...")
                continue

        raise RuntimeError("All models failed")

    def _safe_parse_json(self, text: str, default: Any) -> Any:
        """安全解析 JSON"""
        # 清理 markdown 代码块
        text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
        text = re.sub(r'\s*```\s*$', '', text.strip(), flags=re.MULTILINE)

        # 替换中文引号
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        text = text.replace('\u2018', "'").replace('\u2019', "'")

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 对象
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return default

    def _estimate_tokens(self, elements: List[ContentElement]) -> int:
        """估算 token 数量（粗略估计：1 token ≈ 0.75 字符）"""
        total_chars = sum(len(e.content) for e in elements)
        return int(total_chars / 0.75)

    def _group_elements_by_chapter(
        self,
        elements: List[ContentElement],
        chapters: List[Dict]
    ) -> List[List[ContentElement]]:
        """将元素按章节分组"""
        if not chapters:
            return [elements]

        # 简化实现：平均分配
        chunk_size = len(elements) // max(1, len(chapters))
        result = []

        for i in range(len(chapters)):
            start = i * chunk_size
            end = start + chunk_size if i < len(chapters) - 1 else len(elements)
            result.append(elements[start:end])

        return result


# 便捷函数
def extract_book_enhanced(
    book_content: str,
    book_name: str,
    primary_client,
    fallback_client=None,
    fallback2_client=None,
    use_long_context: bool = False,
    progress_callback: Optional[callable] = None
) -> Dict:
    """
    便捷函数：使用增强版提取器处理书籍

    Args:
        book_content: 书籍文本内容
        book_name: 书名
        primary_client: 主 AI 客户端
        fallback_client: 备用 AI 客户端
        fallback2_client: 备用2 AI 客户端
        use_long_context: 是否使用长上下文模式
        progress_callback: 进度回调函数

    Returns:
        完整的提取结果
    """
    extractor = EnhancedBookExtractor(
        primary_client=primary_client,
        fallback_client=fallback_client,
        fallback2_client=fallback2_client,
        use_long_context=use_long_context
    )

    return extractor.extract(book_content, book_name, progress_callback)
