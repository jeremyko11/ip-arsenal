"""
IP Arsenal 提取引擎 v2.0 - 整合业界最佳实践

基于深度调研（GitHub/X/Google）的优化实现：
1. Marker/Unstructured 的布局感知思想
2. JSON Schema 结构化输出
3. 知识图谱构建
4. 长上下文 + 智能分块混合策略
5. 多级质量验证
"""

import json
import re
import hashlib
from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════
# 配置常量
# ═══════════════════════════════════════════════════════════════════════════

class ExtractionConfig:
    """提取配置"""
    # 分块策略
    CHUNK_SIZE = 4000          # 目标 chunk 大小
    CHUNK_OVERLAP = 200        # 重叠大小
    MAX_CHUNK_SIZE = 8000      # 最大 chunk 大小

    # 长上下文阈值
    LONG_CONTEXT_THRESHOLD = 100000  # tokens

    # 质量评分阈值
    QUALITY_THRESHOLD_AUTO = 0.80
    QUALITY_THRESHOLD_REVIEW = 0.55

    # IP 方向关键词
    IP_KEYWORDS = {
        "职场": ["职场", "工作", "职业", "升职", "加薪", "领导", "同事", "沟通", "汇报"],
        "人性": ["人性", "心理", "情绪", "关系", "社交", "影响力", "说服", "认知"],
        "成长": ["成长", "突破", "改变", "习惯", "自律", "学习", "思维", "格局"]
    }


# ═══════════════════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════════════════

class ContentType(Enum):
    TEXT = "text"
    HEADING = "heading"
    LIST = "list"
    TABLE = "table"
    QUOTE = "quote"
    IMAGE = "image"


@dataclass
class DocumentElement:
    """文档元素 - 保留结构信息"""
    type: ContentType
    content: str
    level: int = 0           # 标题层级
    index: int = 0           # 序号
    metadata: Dict = field(default_factory=dict)


@dataclass
class TextChunk:
    """文本块"""
    chunk_id: str
    text: str
    char_start: int
    char_end: int
    chapter_title: str
    chapter_index: int
    elements: List[DocumentElement] = field(default_factory=list)
    summary: str = ""
    keywords: List[str] = field(default_factory=list)
    prev_chunk: Optional[str] = None
    next_chunk: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text[:200] + "..." if len(self.text) > 200 else self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "chapter_title": self.chapter_title,
            "chapter_index": self.chapter_index,
            "summary": self.summary,
            "keywords": self.keywords,
            "prev_chunk": self.prev_chunk,
            "next_chunk": self.next_chunk
        }


@dataclass
class ExtractedMaterial:
    """提取的素材"""
    id: str
    category: str           # quote/case/viewpoint/action/topic
    content: str
    context: str           # 上下文
    source_chapter: str
    source_chunk: str
    metadata: Dict
    quality_score: Dict
    validation_status: str = "pending"  # pending/approved/rejected

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category,
            "content": self.content,
            "context": self.context,
            "source_chapter": self.source_chapter,
            "metadata": self.metadata,
            "quality_score": self.quality_score,
            "validation_status": self.validation_status
        }


@dataclass
class KnowledgeNode:
    """知识图谱节点"""
    id: str
    name: str
    type: str             # person/organization/concept/event
    description: str
    mentions: int = 1
    related_materials: List[str] = field(default_factory=list)


@dataclass
class KnowledgeEdge:
    """知识图谱边"""
    source: str
    target: str
    relation: str
    evidence: str
    confidence: float


# ═══════════════════════════════════════════════════════════════════════════
# Stage 1: 文档解析与结构化（Marker + Unstructured 思想）
# ═══════════════════════════════════════════════════════════════════════════

class DocumentParser:
    """文档解析器 - 识别结构元素"""

    # 章节标题模式
    CHAPTER_PATTERNS = [
        (r'^\s*第[一二三四五六七八九十百千万零\d]+[章篇节部分]\s*[：:．.]?\s*(.+)?$', 1),
        (r'^\s*Chapter\s+\d+[\s:：.]+(.+)?$', 1),
        (r'^\s*Part\s+\d+[\s:：.]+(.+)?$', 1),
        (r'^\s*(前言|序言|引言|导论|后记|附录|结语|总结)\s*$', 1),
        (r'^\s*\d+[\.．、]\s*(.+)$', 2),
        (r'^#{1,6}\s*(.+)$', 0),  # Markdown 标题
    ]

    def __init__(self):
        self.patterns = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), level)
            for p, level in self.CHAPTER_PATTERNS
        ]

    def parse(self, text: str) -> List[DocumentElement]:
        """
        解析文本为结构化元素

        借鉴 Unstructured 的分区思想：
        1. 识别标题、段落、列表、引用
        2. 保留层级关系
        3. 生成带类型的元素列表
        """
        elements = []
        lines = text.split('\n')
        current_list = []
        in_code_block = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 代码块处理
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # 空行处理
            if not stripped:
                if current_list:
                    elements.append(DocumentElement(
                        type=ContentType.LIST,
                        content='\n'.join(current_list),
                        metadata={"item_count": len(current_list)}
                    ))
                    current_list = []
                continue

            # 标题检测
            is_heading, level, title = self._detect_heading(stripped)
            if is_heading:
                elements.append(DocumentElement(
                    type=ContentType.HEADING,
                    content=title or stripped,
                    level=level,
                    index=len([e for e in elements if e.type == ContentType.HEADING])
                ))
                continue

            # 列表检测
            if re.match(r'^[\s]*[\d\-\*\+][\.\s]', stripped):
                current_list.append(stripped)
                continue

            # 引用检测
            if stripped.startswith('>') or stripped.startswith('"'):
                elements.append(DocumentElement(
                    type=ContentType.QUOTE,
                    content=stripped
                ))
                continue

            # 普通文本
            elements.append(DocumentElement(
                type=ContentType.TEXT,
                content=stripped
            ))

        return elements

    def _detect_heading(self, line: str) -> tuple[bool, int, Optional[str]]:
        """检测标题"""
        for pattern, default_level in self.patterns:
            match = pattern.match(line)
            if match:
                title = match.group(1) if match.groups() else line
                # Markdown 标题特殊处理
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    title = line.lstrip('#').strip()
                else:
                    level = default_level
                return True, level, title
        return False, 0, None


# ═══════════════════════════════════════════════════════════════════════════
# Stage 2: 智能分块（语义保持）
# ═══════════════════════════════════════════════════════════════════════════

class SemanticChunker:
    """语义切分器 - 保持语义连贯性"""

    def __init__(self, config: ExtractionConfig = None):
        self.config = config or ExtractionConfig()

    def chunk(
        self,
        elements: List[DocumentElement],
        book_name: str = ""
    ) -> List[TextChunk]:
        """
        将文档元素切分为语义连贯的 chunks

        策略：
        1. 按章节分组
        2. 章节内按语义边界切分
        3. 保持标题-内容的关联
        4. 添加重叠区域
        """
        # 按章节分组
        chapters = self._group_by_chapter(elements)

        chunks = []
        global_pos = 0

        for ch_idx, (chapter_title, chapter_elems) in enumerate(chapters):
            # 合并章节文本
            chapter_text = '\n\n'.join([e.content for e in chapter_elems])

            if len(chapter_text) <= self.config.CHUNK_SIZE:
                # 章节较短，不需要切分
                chunk = TextChunk(
                    chunk_id=f"ch{ch_idx:03d}_001",
                    text=chapter_text,
                    char_start=global_pos,
                    char_end=global_pos + len(chapter_text),
                    chapter_title=chapter_title,
                    chapter_index=ch_idx,
                    elements=chapter_elems
                )
                chunks.append(chunk)
                global_pos += len(chapter_text)
            else:
                # 需要切分
                chapter_chunks = self._split_chapter(
                    chapter_text, chapter_elems, ch_idx, chapter_title, global_pos
                )
                chunks.extend(chapter_chunks)
                global_pos += len(chapter_text)

        # 建立 chunk 间关联
        for i, chunk in enumerate(chunks):
            if i > 0:
                chunk.prev_chunk = chunks[i-1].chunk_id
            if i < len(chunks) - 1:
                chunk.next_chunk = chunks[i+1].chunk_id

        return chunks

    def _group_by_chapter(
        self,
        elements: List[DocumentElement]
    ) -> List[tuple[str, List[DocumentElement]]]:
        """按章节分组元素"""
        chapters = []
        current_title = "前言"
        current_elems = []

        for elem in elements:
            if elem.type == ContentType.HEADING:
                if current_elems:
                    chapters.append((current_title, current_elems))
                current_title = elem.content
                current_elems = [elem]
            else:
                current_elems.append(elem)

        if current_elems:
            chapters.append((current_title, current_elems))

        return chapters

    def _split_chapter(
        self,
        text: str,
        elements: List[DocumentElement],
        ch_idx: int,
        chapter_title: str,
        start_pos: int
    ) -> List[TextChunk]:
        """切分章节为 chunks"""
        chunks = []

        # 按段落分割
        paragraphs = text.split('\n\n')
        current_text = ""
        current_start = start_pos
        chunk_idx = 0

        for para in paragraphs:
            if len(current_text) + len(para) > self.config.CHUNK_SIZE and len(current_text) >= self.config.CHUNK_SIZE // 2:
                # 保存当前 chunk
                chunk_idx += 1
                chunk = TextChunk(
                    chunk_id=f"ch{ch_idx:03d}_{chunk_idx:03d}",
                    text=current_text.strip(),
                    char_start=current_start,
                    char_end=current_start + len(current_text),
                    chapter_title=chapter_title,
                    chapter_index=ch_idx
                )
                chunks.append(chunk)

                # 开始新 chunk，保留重叠
                overlap = self._get_overlap(current_text)
                current_text = overlap + para + "\n\n"
                current_start = current_start + len(current_text) - len(overlap)
            else:
                current_text += para + "\n\n"

        # 最后一个 chunk
        if current_text.strip():
            chunk_idx += 1
            chunk = TextChunk(
                chunk_id=f"ch{ch_idx:03d}_{chunk_idx:03d}",
                text=current_text.strip(),
                char_start=current_start,
                char_end=start_pos + len(text),
                chapter_title=chapter_title,
                chapter_index=ch_idx
            )
            chunks.append(chunk)

        return chunks

    def _get_overlap(self, text: str) -> str:
        """获取重叠文本"""
        if len(text) <= self.config.CHUNK_OVERLAP:
            return text

        overlap = text[-self.config.CHUNK_OVERLAP:]
        # 尽量在句子边界切分
        for punct in ['。', '？', '！', '.', '?', '!', '\n']:
            pos = overlap.find(punct)
            if pos > 0 and pos < len(overlap) - 10:
                return overlap[pos+1:].strip()
        return overlap


# ═══════════════════════════════════════════════════════════════════════════
# Stage 3: 结构化提取（JSON Schema 约束）
# ═══════════════════════════════════════════════════════════════════════════

class StructuredExtractor:
    """结构化提取器 - 使用 JSON Schema"""

    # 提取 Schema
    EXTRACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "quotes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "context": {"type": "string"},
                        "significance": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["text"]
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
                        "lesson": {"type": "string"}
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
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]}
                    },
                    "required": ["statement"]
                }
            }
        }
    }

    def __init__(self, ai_client, model_id: str):
        self.client = ai_client
        self.model_id = model_id

    def extract(
        self,
        chunk: TextChunk,
        book_context: Dict
    ) -> List[ExtractedMaterial]:
        """从 chunk 中提取结构化素材"""
        system_prompt = f"""你是一位专业的内容提取专家。
请从以下文本中提取素材，输出严格的 JSON 格式。

Schema:
{json.dumps(self.EXTRACTION_SCHEMA, indent=2)}

要求：
1. 只输出 JSON，不要其他文字
2. 确保 JSON 格式正确
3. 忠实原文，不编造内容"""

        user_prompt = f"""章节：{chunk.chapter_title}

上下文：{chunk.summary or book_context.get('core_thesis', '')}

文本内容：
{chunk.text[:6000]}

请提取素材。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )

            content = response.choices[0].message.content or "{}"
            parsed = self._parse_json(content)

            materials = []

            # 处理金句
            for i, q in enumerate(parsed.get("quotes", [])):
                materials.append(ExtractedMaterial(
                    id=f"{chunk.chunk_id}_q{i}",
                    category="quote",
                    content=q.get("text", ""),
                    context=q.get("context", ""),
                    source_chapter=chunk.chapter_title,
                    source_chunk=chunk.chunk_id,
                    metadata={
                        "significance": q.get("significance", ""),
                        "tags": q.get("tags", [])
                    },
                    quality_score={}
                ))

            # 处理案例
            for i, c in enumerate(parsed.get("cases", [])):
                materials.append(ExtractedMaterial(
                    id=f"{chunk.chunk_id}_c{i}",
                    category="case",
                    content=json.dumps(c, ensure_ascii=False),
                    context=c.get("background", ""),
                    source_chapter=chunk.chapter_title,
                    source_chunk=chunk.chunk_id,
                    metadata={"lesson": c.get("lesson", "")},
                    quality_score={}
                ))

            return materials

        except Exception as e:
            print(f"Extraction failed for {chunk.chunk_id}: {e}")
            return []

    def _parse_json(self, text: str) -> Dict:
        """安全解析 JSON"""
        # 清理 markdown
        text = re.sub(r'^```(?:json)?\s*', '', text.strip())
        text = re.sub(r'\s*```\s*$', '', text.strip())

        # 替换中文引号
        text = text.replace('\u201c', '"').replace('\u201d', '"')

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {}


# ═══════════════════════════════════════════════════════════════════════════
# Stage 4: 知识图谱构建
# ═══════════════════════════════════════════════════════════════════════════

class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    # 实体类型
    ENTITY_TYPES = ["person", "organization", "concept", "event", "product", "theory"]

    def __init__(self, ai_client, model_id: str):
        self.client = ai_client
        self.model_id = model_id

    def build(
        self,
        materials: List[ExtractedMaterial],
        chunks: List[TextChunk]
    ) -> Dict[str, List]:
        """从素材构建知识图谱"""
        # 收集所有文本
        all_text = ' '.join([m.content for m in materials[:50]])

        system_prompt = """从文本中提取知识图谱，输出 JSON：
{"entities": [{"name": "", "type": "person/organization/concept/event", "description": ""}],
 "relations": [{"source": "", "target": "", "relation": "", "evidence": ""}]}"""

        user_prompt = f"请分析以下内容，提取知识图谱：\n\n{all_text[:8000]}"

        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )

            content = response.choices[0].message.content or "{}"
            parsed = self._parse_json(content)

            return {
                "nodes": parsed.get("entities", []),
                "edges": parsed.get("relations", [])
            }

        except Exception as e:
            print(f"Knowledge graph building failed: {e}")
            return {"nodes": [], "edges": []}

    def _parse_json(self, text: str) -> Dict:
        """安全解析 JSON"""
        text = re.sub(r'^```(?:json)?\s*', '', text.strip())
        text = re.sub(r'\s*```\s*$', '', text.strip())
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
# Stage 5: 质量验证
# ═══════════════════════════════════════════════════════════════════════════

class QualityValidator:
    """质量验证器"""

    def __init__(self, config: ExtractionConfig = None):
        self.config = config or ExtractionConfig()

    def validate(self, material: ExtractedMaterial) -> Dict:
        """验证素材质量"""
        scores = {
            "completeness": self._check_completeness(material),
            "ip_fit": self._check_ip_fit(material),
            "actionable": self._check_actionable(material),
            "uniqueness": 1.0  # 需要外部去重
        }

        overall = sum(scores.values()) / len(scores)

        # 确定验证状态
        if overall >= self.config.QUALITY_THRESHOLD_AUTO:
            status = "approved"
        elif overall >= self.config.QUALITY_THRESHOLD_REVIEW:
            status = "pending"
        else:
            status = "rejected"

        material.quality_score = scores
        material.validation_status = status

        return {
            "scores": scores,
            "overall": overall,
            "status": status
        }

    def _check_completeness(self, material: ExtractedMaterial) -> float:
        """检查完整度"""
        score = 1.0
        content = material.content

        if len(content) < 20:
            score -= 0.3
        if len(content) > 2000:
            score -= 0.1
        if not material.context:
            score -= 0.1

        return max(0, score)

    def _check_ip_fit(self, material: ExtractedMaterial) -> float:
        """检查 IP 契合度"""
        content = material.content.lower()
        matched = 0

        for domain, keywords in self.config.IP_KEYWORDS.items():
            for kw in keywords:
                if kw in content:
                    matched += 1

        return min(1.0, 0.3 + matched * 0.1)

    def _check_actionable(self, material: ExtractedMaterial) -> float:
        """检查可执行性"""
        if material.category == "quote":
            return 0.9 if len(material.content) < 100 else 0.7
        elif material.category == "case":
            return 0.85 if "结果" in material.content else 0.6
        elif material.category == "action":
            return 0.9 if re.search(r'\d+\.', material.content) else 0.7
        return 0.7


# ═══════════════════════════════════════════════════════════════════════════
# 主流程整合
# ═══════════════════════════════════════════════════════════════════════════

class IPArsenalExtractorV2:
    """
    IP Arsenal 提取引擎 v2.0

    整合业界最佳实践的完整流程：
    1. 文档解析（Marker + Unstructured 思想）
    2. 智能分块（语义保持）
    3. 结构化提取（JSON Schema）
    4. 知识图谱构建
    5. 质量验证
    """

    def __init__(
        self,
        ai_client,
        model_id: str,
        config: ExtractionConfig = None
    ):
        self.ai_client = ai_client
        self.model_id = model_id
        self.config = config or ExtractionConfig()

        # 初始化各阶段组件
        self.parser = DocumentParser()
        self.chunker = SemanticChunker(self.config)
        self.extractor = StructuredExtractor(ai_client, model_id)
        self.kg_builder = KnowledgeGraphBuilder(ai_client, model_id)
        self.validator = QualityValidator(self.config)

    def extract(
        self,
        text: str,
        book_name: str = "",
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        执行完整提取流程

        Args:
            text: 书籍文本
            book_name: 书名
            progress_callback: 进度回调 (stage, progress, message)

        Returns:
            提取结果
        """
        result = {
            "book_name": book_name,
            "version": "2.0",
            "chunks": [],
            "materials": [],
            "knowledge_graph": {"nodes": [], "edges": []},
            "stats": {}
        }

        # Stage 1: 文档解析
        if progress_callback:
            progress_callback("parse", 10, "解析文档结构...")
        elements = self.parser.parse(text)

        # Stage 2: 智能分块
        if progress_callback:
            progress_callback("chunk", 25, "语义分块...")
        chunks = self.chunker.chunk(elements, book_name)
        result["chunks"] = [c.to_dict() for c in chunks]

        # Stage 3: 结构化提取
        if progress_callback:
            progress_callback("extract", 40, "提取素材...")

        all_materials = []
        book_context = {"core_thesis": ""}

        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(
                    "extract",
                    40 + int((i / len(chunks)) * 30),
                    f"提取第{i+1}/{len(chunks)}块..."
                )

            materials = self.extractor.extract(chunk, book_context)
            all_materials.extend(materials)

        # Stage 4: 知识图谱
        if progress_callback:
            progress_callback("kg", 75, "构建知识图谱...")
        kg = self.kg_builder.build(all_materials, chunks)
        result["knowledge_graph"] = kg

        # Stage 5: 质量验证
        if progress_callback:
            progress_callback("validate", 90, "质量验证...")

        approved = []
        pending = []
        rejected = []

        for m in all_materials:
            validation = self.validator.validate(m)
            if m.validation_status == "approved":
                approved.append(m)
            elif m.validation_status == "pending":
                pending.append(m)
            else:
                rejected.append(m)

        result["materials"] = [m.to_dict() for m in approved + pending]
        result["stats"] = {
            "total_chunks": len(chunks),
            "total_materials": len(all_materials),
            "approved": len(approved),
            "pending_review": len(pending),
            "rejected": len(rejected),
            "kg_nodes": len(kg["nodes"]),
            "kg_edges": len(kg["edges"])
        }

        if progress_callback:
            progress_callback("complete", 100, "提取完成")

        return result


# 便捷函数
def extract_book_v2(
    text: str,
    book_name: str,
    ai_client,
    model_id: str = "gpt-4",
    progress_callback: Optional[callable] = None
) -> Dict:
    """便捷函数：使用 v2 引擎提取书籍"""
    extractor = IPArsenalExtractorV2(ai_client, model_id)
    return extractor.extract(text, book_name, progress_callback)
