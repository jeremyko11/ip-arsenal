import sqlite3
conn = sqlite3.connect('data/arsenal.db')
c = conn.cursor()

c.execute('SELECT status, COUNT(*) FROM sources GROUP BY status')
print('=== 状态统计 ===')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}本')

c.execute("SELECT title, status, updated_at FROM sources WHERE status IN ('pending','processing') ORDER BY updated_at")
print('=== 卡住的书 ===')
stuck = c.fetchall()
for r in stuck:
    print(f'  [{r[1]}] {r[0]} | 最后更新:{r[2]}')

print(f'\n共卡住 {len(stuck)} 本')
conn.close()
