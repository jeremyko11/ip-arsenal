"""
修复平原公子赵胜微博提炼
1. 读取 weibo_pygz.json 的 87 条真实内容
2. 清理数据库旧垃圾数据
3. 调用 AI 提炼（金句/故事/观点/实操/选题）
4. 写入数据库
"""
import sys, os, json, sqlite3, uuid
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import concurrent.futures, time

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# ── 配置 ──────────────────────────────────────────────────────────────
WEIBO_JSON  = r'C:\Users\jeremyko11\WorkBuddy\Claw\weibo_pygz.json'
DB_PATH     = r'C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\data\arsenal.db'
SOURCE_ID   = 'd4949dc7-d51f-4fcd-9e91-b095581cfe8a'
BLOGGER     = '平原公子赵胜'
MAX_WEIBOS  = 87  # 全部使用

# AI 配置（讯飞星辰）
XUNFEI_BASE = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
XUNFEI_KEY  = "d25220d05c80686af77fcc163c6fe92a:MmRkNjk3MzQ2MGQzMDllNzAyZjM3Mzg0"
XUNFEI_MODEL= "astron-code-latest"

# 备用1: MiniMax
FALLBACK1_BASE  = "https://llm.chudian.site/v1"
FALLBACK1_KEY   = "sk-ag-0e87970be36f68d06e47e7a49cceb64d"
FALLBACK1_MODEL = "minimax-m2.7"

# 备用2: DeepSeek
FALLBACK2_BASE  = "https://api.deepseek.com/v1"
FALLBACK2_KEY   = "sk-ab948053383f436fb1cf50639f57b439"
FALLBACK2_MODEL = "deepseek-chat"

def now():
    return datetime.now().isoformat()

# ── Step 1: 读取微博内容 ──────────────────────────────────────────────
print("📖 Step 1: 读取微博内容...")
with open(WEIBO_JSON, 'r', encoding='utf-8') as f:
    data = json.load(f)

weibos = data.get('weibos', [])
print(f"   读取到 {len(weibos)} 条微博")

# 组装文本
text_parts = []
for i, w in enumerate(weibos[:MAX_WEIBOS]):
    text = w.get('text', '').strip()
    if text and len(text) > 10:
        text_parts.append(f"【微博 {i+1}】{text}")

full_text = "\n\n".join(text_parts)
print(f"   有效内容: {len(text_parts)} 条，{len(full_text):,} 字")

# 截断（避免超过 token 限制）
MAX_CHARS = 60000
if len(full_text) > MAX_CHARS:
    full_text = full_text[:MAX_CHARS]
    print(f"   截断至 {MAX_CHARS:,} 字")

# ── Step 2: 清理旧数据 ───────────────────────────────────────────────
print("\n🗑️  Step 2: 清理旧垃圾数据...")
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")
conn.row_factory = sqlite3.Row

old_mats = conn.execute("SELECT COUNT(*) as cnt FROM materials WHERE source_id=?", (SOURCE_ID,)).fetchone()['cnt']
print(f"   旧素材 {old_mats} 条 → 全部删除")
conn.execute("DELETE FROM materials WHERE source_id=?", (SOURCE_ID,))

# 更新 source 记录
conn.execute("""UPDATE sources SET 
    title=?, char_count=?, status='processing', error_msg=NULL, updated_at=?
    WHERE id=?""",
    (f"@{BLOGGER} 微博精华（{len(text_parts)}条）", len(full_text), now(), SOURCE_ID))
conn.commit()
print(f"   source 已更新: title=@{BLOGGER} 微博精华（{len(text_parts)}条）")

# ── Step 3: AI 提炼 ───────────────────────────────────────────────────
SYSTEM_PROMPT = """你是个人IP内容素材提炼专家，专门从博主内容中提炼可复用的IP素材。
你的任务：从微博博主的原创内容中，精准提炼出：
- 金句弹药库（有杀伤力、可直接改写用的观点句）
- 故事与案例（有情节的、有反转的、有爆点的素材）
- 认知与观点（颠覆常识的、有角度的洞察）
- 实操行动库（具体可用的方法、建议、策略）
- 爆款选题（可延伸的话题、场景、切入角度）

提炼原则：
1. 只提炼真正有价值的素材，宁缺毋滥
2. 保留原文的语言风格和锐度，不要稀释
3. 标注风险（涉及政治/争议话题标⚠️）
4. 每条素材要有实际的传播价值

输出格式必须严格遵守，方便解析入库。"""

USER_PROMPT = f"""请对微博博主 @{BLOGGER} 的以下 {len(text_parts)} 条微博内容进行地毯式提炼：

【内容来源】
{full_text}

---

请按以下格式严格输出：

## 【第一部分：金句弹药库】
格式（每条完整填写）：
> [场景标签] 金句内容 【适用场景】
> ⚠️ 风险标签：✅安全 / ⚠️需语境 / ❌禁用
> 🎯 爆点场景：🔥爆款 / 💡治愈 / 📚深度
> ⏳ 改写成本：⚡0成本 / ✂️中成本 / 🛠️高成本
> 🕒 时效熔断：🟢长效 / 🟡半年 / 🔴当季

（尽量提炼15-25条有价值的金句）

## 【第二部分：故事与案例】
**故事/案例标题（用原文中的真实事件或逻辑）**
背景：...
核心：...
反转/结论：...
⚠️ 风险：✅安全 / ⚠️需语境 / ❌禁用
🎯 爆点：...

（尽量提炼8-12个有价值的故事案例）

## 【第三部分：认知与观点】
**观点标题（要有冲击力）**
核心论点：...
支撑逻辑：...
适用场景：...
⚠️ 风险标签：✅安全 / ⚠️需语境 / ❌禁用

（尽量提炼10-15个有价值的认知）

## 【第四部分：实操行动库】
**行动/方法名称**
适用场景：...
具体步骤：...
注意事项：...

（尽量提炼6-10个可用的实操方法）

## 【第五部分：爆款选题库】
1. 选题：... | 角度：... | 目标人群：...
2. 选题：... | 角度：... | 目标人群：...
...
（提炼10-15个可延伸的选题方向）"""


def call_ai(base_url, api_key, model, system_prompt, user_prompt, max_tokens=12000):
    """调用 AI，返回 (content, model_used)"""
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=180.0)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return resp.choices[0].message.content, model


def ai_extract_with_fallback():
    providers = [
        (XUNFEI_BASE,   XUNFEI_KEY,   XUNFEI_MODEL,   "讯飞星辰"),
        (FALLBACK1_BASE, FALLBACK1_KEY, FALLBACK1_MODEL, "MiniMax"),
        (FALLBACK2_BASE, FALLBACK2_KEY, FALLBACK2_MODEL, "DeepSeek"),
    ]
    for base_url, api_key, model, name in providers:
        try:
            print(f"   🤖 尝试 {name}...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(call_ai, base_url, api_key, model, SYSTEM_PROMPT, USER_PROMPT)
                content, model_id = future.result(timeout=180)
            print(f"   ✅ {name} 成功，返回 {len(content):,} 字")
            return content, name
        except Exception as e:
            print(f"   ❌ {name} 失败: {e}")
            continue
    raise RuntimeError("所有 AI 提供商均失败")

print("\n🤖 Step 3: 调用 AI 提炼（最长3分钟）...")
raw_content, model_used = ai_extract_with_fallback()

# ── Step 4: 解析素材 ─────────────────────────────────────────────────
print("\n📊 Step 4: 解析素材...")

def parse_materials(source_id, raw_content):
    lines = raw_content.split("\n")
    current_cat = "quote"
    current_block = []
    materials = []
    now_str = now()

    cat_map = {
        "第一部分": "quote",  "金句弹药库": "quote",
        "第二部分": "case",   "故事与案例": "case",
        "第三部分": "viewpoint", "认知与观点": "viewpoint",
        "第四部分": "action", "实操行动库": "action",
        "第五部分": "topic",  "爆款选题": "topic",
    }

    def flush_block():
        content = "\n".join(current_block).strip()
        if content and len(content) > 10:
            materials.append({
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "category": current_cat,
                "content": content,
                "metadata": "{}",
                "tags": "[]",
                "platform": "",
                "use_count": 0,
                "is_starred": 0,
                "created_at": now_str,
            })

    for line in lines:
        # 检测分类切换
        new_cat = None
        for key, cat in cat_map.items():
            if key in line and ("##" in line or "【" in line):
                new_cat = cat
                break

        if new_cat:
            flush_block()
            current_block = []
            current_cat = new_cat
        else:
            # 金句单条切割（以 > 开头）
            if current_cat == "quote" and line.startswith("> ") and not any(x in line for x in ["风险标签", "爆点场景", "改写成本", "时效熔断"]):
                if current_block:
                    flush_block()
                current_block = [line]
            elif current_cat == "quote" and line.startswith("> "):
                current_block.append(line)
            # 案例/观点/行动 — 以 ** 开头新条目
            elif current_cat in ("case","viewpoint","action") and line.startswith("**") and line.endswith("**"):
                if current_block:
                    flush_block()
                current_block = [line]
            # 选题 — 数字序号开头
            elif current_cat == "topic" and line.strip() and line.strip()[0].isdigit() and ". " in line:
                if current_block:
                    flush_block()
                current_block = [line]
            elif current_block:
                current_block.append(line)

    flush_block()
    return materials

materials = parse_materials(SOURCE_ID, raw_content)
print(f"   解析出 {len(materials)} 条素材")

cat_counts = {}
for m in materials:
    cat_counts[m['category']] = cat_counts.get(m['category'], 0) + 1
for cat, cnt in cat_counts.items():
    print(f"   [{cat}] {cnt} 条")

# ── Step 5: 写入数据库 ───────────────────────────────────────────────
print("\n💾 Step 5: 写入数据库...")
for m in materials:
    conn.execute(
        "INSERT OR REPLACE INTO materials VALUES (?,?,?,?,?,?,?,?,?,?)",
        (m["id"], m["source_id"], m["category"], m["content"],
         m["metadata"], m["tags"], m["platform"],
         m["use_count"], m["is_starred"], m["created_at"])
    )

conn.execute("UPDATE sources SET status='done', char_count=?, updated_at=? WHERE id=?",
             (len(full_text), now(), SOURCE_ID))
conn.commit()
conn.close()
print(f"   ✅ 写入完成！共 {len(materials)} 条素材")

print(f"\n🎉 全部完成！@{BLOGGER} 的 {len(text_parts)} 条微博已提炼为 {len(materials)} 条IP素材")
print(f"   AI 模型：{model_used}")
print(f"\n请刷新 IP 军火库（http://localhost:8765）查看提炼结果！")

# 保存原始输出供参考
with open(r'C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\backend\weibo_extract_raw.txt', 'w', encoding='utf-8') as f:
    f.write(raw_content)
print("   原始AI输出已保存到 weibo_extract_raw.txt")
