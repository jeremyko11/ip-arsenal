import sqlite3, json, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\data\arsenal.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 查找微博相关的sources
rows = conn.execute("SELECT id, title, type, url, status, char_count, created_at FROM sources WHERE url LIKE '%weibo%' OR title LIKE '%微博%' OR title LIKE '%1564834725%' OR title LIKE '%平原%' ORDER BY created_at DESC").fetchall()
print(f"找到 {len(rows)} 条微博相关source:")
for r in rows:
    print(f"  id={r['id']}")
    print(f"  title={r['title']}")
    print(f"  type={r['type']}")
    print(f"  url={r['url']}")
    print(f"  status={r['status']}")
    print(f"  char_count={r['char_count']}")
    print()

# 找相关的materials
for r in rows:
    mats = conn.execute("SELECT id, category, content FROM materials WHERE source_id=? LIMIT 3", (r['id'],)).fetchall()
    if mats:
        print(f"  [materials for {r['id'][:8]}...]:")
        for m in mats:
            print(f"    [{m['category']}] {m['content'][:150]}")
        print()

conn.close()
