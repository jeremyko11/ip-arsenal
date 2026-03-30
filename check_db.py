import sqlite3
conn = sqlite3.connect('data/arsenal.db')
conn.row_factory = sqlite3.Row

rows = conn.execute('SELECT id, title, type, status, error_msg, file_path FROM sources ORDER BY created_at DESC LIMIT 10').fetchall()
print('=== SOURCES ===')
for r in rows:
    print('id=%s type=%-6s status=%-10s title=%s' % (r['id'][:8], r['type'], r['status'], r['title'][:40]))
    if r['error_msg']:
        print('  ERR:', r['error_msg'])
    if r['file_path']:
        print('  FILE:', r['file_path'])

print()
tasks = conn.execute('''
    SELECT t.source_id, t.status, t.progress, t.message 
    FROM tasks t 
    JOIN sources s ON t.source_id=s.id 
    ORDER BY s.created_at DESC LIMIT 10
''').fetchall()
print('=== TASKS ===')
for t in tasks:
    print('src=%-8s status=%-10s prog=%3s%% msg=%s' % (t['source_id'][:8], t['status'], t['progress'], t['message']))

conn.close()
