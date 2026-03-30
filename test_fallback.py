"""测试备用模型 MiniMax 是否可达"""
from openai import OpenAI

FALLBACK_API_BASE = "https://llm.chudian.site/v1"
FALLBACK_API_KEY  = "sk-ag-0e87970be36f68d06e47e7a49cceb64d"
FALLBACK_MODEL_ID = "minimax-m2.7"

client = OpenAI(api_key=FALLBACK_API_KEY, base_url=FALLBACK_API_BASE)

try:
    resp = client.chat.completions.create(
        model=FALLBACK_MODEL_ID,
        messages=[
            {"role": "user", "content": "请用一句话介绍《欲望心理学》这本书的核心主题。"}
        ],
        max_tokens=200,
        temperature=0.7,
    )
    content = resp.choices[0].message.content
    print("备用模型 OK！")
    print("回答：", content[:200])
except Exception as e:
    print("备用模型失败：", e)
