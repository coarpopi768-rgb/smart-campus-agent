import requests
from urllib.parse import quote
from langchain_core.tools import tool

@tool
def baidu_search(query: str):
    """百度百科搜索，用于查询名词、知识点、人物等百科信息
    参数：
        query: 要搜索的关键词
    """
    url = f"https://baike.baidu.com/item/{quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        resp.encoding = "utf-8"  # 指定编码，防止乱码
        # 截取内容并简单精简，避免返回冗余HTML
        content = resp.text
        return content[:1500]
    except Exception as e:
        return f"搜索失败，错误信息：{str(e)}"