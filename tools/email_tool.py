import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool
from config.settings import *

@tool
def send_email(to,subject,body):
    """发送邮件"""
    msg = MIMEMultipart()

    msg["From"] = EMAIL_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain","utf-8"))

    server = smtplib.SMTP_SSL(
        "smtp.qq.com",
        465
    )
    server.login(
        EMAIL_USER,
        EMAIL_PASSWORD
    )
    server.sendmail(
        EMAIL_USER,
        [to],
        msg.as_string() 
    )

    server.quit()
    return "邮件发送成功"