import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/jeremyko11/WorkBuddy/Claw/weibo_pygz.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"博主: {data.get('blogger')}")
print(f"URL: {data.get('url')}")
print(f"爬取时间: {data.get('crawled_at')}")
print(f"总数: {data.get('total')}")

weibos = data.get('weibos', [])
print(f"实际weibos条数: {len(weibos)}")

if weibos:
    print(f"\n第一条字段: {list(weibos[0].keys()) if isinstance(weibos[0], dict) else type(weibos[0])}")
    print("\n前5条内容预览:")
    for i, w in enumerate(weibos[:5]):
        if isinstance(w, dict):
            text = w.get('text', w.get('content', ''))
            print(f"\n[{i+1}] {text[:200]}")
        else:
            print(f"[{i+1}] {str(w)[:200]}")
