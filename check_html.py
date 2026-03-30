import requests, json

r = requests.post('http://127.0.0.1:8765/api/wechat-format', 
    json={'content': '## 测试\n**加粗**，*斜体*\n\n> 引用\n\n- 列表1\n- 列表2', 'theme': 'wechat-native'})
html = r.json()['html']

dq_count = html.count('"')
print('双引号数量:', dq_count)
print('HTML前300字符:')
print(html[:300])
print()
print('HTML中是否含有style=":')
import re
matches = re.findall(r'style="[^"]{0,50}', html)
print(f'找到 {len(matches)} 个style属性，前3个:')
for m in matches[:3]:
    print(' ', repr(m))
