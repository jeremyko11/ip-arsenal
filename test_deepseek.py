"""测试 DeepSeek API 是否可用"""
import sys
sys.path.insert(0, 'backend')

from openai import OpenAI

FALLBACK2_BASE = "https://api.deepseek.com/v1"
FALLBACK2_KEY = "sk-ab948053383f436fb1cf50639f57b439"
FALLBACK2_MODEL = "deepseek-chat"

client = OpenAI(api_key=FALLBACK2_KEY, base_url=FALLBACK2_BASE)

print("测试 DeepSeek...")
try:
    resp = client.chat.completions.create(
        model=FALLBACK2_MODEL,
        messages=[
            {"role": "user", "content": "你好，回复'DeepSeek可用'三个字"}
        ],
        max_tokens=50,
        timeout=30
    )
    print(f"[OK] DeepSeek 可用: {resp.choices[0].message.content}")
except Exception as e:
    print(f"[FAIL] DeepSeek 失败: {e}")
