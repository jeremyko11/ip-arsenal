#!/usr/bin/env python3
# 全功能检测脚本
import urllib.request, json

BASE = 'http://localhost:8765'

def get(path):
    req = urllib.request.urlopen(BASE + path, timeout=5)
    return json.loads(req.read())

def post(path, data):
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=payload, headers={'Content-Type':'application/json'})
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())

print("=" * 50)
print("IP军火库 全功能检测")
print("=" * 50)

# 1. 书籍列表
try:
    d = get('/api/sources?limit=2')
    print(f"[OK] 书籍列表: {len(d)} 本书")
    src_id = d[0]['id'] if d else None
    src_title = d[0]['title'][:15] if d else None
except Exception as e:
    print(f"[FAIL] 书籍列表: {e}")
    src_id = None

# 2. 主题列表
try:
    d = get('/api/wechat-themes')
    print(f"[OK] 公众号主题: {len(d)} 个主题")
    first_theme = d[0]['id']
except Exception as e:
    print(f"[FAIL] 公众号主题: {e}")
    first_theme = 'wechat-native'

# 3. 排版测试
try:
    md = "# 测试标题\n\n**加粗**内容，*斜体*。\n\n> 引用段落\n\n- 列表1\n- 列表2"
    d = post('/api/wechat-format', {'content': md, 'theme': first_theme})
    html = d.get('html', '')
    has_inline = 'style=' in html
    print(f"[OK] 公众号排版: HTML长度={len(html)}, 内联样式={has_inline}")
except Exception as e:
    print(f"[FAIL] 公众号排版: {e}")

# 4. 朴树之道列表
try:
    d = get('/api/pushutree')
    print(f"[OK] 朴树之道列表: {len(d)} 个任务")
except Exception as e:
    print(f"[FAIL] 朴树之道列表: {e}")

# 5. 朴树之道创建（有书籍）
if src_id:
    try:
        d = post('/api/pushutree/create', {
            'source_id': src_id,
            'episode_count': 2,
            'platform': 'wechat',
            'style': '朴树之道风格'
        })
        print(f"[OK] 朴树之道创建: id={d['script_id'][:8]}..., status={d['status']}")
    except Exception as e:
        print(f"[FAIL] 朴树之道创建: {e}")
else:
    print("[SKIP] 朴树之道创建：无可用书籍")

print("=" * 50)
print("检测完成！")
