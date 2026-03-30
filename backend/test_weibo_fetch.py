import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_fetch():
    url = "https://www.weibo.com/u/1564834725"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        resp = await c.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        print(f"状态码: {resp.status_code}")
        print(f"最终URL: {resp.url}")
        print(f"响应大小: {len(resp.text)} 字符")
        
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        print(f"提取文本长度: {len(text)}")
        print(f"前500字符:\n{text[:500]}")

asyncio.run(test_fetch())
