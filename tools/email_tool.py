"""
邮件发送工具 —— 带 RBAC 权限控制
仅 teacher 和 admin 角色可以发送邮件

用户角色由 Supervisor 通过工具入参 user_role 显式传递，不使用 thread-local，避免并发串号。
"""
import smtplib, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool
from config.settings import EMAIL_USER, EMAIL_PASSWORD


def _validate_email(email: str) -> bool:
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))


@tool
def send_email(to: str, subject: str, body: str, user_role: str = "guest") -> str:
    """
    发送邮件通知。仅教师和管理员可发送邮件。

    参数:
        to: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文
        user_role: 调用方注入的用户角色（admin/teacher/student/guest），由 Supervisor 传入
    """
    # 权限检查 - 角色来自调用方显式注入的入参
    role = user_role or "guest"

    if role not in ("admin", "teacher"):
        return f"[权限不足] 当前角色({role})没有发送邮件的权限。仅教师和管理员可发送邮件。"

    if not EMAIL_USER or not EMAIL_PASSWORD:
        return "[错误] 邮件服务未配置。"

    if not _validate_email(to):
        return f"[错误] 收件人邮箱格式不正确: {to}"

    if not subject.strip() or not body.strip():
        return "[错误] 邮件主题和正文不能为空。"

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        server = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=10)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, [to], msg.as_string())
        server.quit()

        return f"[成功] 邮件已发送至 {to}，主题: {subject}"

    except smtplib.SMTPAuthenticationError:
        return "[错误] 邮箱登录失败，请检查 SMTP 授权码。"
    except Exception as e:
        return f"[错误] 发送失败: {str(e)}"
