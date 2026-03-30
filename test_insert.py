import sqlite3, uuid

DB_PATH = r'C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\data\arsenal.db'

def now():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

source_id = '5e91f2b3-25a5-4a6f-be2f-f4acdef2e7f5'
src = conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
print("src found:", src is not None)
source_title = src["title"]
print("source_title:", repr(source_title))

script_id = str(uuid.uuid4())
print("script_id:", script_id)

try:
    conn.execute(
        "INSERT INTO scripts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (script_id, source_id, source_title,
         4, "test", "test",
         "pending", 0, "等待生成...",
         "[]", "[]", None, now(), now())
    )
    conn.commit()
    print("INSERT OK!")
except Exception as e:
    print("INSERT FAILED:", e)

conn.close()
