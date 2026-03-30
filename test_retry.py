import urllib.request, json

BASE = 'http://localhost:8765'

r = urllib.request.urlopen(BASE + '/api/sources?limit=1', timeout=5)
sources = json.loads(r.read())
sid = sources[0]['id']
title = sources[0]['title'][:20]
status = sources[0]['status']
print(f'测试书籍: {title}, 当前状态: {status}')

# 调用重试接口
payload = b''
req = urllib.request.Request(
    f'{BASE}/api/sources/{sid}/retry',
    data=payload,
    method='POST',
    headers={'Content-Length': '0'}
)
resp = urllib.request.urlopen(req, timeout=10)
d = json.loads(resp.read())
print('重试接口返回:', d)
print('OK =', d.get('ok'), ', task_id =', d.get('task_id', '')[:12] + '...')
