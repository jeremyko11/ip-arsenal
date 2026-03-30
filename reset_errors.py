"""重置错误书籍状态为 pending，让 worker 重新处理"""
import sqlite3

conn = sqlite3.connect('data/arsenal.db')
conn.row_factory = sqlite3.Row

# 找所有出错的书
rows = conn.execute("""
    SELECT s.id as sid, s.title, s.type, t.id as tid
    FROM sources s
    LEFT JOIN tasks t ON t.source_id = s.id
    WHERE s.status = 'error'
    AND s.type IN ('epub', 'txt', 'docx')
    ORDER BY s.created_at DESC
""").fetchall()

print(f"找到 {len(rows)} 本出错的文字书籍:")
for r in rows:
    print(f"  [{r['type']}] {r['title']}")

from datetime import datetime
now = datetime.now().isoformat()

for r in rows:
    conn.execute(
        "UPDATE sources SET status='pending', error_msg=NULL, updated_at=? WHERE id=?",
        (now, r['sid'])
    )
    if r['tid']:
        conn.execute(
            "UPDATE tasks SET status='pending', progress=0, message='等待重新处理...', updated_at=? WHERE id=?",
            (now, r['tid'])
        )

conn.commit()
conn.close()
print("完成！重置为 pending，重启后端后会自动重新处理。")
