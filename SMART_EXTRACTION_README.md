# IP Arsenal 智能提取增强版

## 新增功能概览

本次升级引入了三个核心模块，大幅提升书籍内容提取的质量和效率：

### 1. 分层 Chunking 模块 (`chunking.py`)
- **功能**：保留书籍结构，按章节语义切分文本
- **优势**：
  - 识别章节层级结构
  - 语义段落切分（避免句子断裂）
  - 维护 chunk 间的前后文关联
  - 生成 chunk 摘要和关键词

### 2. 多轮迭代提取 Pipeline (`extraction_pipeline.py`)
- **功能**：四轮递进式内容提取
- **流程**：
  - Round 1: 结构理解（轻量模型）- 提取大纲、核心论点
  - Round 2: 逐章深度提取（强模型）- 金句/案例/观点/行动
  - Round 3: 跨章节关联分析（强模型）- 主题关联、观点演变
  - Round 4: IP化选题生成（创意模型）- 爆款选题、平台适配

### 3. 质量评分模块 (`quality_control.py`)
- **功能**：素材入库前的多维质量评估
- **维度**：
  - 完整度：字段是否齐全
  - 唯一性：与已有素材去重
  - IP契合度：与 IP 方向的匹配
  - 可执行性：是否具体可操作
  - 风险等级：内容安全性
- **路由**：自动批准 / 人工审核 / 自动丢弃

---

## API 使用方式

### 启动智能提取（新版）

```bash
POST /api/sources/{source_id}/extract-smart
```

**参数**：
- `source_id`: 书籍来源ID
- `mode`: 提取模式（暂时只支持 "full"）

**响应**：
```json
{
  "task_id": "xxx",
  "source_id": "xxx",
  "mode": "smart",
  "message": "智能提取任务已创建"
}
```

### 对比新旧提取方式（测试用）

```bash
POST /api/sources/{source_id}/extract-compare
```

会同时创建两个任务：
- 原版提取任务
- 智能版提取任务

方便对比效果。

### 获取素材质量详情

```bash
GET /api/materials/{material_id}/quality
```

**响应**：
```json
{
  "material_id": "xxx",
  "quality_score": {
    "completeness": 0.9,
    "uniqueness": 1.0,
    "ip_fit": 0.85,
    "actionable": 0.9,
    "risk_level": "safe",
    "overall": 0.88
  },
  "suggestions": ["改进建议1", "改进建议2"]
}
```

---

## 与原版的对比

| 特性 | 原版 | 智能版 |
|------|------|--------|
| 文本切分 | 简单截断（80000字符） | 分层语义切分（保留结构） |
| 提取方式 | 单次 AI 调用 | 四轮迭代递进 |
| 质量把控 | 无 | 五维评分+智能路由 |
| 跨章关联 | 无 | 自动分析主题关联 |
| IP选题 | 简单映射 | 多平台爆款生成 |
| 入库控制 | 全部入库 | 自动/审核/丢弃分级 |

---

## 配置说明

### 环境变量

```bash
# 可选：百度 AI Studio Token（用于 OCR）
set AISTUDIO_TOKEN=your_token_here
```

### 质量评分阈值

在 `quality_control.py` 中可调整：

```python
THRESHOLDS = {
    "auto_approve": 0.80,    # 自动入库阈值
    "human_review": 0.55,    # 人工审核阈值
    "auto_discard": 0.30     # 自动丢弃阈值
}
```

### IP 方向关键词

在 `quality_control.py` 中可自定义：

```python
IP_KEYWORDS = {
    "职场认知升级": ["职场", "工作", ...],
    "人性洞察": ["人性", "心理", ...],
    "个人成长破局": ["成长", "突破", ...]
}
```

---

## 测试

运行测试脚本验证模块：

```bash
cd C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal
python test_smart_extraction.py
```

---

## 后续优化建议

1. **向量化检索**：集成 sentence-transformers + FAISS，实现语义搜索
2. **人机审核界面**：前端增加待审核素材的展示和操作
3. **反馈闭环**：记录用户对素材的使用情况，优化评分模型
4. **增量更新**：支持书籍内容更新时的增量提取
5. **多模态支持**：提取图片、图表中的信息

---

## 文件结构

```
backend/
├── main.py                    # 主服务（已集成新模块）
├── chunking.py               # 分层 Chunking 模块 [新增]
├── extraction_pipeline.py    # 多轮迭代提取 [新增]
├── quality_control.py        # 质量评分模块 [新增]
└── ip_arsenal.db            # SQLite 数据库

test_smart_extraction.py      # 测试脚本 [新增]
```

---

## 注意事项

1. 智能提取流程比原版耗时更长（约 2-5 倍），但质量显著提升
2. 建议先用 `/extract-compare` 对比效果，再决定是否全面切换
3. 质量评分依赖已有素材库，首次使用时唯一性评分会偏高
4. 多轮 Pipeline 的 API 调用成本更高，但三级降级机制确保可用性
