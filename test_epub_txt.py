"""
测试 epub/txt 文本提取 + AI 调用，找出三级全部失败的根因
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.dirname(__file__))

# 加载配置
import json
config = json.load(open('config.json', encoding='utf-8'))

from main import extract_text_from_epub, extract_text_from_txt, ai_extract, build_prompt, MAX_CHARS
import sqlite3

DB = 'data/arsenal.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM sources WHERE type IN ('epub','txt') ORDER BY created_at DESC LIMIT 5").fetchall()
conn.close()

for src in rows:
    print(f"\n{'='*60}")
    print(f"书名: {src['title']}  type={src['type']}")
    fpath = src['file_path']
    if not fpath or not os.path.exists(fpath):
        print(f"  文件不存在: {fpath}")
        continue

    # 1. 测试文本提取
    print(f"  文件: {fpath}")
    if src['type'] == 'epub':
        text, pages, _ = extract_text_from_epub(fpath)
    else:
        text, pages, _ = extract_text_from_txt(fpath)

    print(f"  提取字数: {len(text)}, 章节数: {pages}")
    if not text:
        print("  !! 文本提取为空！")
        continue

    print(f"  文本片段: {text[:200]!r}")

    # 2. 测试 AI 提炼（只用前 5000 字测试，避免超限）
    short_text = text[:5000]
    sys_p, usr_p = build_prompt(src['title'], short_text, 'full')
    print(f"\n  Prompt 总字数: sys={len(sys_p)} usr={len(usr_p)}")

    print("  测试 AI 调用...")
    try:
        result, model = ai_extract(sys_p, usr_p, max_tokens=3000, temperature=0.7)
        print(f"  AI 成功！model={model}  输出前100字: {result[:100]}")
    except Exception as e:
        print(f"  AI 全部失败: {e}")

print("\n完成")
