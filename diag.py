import sqlite3

conn = sqlite3.connect('data/arsenal.db')
conn.row_factory = sqlite3.Row

# 先查 schema
print("=== sources 表结构 ===")
cols = conn.execute("PRAGMA table_info(sources)").fetchall()
for c in cols:
    print(f"  {c['name']} {c['type']}")
print()

print("=== tasks 表结构 ===")
cols2 = conn.execute("PRAGMA table_info(tasks)").fetchall()
for c in cols2:
    print(f"  {c['name']} {c['type']}")
print()

# 查这两本书
rows = conn.execute("""
    SELECT s.id, s.title, s.type, s.status, s.error_msg,
           t.status as task_status, t.progress, t.message
    FROM sources s 
    LEFT JOIN tasks t ON t.source_id = s.id 
    WHERE s.title LIKE '%厚黑学%' OR s.title LIKE '%跃迁%'
    ORDER BY s.created_at DESC
""").fetchall()

for r in rows:
    print(f"=== {r['title']} ===")
    print(f"  type={r['type']} status={r['status']} task={r['task_status']} prog={r['progress']}%")
    print(f"  error_msg: {r['error_msg']}")
    print(f"  task_msg: {r['message']}")
    print()

conn.close()
