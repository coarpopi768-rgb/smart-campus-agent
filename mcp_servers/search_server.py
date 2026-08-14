"""MCP Server —— 百度百科搜索服务（MCP stdio 协议）
用法：python mcp_servers/search_server.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re, requests
from urllib.parse import quote

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


server = Server("campus-search")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="baidu_baike_search",
            description="通过百度百科搜索外部知识，返回百科条目摘要",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如：什么是机器学习"
                    }
                },
                "required": ["query"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "baidu_baike_search":
        query = arguments.get("query", "").strip()
        if not query:
            return [TextContent(type="text", text="[Error] 搜索关键词不能为空")]

        url = f"https://baike.baidu.com/item/{quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            resp = requests.get(url, headers=headers, timeout=8)
            resp.encoding = "utf-8"
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = re.sub(r"\s+", " ", text).strip()

            summary = text[:1000]
            if len(text) > 1000:
                summary += "..."

            if not summary.strip():
                return [TextContent(type="text", text=f"[No result] 未找到百科条目: {query}")]

            return [TextContent(type="text", text=f"[Baidu Baike] {query}\n{summary}")]

        except requests.Timeout:
            return [TextContent(type="text", text=f"[Error] 搜索超时: {query}")]
        except Exception as e:
            return [TextContent(type="text", text=f"[Error] {e}")]

    return [TextContent(type="text", text=f"[Error] 未知工具: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
