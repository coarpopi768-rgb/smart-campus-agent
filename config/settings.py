from dotenv import load_dotenv
import os
load_dotenv()

#数据库
MYSQL_HOST = os.getenv("mysql_host")
MYSQL_PORT = int(os.getenv("mysql_port"))
MYSQL_USER = os.getenv("mysql_user")
MYSQL_PASSWORD = os.getenv("mysql_password")
MYSQL_DB = os.getenv("mysql_db")

#智谱ai
ZHIPUAI_API_KEY = os.getenv("zhipuai_api_key")

#邮箱
EMAIL_USER = os.getenv("email_user")
EMAIL_PASSWORD = os.getenv("email_password")



