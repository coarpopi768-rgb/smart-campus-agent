"""MCP Server —— 邮件发送服务（MCP stdio 协议）
用法：python mcp_servers/email_server.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import EMAIL_USER, EMAIL_PASSWORD

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


server = Server("campus-email")

# 仅教师和管理员可发送邮件
ALLOWED_ROLES = {"admin", "teacher"}


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email))


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="send_campus_email",
            description="发送校园通知邮件。仅教师(teacher)和管理员(admin)角色可用",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "收件人邮箱地址"
                    },
                    "subject": {
                        "type": "string",
                        "description": "邮件主题"
                    },
                    "body": {
                        "type": "string",
                        "description": "邮件正文"
                    },
                    "user_role": {
                        "type": "string",
                        "description": "调用者角色：admin / teacher",
                        "enum": ["admin", "teacher"]
                    }
                },
                "required": ["to", "subject", "body", "user_role"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "send_campus_email":
        return [TextContent(type="text", text=f"[Error] 未知工具: {name}")]

    role = arguments.get("user_role", "guest")
    if role not in ALLOWED_ROLES:
        return [TextContent(type="text", text=f"[权限不足] 当前角色({role})没有发送邮件的权限，仅教师和管理员可发送邮件")]

    to = arguments.get("to", "").strip()
    subject = arguments.get("subject", "").strip()
    body = arguments.get("body", "").strip()

    if not EMAIL_USER or not EMAIL_PASSWORD:
        return [TextContent(type="text", text="[错误] 邮件服务未配置。")]

    if not _validate_email(to):
        return [TextContent(type="text", text=f"[错误] 收件人邮箱格式不正确: {to}")]

    if not subject or not body:
        return [TextContent(type="text", text="[错误] 邮件主题和正文不能为空。")]

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        smtp_server = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=10)
        smtp_server.login(EMAIL_USER, EMAIL_PASSWORD)
        smtp_server.sendmail(EMAIL_USER, [to], msg.as_string())
        smtp_server.quit()

        return [TextContent(type="text", text=f"[成功] 邮件已发送至 {to}，主题: {subject}")]

    except smtplib.SMTPAuthenticationError:
        return [TextContent(type="text", text="[错误] 邮箱登录失败，请检查 SMTP 授权码。")]
    except Exception as e:
        return [TextContent(type="text", text=f"[错误] 发送失败: {e}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
