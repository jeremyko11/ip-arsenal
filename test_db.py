import sqlite3
DB_PATH = r'C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\data\arsenal.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# 查看 sources 表结构
cols = [row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()]
print("sources 列:", cols)

# 查看 scripts 表结构
cols2 = [row[1] for row in conn.execute("PRAGMA table_info(scripts)").fetchall()]
print("scripts 列:", cols2)
print("scripts 列数:", len(cols2))

# 查目标书籍
src = conn.execute("SELECT * FROM sources WHERE id=?", ('5e91f2b3-25a5-4a6f-be2f-f4acdef2e7f5',)).fetchone()
if src:
    print("书籍:", dict(src))
else:
    print("书籍不存在！")

conn.close()
