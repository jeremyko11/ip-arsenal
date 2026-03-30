"""对一本失败的书触发重试，然后轮询状态观察降级流程"""
import urllib.request, json, time

BASE = 'http://localhost:8765'

def get(path):
    r = urllib.request.urlopen(BASE + path, timeout=10)
    return json.loads(r.read())

def post(path, data=None):
    payload = json.dumps(data).encode() if data else b''
    req = urllib.request.Request(BASE + path, data=payload, method='POST',
                                  headers={'Content-Type':'application/json','Content-Length':str(len(payload))})
    r = urllib.request.urlopen(req, timeout=10)
    return json.loads(r.read())

# 找到失败的书
sources = get('/api/sources?limit=50')
errors = [s for s in sources if s['status'] == 'error']
print(f'失败书籍: {len(errors)} 本')
if not errors:
    print('没有失败书籍，测试结束')
    exit()

s = errors[0]
sid = s['id']
title = s['title']
print(f'\n对《{title}》触发重试...')

res = post(f'/api/sources/{sid}/retry')
task_id = res['task_id']
print(f'重试任务ID: {task_id[:12]}...')

# 轮询状态
for i in range(30):
    time.sleep(5)
    task = get(f'/api/tasks/{task_id}')
    status = task['status']
    progress = task['progress']
    message = task['message'][:80]
    print(f'  [{i+1}] status={status} progress={progress}% msg={message}')
    if status in ('done', 'error'):
        print(f'\n最终结果: {status}')
        src = get(f'/api/sources?limit=50')
        updated = next((x for x in src if x['id'] == sid), None)
        if updated:
            print(f'书籍状态: {updated["status"]}')
            print(f'错误信息: {updated.get("error_msg","")[:200]}')
        break
