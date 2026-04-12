# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IP Arsenal (IP 军火库) is a personal knowledge asset management platform focused on content extraction, chunking, and intelligent organization. It supports importing from PDFs, EPUBs, and social media via MediaCrawler.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start backend (development with hot reload)
python -m uvicorn backend.main:app --reload --port 8765

# Or run directly
python backend/main.py

# Windows一键启动
start_all.bat
```

## Architecture

### Backend (Python/FastAPI)
- `backend/main.py` (~5100 lines) - Main API server. Contains all REST endpoints and business logic.
- `backend/chunking.py` - Hierarchical book text chunking with chapter detection
- `backend/extraction_pipeline.py` - Multi-round AI extraction pipeline (Round 1-4 for structure, depth, cross-ref, IP选题)
- `backend/quality_control.py` - Material quality scoring (completeness, uniqueness, IP fit, risk)

### Frontend (Native HTML/CSS/JS SPA)
- `frontend/index.html` - Single-page application, ~212KB

### Database
- SQLite at `backend/arsenal.db` (also `ip_arsenal.db`)

### AI Integration
- Primary: MiniMax via `llm.chudian.site` proxy
- Fallback: 讯飞星火 (API_KEY), MiniMax account 2
- Fallback chain implemented in `_build_model_chain()` with timeout handling

## Key API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/sources/upload-pdf` | Upload and process PDF |
| `POST /api/sources/add` | Add source URL |
| `GET /api/materials` | List materials |
| `POST /api/rewrite` | AI content rewriting |
| `POST /api/wechat-format` | Convert to WeChat article format |
| `POST /api/pushutree/create` | Create writing script |
| `GET /api/media/files` | MediaCrawler files |
| `POST /api/sources/{id}/extract-smart` | Smart multi-round extraction |

## Configuration

- `config.json` - Output directory, WeChat settings, MediaCrawler data path
- API keys hardcoded in `backend/main.py` (API_KEY, MINIMAX_API_KEY_1, etc.)
- Java 11 path hardcoded for opendataloader-pdf OCR: `C:\Users\jeremyko11\AppData\Local\Programs\Microsoft\jdk-11.0.30.7-hotspot\bin`

## Smart Extraction Pipeline

The intelligent extraction uses a 4-round pipeline:
1. **Round 1**: Structure understanding (lightweight model) - outline, core arguments
2. **Round 2**: Per-chapter deep extraction (strong model) - quotes/cases/viewpoints/actions
3. **Round 3**: Cross-chapter analysis (strong model) - theme relationships
4. **Round 4**: IP topic generation (creative model) - viral topics, platform adaptation

Quality scoring dimensions: completeness, uniqueness, IP fit, actionability, risk level.

## MediaCrawler Integration

Located at `C:\Users\jeremyko11\WorkBuddy\Claw\media_crawler`. Data imported via `/api/media/import`. Supported platforms: 抖音, 小红书, 微博, 快手, B站, 贴吧, 知乎.

## Dependencies

Key packages: fastapi, uvicorn, pydantic, fitz (PyMuPDF), openai, httpx, beautifulsoup4, Pillow, numpy. Optional: paddleocr, opendataloader-pdf.
