"""
分层 Chunking 模块 - 智能书籍文本切分

核心功能：
1. 提取并保留书籍目录结构
2. 按章节语义切分 chunk
3. 生成 chunk 摘要和关键词
4. 维护 chunk 间的前后文关联
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class TextChunk:
    """文本块数据结构"""
    chunk_id: str
    text: str
    char_start: int
    char_end: int
    chapter_title: str
    chapter_level: int
    chapter_index: int
    summary: str = ""
    keywords: List[str] = None
    entities: List[str] = None
    prev_chunk: Optional[str] = None
    next_chunk: Optional[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.entities is None:
            self.entities = []

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Chapter:
    """章节数据结构"""
    title: str
    level: int
    index: int
    start_pos: int
    end_pos: int
    content: str = ""
    chunks: List[TextChunk] = None
    summary: str = ""

    def __post_init__(self):
        if self.chunks is None:
            self.chunks = []

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "level": self.level,
            "index": self.index,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "content_length": len(self.content),
            "chunk_count": len(self.chunks),
            "summary": self.summary,
            "chunks": [c.to_dict() for c in self.chunks]
        }


class BookStructureExtractor:
    """书籍结构提取器"""

    # 常见章节标题模式
    CHAPTER_PATTERNS = [
        # 第X章 / 第X篇 / 第X节
        r'^\s*第[一二三四五六七八九十百千万零\d]+[章篇节部分]\s*[：:．.]?\s*(.+)?$',
        # Chapter X / Part X
        r'^\s*Chapter\s+\d+[\s:：.]+(.+)?$',
        r'^\s*Part\s+\d+[\s:：.]+(.+)?$',
        # X. 标题 / X.X 标题
        r'^\s*\d+[\.．、]\s*(.+)$',
        r'^\s*\d+\.\d+[\.．、]?\s*(.+)$',
        # 前言、后记、附录等
        r'^\s*(前言|序言|引言|导论|后记|附录|结语|总结)\s*$',
        r'^\s*(Preface|Introduction|Conclusion|Appendix)\s*$',
    ]

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.CHAPTER_PATTERNS]

    def extract_structure(self, text: str) -> List[Chapter]:
        """
        从文本中提取章节结构

        Args:
            text: 完整书籍文本

        Returns:
            Chapter 列表
        """
        lines = text.split('\n')
        chapters = []
        current_chapter = None
        chapter_start = 0

        for i, line in enumerate(lines):
            is_chapter_start, level, title = self._is_chapter_line(line)

            if is_chapter_start:
                # 保存前一个章节
                if current_chapter is not None:
                    content = '\n'.join(lines[chapter_start:i])
                    current_chapter.end_pos = len('\n'.join(lines[:i]))
                    current_chapter.content = content
                    chapters.append(current_chapter)

                # 开始新章节
                current_chapter = Chapter(
                    title=title or line.strip(),
                    level=level,
                    index=len(chapters),
                    start_pos=len('\n'.join(lines[:i])),
                    end_pos=0
                )
                chapter_start = i

        # 处理最后一个章节
        if current_chapter is not None:
            content = '\n'.join(lines[chapter_start:])
            current_chapter.end_pos = len(text)
            current_chapter.content = content
            chapters.append(current_chapter)

        # 如果没有识别到章节，将整个文本作为一个章节
        if not chapters:
            chapters.append(Chapter(
                title="全文",
                level=1,
                index=0,
                start_pos=0,
                end_pos=len(text),
                content=text
            ))

        return chapters

    def _is_chapter_line(self, line: str) -> Tuple[bool, int, Optional[str]]:
        """判断一行是否是章节标题"""
        line = line.strip()
        if not line or len(line) > 100:  # 章节标题通常不会太长
            return False, 0, None

        for i, pattern in enumerate(self.patterns):
            match = pattern.match(line)
            if match:
                # 根据模式类型判断层级
                if i < 2:  # 第X章/Chapter
                    level = 1
                elif i < 4:  # 第X篇/Part
                    level = 1
                elif i < 6:  # X. / X.X
                    level = 2 if '.' in line[:5] else 1
                else:  # 前言/后记等
                    level = 1

                title = match.group(1) if match.groups() else line
                return True, level, title.strip()

        return False, 0, None


class SemanticChunker:
    """语义切分器 - 按语义段落切分章节内容"""

    def __init__(
        self,
        min_chunk_size: int = 1000,
        max_chunk_size: int = 4000,
        overlap_size: int = 200
    ):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size

    def chunk_chapter(self, chapter: Chapter) -> List[TextChunk]:
        """
        将章节内容切分为语义连贯的 chunks

        Args:
            chapter: Chapter 对象

        Returns:
            TextChunk 列表
        """
        content = chapter.content
        if len(content) <= self.max_chunk_size:
            # 章节较短，不需要切分
            chunk = TextChunk(
                chunk_id=f"c{chapter.index}-001",
                text=content,
                char_start=chapter.start_pos,
                char_end=chapter.end_pos,
                chapter_title=chapter.title,
                chapter_level=chapter.level,
                chapter_index=chapter.index,
                prev_chunk=None,
                next_chunk=None
            )
            return [chunk]

        # 需要切分
        chunks = []
        paragraphs = self._split_to_paragraphs(content)

        current_text = ""
        current_start = chapter.start_pos
        chunk_index = 0

        for para in paragraphs:
            para_len = len(para)
            current_len = len(current_text)

            # 判断是否需要切分
            if current_len + para_len > self.max_chunk_size and current_len >= self.min_chunk_size:
                # 保存当前 chunk
                chunk_index += 1
                chunk = TextChunk(
                    chunk_id=f"c{chapter.index}-{chunk_index:03d}",
                    text=current_text.strip(),
                    char_start=current_start,
                    char_end=current_start + current_len,
                    chapter_title=chapter.title,
                    chapter_level=chapter.level,
                    chapter_index=chapter.index
                )
                chunks.append(chunk)

                # 开始新 chunk，保留重叠部分
                overlap_text = self._get_overlap(current_text)
                current_text = overlap_text + para + "\n\n"
                current_start = current_start + current_len - len(overlap_text)
            else:
                current_text += para + "\n\n"

        # 处理最后一个 chunk
        if current_text.strip():
            chunk_index += 1
            chunk = TextChunk(
                chunk_id=f"c{chapter.index}-{chunk_index:03d}",
                text=current_text.strip(),
                char_start=current_start,
                char_end=chapter.end_pos,
                chapter_title=chapter.title,
                chapter_level=chapter.level,
                chapter_index=chapter.index
            )
            chunks.append(chunk)

        # 建立 chunk 间关联
        for i, chunk in enumerate(chunks):
            if i > 0:
                chunk.prev_chunk = chunks[i-1].chunk_id
            if i < len(chunks) - 1:
                chunk.next_chunk = chunks[i+1].chunk_id

        return chunks

    def _split_to_paragraphs(self, text: str) -> List[str]:
        """将文本分割为段落列表"""
        # 按空行分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        # 清理并过滤空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return paragraphs

    def _get_overlap(self, text: str) -> str:
        """获取文本末尾的重叠部分"""
        if len(text) <= self.overlap_size:
            return text

        # 尽量在句子边界处切分
        overlap = text[-self.overlap_size:]
        # 找最后一个句号、问号、感叹号
        for punct in ['。', '？', '！', '.', '?', '!']:
            pos = overlap.find(punct)
            if pos != -1 and pos < len(overlap) - 1:
                return overlap[pos+1:].strip()

        return overlap


class ChunkSummarizer:
    """Chunk 摘要生成器 - 使用轻量模型生成摘要和关键词"""

    SUMMARY_PROMPT = """请对以下文本片段生成简洁的摘要和关键词。

要求：
1. 摘要：3-5句话，概括核心观点和关键信息
2. 关键词：提取5-10个关键词或关键短语
3. 实体：提取文中提到的重要人名、书名、概念等

输出格式（必须严格按此格式）：
摘要：[摘要内容]
关键词：[关键词1], [关键词2], ...
实体：[实体1], [实体2], ...

文本片段：
{text}
"""

    def __init__(self, ai_client=None, model_id: str = None):
        self.ai_client = ai_client
        self.model_id = model_id

    def summarize(self, chunk: TextChunk) -> TextChunk:
        """为 chunk 生成摘要"""
        if not self.ai_client:
            # 无 AI 客户端，使用简单规则提取
            chunk.summary = self._simple_summary(chunk.text)
            chunk.keywords = self._simple_keywords(chunk.text)
            return chunk

        try:
            prompt = self.SUMMARY_PROMPT.format(text=chunk.text[:3000])

            resp = self.ai_client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "你是一个专业的文本分析助手，擅长提取关键信息。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            content = resp.choices[0].message.content or ""

            # 解析输出
            chunk.summary = self._extract_field(content, "摘要") or self._simple_summary(chunk.text)
            chunk.keywords = self._extract_list(content, "关键词") or self._simple_keywords(chunk.text)
            chunk.entities = self._extract_list(content, "实体")

        except Exception as e:
            print(f"Summarize chunk {chunk.chunk_id} failed: {e}")
            chunk.summary = self._simple_summary(chunk.text)
            chunk.keywords = self._simple_keywords(chunk.text)

        return chunk

    def _simple_summary(self, text: str) -> str:
        """简单规则摘要：取前3句"""
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return '。'.join(sentences[:3]) + '。' if sentences else text[:200]

    def _simple_keywords(self, text: str) -> List[str]:
        """简单规则关键词：提取高频词"""
        # 简单的关键词提取：找引号内容、书名号内容
        keywords = []

        # 提取引号内容
        quotes = re.findall(r'["""]([^"""]+)["""]', text)
        keywords.extend(quotes[:5])

        # 提取书名号内容
        books = re.findall(r'《([^》]+)》', text)
        keywords.extend(books[:3])

        return keywords[:10]

    def _extract_field(self, text: str, field: str) -> Optional[str]:
        """从 AI 输出中提取字段"""
        pattern = rf'{field}[：:]\s*(.+?)(?=\n\w+[：:]|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _extract_list(self, text: str, field: str) -> List[str]:
        """从 AI 输出中提取列表"""
        content = self._extract_field(text, field)
        if not content:
            return []

        # 按逗号、顿号分割
        items = re.split(r'[,，、]', content)
        return [item.strip() for item in items if item.strip()]


class HierarchicalChunkingPipeline:
    """分层 Chunking 完整流程"""

    def __init__(
        self,
        ai_client=None,
        model_id: str = None,
        min_chunk_size: int = 1000,
        max_chunk_size: int = 4000
    ):
        self.structure_extractor = BookStructureExtractor()
        self.semantic_chunker = SemanticChunker(min_chunk_size, max_chunk_size)
        self.summarizer = ChunkSummarizer(ai_client, model_id)

    def process(self, text: str, book_name: str = "") -> Dict:
        """
        处理书籍文本，返回分层结构

        Args:
            text: 完整书籍文本
            book_name: 书名

        Returns:
            包含章节结构和 chunks 的字典
        """
        print(f"[Chunking] 开始处理《{book_name}》，文本长度: {len(text)}")

        # 步骤1：提取章节结构
        print("[Chunking] 步骤1: 提取章节结构...")
        chapters = self.structure_extractor.extract_structure(text)
        print(f"[Chunking] 识别到 {len(chapters)} 个章节")

        # 步骤2：逐章节切分 chunks
        print("[Chunking] 步骤2: 语义切分 chunks...")
        all_chunks = []
        for chapter in chapters:
            chunks = self.semantic_chunker.chunk_chapter(chapter)
            chapter.chunks = chunks
            all_chunks.extend(chunks)

        print(f"[Chunking] 共生成 {len(all_chunks)} 个 chunks")

        # 步骤3：生成摘要（可选，异步进行）
        # for chunk in all_chunks:
        #     self.summarizer.summarize(chunk)

        # 构建输出
        result = {
            "book_name": book_name,
            "total_chars": len(text),
            "chapter_count": len(chapters),
            "chunk_count": len(all_chunks),
            "chapters": [c.to_dict() for c in chapters],
            "chunks": [c.to_dict() for c in all_chunks]
        }

        return result

    def get_flat_chunks(self, result: Dict) -> List[TextChunk]:
        """获取扁平化的 chunk 列表，用于喂给 AI"""
        chunks = []
        for ch in result["chunks"]:
            chunk = TextChunk(
                chunk_id=ch["chunk_id"],
                text=ch["text"],
                char_start=ch["char_start"],
                char_end=ch["char_end"],
                chapter_title=ch["chapter_title"],
                chapter_level=ch["chapter_level"],
                chapter_index=ch["chapter_index"],
                summary=ch.get("summary", ""),
                keywords=ch.get("keywords", []),
                entities=ch.get("entities", []),
                prev_chunk=ch.get("prev_chunk"),
                next_chunk=ch.get("next_chunk")
            )
            chunks.append(chunk)
        return chunks


# 便捷函数
def chunk_book_text(
    text: str,
    book_name: str = "",
    ai_client=None,
    model_id: str = None,
    max_chunk_size: int = 4000
) -> Dict:
    """
    便捷函数：对书籍文本进行分层 chunking

    Args:
        text: 完整书籍文本
        book_name: 书名
        ai_client: AI 客户端（可选，用于生成摘要）
        model_id: 模型 ID（可选）
        max_chunk_size: 最大 chunk 大小

    Returns:
        包含完整结构信息的字典
    """
    pipeline = HierarchicalChunkingPipeline(
        ai_client=ai_client,
        model_id=model_id,
        max_chunk_size=max_chunk_size
    )
    return pipeline.process(text, book_name)
