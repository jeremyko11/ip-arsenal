# IP Arsenal · IP 军火库

> 个人知识资产管理平台 - 专注于内容提取、chunking 与智能整理

[English](./README_en.md) | [Español](./README_es.md)

## 功能特性

### 核心能力
- **多格式内容提取** - 支持 PDF、EPUB、TXT、DOCX 等格式的智能内容提取
- **智能 Chunking** - 基于语义的分层文本分块技术
- **多轮提取 Pipeline** - 迭代式内容质量优化
- **质量评分系统** - 自动评估素材质量等级
- **微信公众号格式转换** - 支持多种主题样式的微信文章生成

### 技术亮点
- AI 驱动的语义分析
- 快速 OCR 文字识别（可选 PaddleOCR）
- 高精度 PDF 解析（可选 opendataloader-pdf）
- RESTful API 设计
- 响应式 Web 界面
- **MediaCrawler 数据接入** - 支持导入社交媒体采集数据

## 项目结构

```
ip-arsenal/
├── frontend/              # Web 前端
│   └── index.html        # 单页应用
├── backend/              # Python 后端
│   ├── main.py          # FastAPI 主服务
│   ├── chunking.py      # 分块算法
│   ├── extraction_pipeline.py  # 提取管道
│   └── quality_control.py     # 质量控制
├── themes/               # 微信主题配置
├── wechat-format/        # 微信格式转换
├── data/                 # 数据存储
├── uploads/              # 上传文件
└── config.json          # 配置文件
```

## 快速开始

### 环境要求
- Python 3.8+
- Windows / macOS / Linux

### 安装

```bash
# 克隆仓库
git clone https://github.com/jeremyko11/ip-arsenal.git
cd ip-arsenal

# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m uvicorn backend.main:app --reload --port 8765
```

### 启动方式

**方式一：命令行**
```bash
python backend/main.py
```

**方式二：一键启动（Windows）**
```bash
start_all.bat
```

**方式三：Docker（待实现）**
```bash
docker build -t ip-arsenal .
docker run -p 8765:8765 ip-arsenal
```

## 配置

编辑 `config.json` 修改基础配置：

```json
{
  "output_dir": "./data/wechat-output",
  "settings": {
    "default_theme": "wechat-native",
    "auto_open_browser": false
  },
  "media_crawler": {
    "data_dir": "D:/P-workplace/MediaCrawler-main/data"
  }
}
```

### MediaCrawler 数据接入

IP Arsenal 支持导入 [MediaCrawler](https://github.com/Netease-Crypto/MediaCrawler) 采集的社交媒体数据：

1. 安装并配置 MediaCrawler
2. 在 `config.json` 中设置 `media_crawler.data_dir` 指向 MediaCrawler 的 data 目录
3. 支持的平台：抖音、小红书、微博、快手、B站、贴吧、知乎

### API 密钥配置

在 `backend/main.py` 中配置你的 API 密钥：
- `API_KEY` - 讯飞星火 API
- `MINIMAX_API_KEY_1` - MiniMax API

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8765/docs
- ReDoc: http://localhost:8765/redoc

## 主题样式

内置 20+ 微信文章主题，包括：
- `wechat-native` - 原生微信风格
- `minimal-blue` - 简约蓝
- `elegant-green` - 优雅绿
- `magazine` - 杂志风
- `sspai` -少数派风格

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | 原生 HTML/CSS/JS |
| 后端 | FastAPI + Python |
| 数据库 | SQLite |
| AI | OpenAI / 讯飞星火 / MiniMax |

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
