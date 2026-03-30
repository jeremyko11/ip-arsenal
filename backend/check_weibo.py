import sqlite3

conn = sqlite3.connect(r'C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\data\arsenal.db')
conn.row_factory = sqlite3.Row

# 看所有表
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("所有表:")
for t in tables:
    print(f"  {t['name']}")

print()

source_id = 'd4949dc7-d51f-4fcd-9e91-b095581cfe8a'

# 找这个source相关的素材
for tname in ['materials', 'snippets', 'assets', 'knowledge', 'extracts']:
    try:
        rows = conn.execute(f"SELECT * FROM {tname} WHERE source_id=? LIMIT 3", (source_id,)).fetchall()
        if rows:
            print(f"\n在 {tname} 找到 {len(rows)} 条:")
            for r in rows:
                for key in r.keys():
                    val = r[key]
                    if val and isinstance(val, str) and len(val) > 200:
                        print(f"  {key}: {val[:200]}...")
                    else:
                        print(f"  {key}: {val}")
        else:
            # 检查表是否存在列
            cols = conn.execute(f"PRAGMA table_info({tname})").fetchall()
            col_names = [c['name'] for c in cols]
            if 'source_id' in col_names:
                print(f"  {tname}: 无匹配记录")
            else:
                print(f"  {tname}: 无source_id字段")
    except Exception as e:
        pass

conn.close()
