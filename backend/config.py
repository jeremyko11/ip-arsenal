# -*- coding: utf-8 -*-
"""
IP Arsenal - 配置模块
所有常量、路径、AI 客户端初始化
"""
import os
from pathlib import Path
from typing import Optional

from openai import OpenAI

# ── 强制 UTF-8 编码（Windows 默认 GBK 会导致中文乱码）────────────────────
import sys
if sys.version_info >= (3, 7):
    import io as _io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ── 路径配置 ───────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
DATA_DIR   = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
FRONT_DIR  = BASE_DIR / "frontend"
DB_PATH    = DATA_DIR / "arsenal.db"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# ── 数据库配置 ────────────────────────────────────────────────────────
# 支持 SQLite（默认，现有数据）和 PostgreSQL（高性能）
# 设置 DATABASE_URL 环境变量即可切换到 PostgreSQL
_DATABASE_URL = os.environ.get("DATABASE_URL", "")

if _DATABASE_URL:
    # PostgreSQL 模式
    USE_POSTGRES = True
    DB_PATH = _DATABASE_URL  # psycopg2 连接串
else:
    USE_POSTGRES = False
    DB_PATH = DATA_DIR / "arsenal.db"  # SQLite 路径（保持兼容）

# ── AI API 配置 ────────────────────────────────────────────────────────
API_BASE = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
API_KEY  = "d25220d05c80686af77fcc163c6fe92a:MmRkNjk3MzQ2MGQzMDllNzAyZjM3Mzg0"
MODEL_ID = "astron-code-latest"

# MiniMax 账号1（旧账号，可能额度已耗尽）
MINIMAX_API_BASE_1 = "https://llm.chudian.site/v1"
MINIMAX_API_KEY_1  = "sk-ag-0e87970be36f68d06e47e7a49cceb64d"
MINIMAX_MODEL_ID   = "minimax-m2.7"

# MiniMax 账号2（额度充足，优先使用）
MINIMAX_API_BASE_2 = "https://llm.chudian.site/v1"
MINIMAX_API_KEY_2  = "sk-cp-9ThlxsSvDTzoHt426NobJjtElVxPp1DBPUWEToX7Er0N6cH_MJjMBWQvOSZYXNFJUm071-xnMeGih4D26vl6bjlX7oq19rZ10P77AAXwkiZb0MXdBgIUHyQ"
MINIMAX_MODEL_ID_2  = "MiniMax-M2.7"

# DeepSeek 备选
FALLBACK2_API_BASE = "https://api.deepseek.com/v1"
FALLBACK2_API_KEY  = "sk-ab948053383f436fb1cf50639f57b439"
FALLBACK2_MODEL_ID = "deepseek-chat"

# 首选 AI 模型
_AI_PREFERRED = "deepseek"
FALLBACK_MODEL_ID = MINIMAX_MODEL_ID

# IP 提炼方向
IP_DIRECTION = "职场认知升级 / 人性洞察 / 个人成长破局"
MAX_CHARS = 80000
MAX_PROMPT_TEXT_CHARS = 60000

# ── AI 客户端初始化 ────────────────────────────────────────────────────
client = OpenAI(api_key=API_KEY, base_url=API_BASE, timeout=120.0)
fallback_client = OpenAI(api_key=MINIMAX_API_KEY_1, base_url=MINIMAX_API_BASE_1, timeout=120.0)
fallback2_client = OpenAI(api_key=FALLBACK2_API_KEY, base_url=FALLBACK2_API_BASE, timeout=120.0)

# MiniMax2 客户端（延迟初始化，支持动态更新 key）
_minimax2_client: Optional[OpenAI] = None

def get_minimax2_client() -> Optional[OpenAI]:
    global _minimax2_client
    if _minimax2_client is None and MINIMAX_API_KEY_2:
        _minimax2_client = OpenAI(api_key=MINIMAX_API_KEY_2, base_url=MINIMAX_API_BASE_2, timeout=240.0)
    return _minimax2_client

# ── 讯飞内容审核拦截判断 ───────────────────────────────────────────────
def is_xunfei_blocked(error_str: str) -> bool:
    """判断是否为讯飞内容审核拦截"""
    blocked_keywords = [
        "法律法规", "无法提供", "xunfei response error",
        "涉及国家安全", "健康和谐网络",
    ]
    err_lower = error_str.lower()
    return any(kw in err_lower for kw in blocked_keywords)

# ── opendataloader-pdf：确保 Java PATH 注入 ────────────────────────────
_JAVA_BIN = r"C:\Users\jeremyko11\AppData\Local\Programs\Microsoft\jdk-11.0.30.7-hotspot\bin"
if _JAVA_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _JAVA_BIN + os.pathsep + os.environ.get("PATH", "")

try:
    from opendataloader_pdf import convert as _odl_convert
    ODL_AVAILABLE = True
except ImportError:
    ODL_AVAILABLE = False

# ── PaddleOCR 延迟初始化 ────────────────────────────────────────────────
_paddle_ocr = None

def get_paddle_ocr():
    global _paddle_ocr
    if _paddle_ocr is None:
        try:
            os.environ.setdefault("FLAGS_use_mkldnn", "0")
            os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
            from paddleocr import PaddleOCR
            import logging
            logging.getLogger("ppocr").setLevel(logging.ERROR)
            _paddle_ocr = PaddleOCR(lang="ch", use_angle_cls=True)
            print("PaddleOCR ready (PP-OCRv5, angle_cls=True)")
        except Exception as e:
            print(f"PaddleOCR init failed: {e}, will use AI fallback")
            _paddle_ocr = False
    return _paddle_ocr if _paddle_ocr is not False else None

# ── 智能提取模块可用性 ─────────────────────────────────────────────────
try:
    from chunking import chunk_book_text, HierarchicalChunkingPipeline
    from extraction_pipeline import MultiRoundExtractionPipeline, extract_book_content
    from quality_control import QualityControlPipeline, check_material_quality
    SMART_EXTRACTION_AVAILABLE = True
    print("[Extraction] 智能提取模块已加载（分层Chunking + 多轮Pipeline + 质量评分）")
except ImportError as e:
    SMART_EXTRACTION_AVAILABLE = False
    print(f"[Extraction] 智能提取模块未加载: {e}")
