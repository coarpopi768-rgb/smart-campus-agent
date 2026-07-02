"""
Baidu Baike search tool
"""
import requests
from urllib.parse import quote
from langchain_core.tools import tool


@tool
def baidu_search(query: str) -> str:
    """
    Search Baidu Baike for encyclopedia entries.

    Args:
        query: Search keyword
    """
    if not query.strip():
        return "[Error] Search keyword cannot be empty."

    url = f"https://baike.baidu.com/item/{quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        resp.encoding = "utf-8"
        content = resp.text

        import re
        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip()

        summary = text[:1000]
        if len(text) > 1000:
            summary += "..."

        if not summary.strip():
            return f"[No result] No Baike entry found for: {query}"

        return f"[Baidu Baike] {query}\n{summary}"

    except requests.Timeout:
        return f"[Error] Search timeout for: {query}"
    except requests.RequestException as e:
        return f"[Error] Search failed: {str(e)}"
    except Exception as e:
        return f"[Error] Unexpected: {str(e)}"
