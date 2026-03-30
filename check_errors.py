import sqlite3

db_path = 'C:/Users/jeremyko11/WorkBuddy/Claw/ip-arsenal/data/arsenal.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

print("=== 各状态数量 ===")
for row in conn.execute("SELECT status, count(*) as cnt FROM sources GROUP BY status ORDER BY cnt DESC").fetchall():
    print(f"  {row['status']}: {row['cnt']}")

print("\n=== 出错书籍（最近10条）===")
rows = conn.execute("SELECT title, error_msg, updated_at FROM sources WHERE status='error' ORDER BY updated_at DESC LIMIT 10").fetchall()
for r in rows:
    print(f"[{r['updated_at']}] {r['title']}")
    print(f"  错误: {(r['error_msg'] or '无')[:150]}")
    print()

conn.close()
