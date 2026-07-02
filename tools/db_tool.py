"""
数据查询工具 —— 带 RBAC 权限控制
不同角色看到的数据范围不同：
  - admin：全校数据
  - teacher：本院系数据
  - student：仅自己的数据
  - guest：无权限
"""
import threading
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from database.sql_generator import gen_sql
from database.db import execute_sql


_thread_local = threading.local()

def set_db_user_context(role: str, user_id=None, student_id=None, display_name='用户'):
    """Set user context for the current thread - called by supervisor before invoking db_query"""
    _thread_local.db_role = role
    _thread_local.db_user_id = user_id
    _thread_local.db_student_id = student_id
    _thread_local.db_display_name = display_name

def _get_user_context(config: RunnableConfig | None) -> dict:
    """从 thread-local 或 config 中提取用户上下文"""
    # Priority: thread-local (set by supervisor) > config (set by LangChain)
    if hasattr(_thread_local, 'db_role'):
        return {
            "role": _thread_local.db_role,
            "user_id": _thread_local.db_user_id,
            "student_id": _thread_local.db_student_id,
            "display_name": _thread_local.db_display_name,
        }
    if config and "configurable" in config:
        return {
            "role": config["configurable"].get("user_role", "guest"),
            "user_id": config["configurable"].get("user_id"),
            "student_id": config["configurable"].get("student_id"),
            "display_name": config["configurable"].get("display_name", "用户"),
        }
    return {"role": "guest", "user_id": None, "student_id": None, "display_name": "游客"}


def _format_db_result(result: dict) -> str:
    """格式化查询结果"""
    if result.get("status") == "error":
        return f"[错误] {result.get('message', '未知错误')}"
    
    rows = result.get("rows", [])
    if not rows:
        return "[查询结果为空] 未找到匹配的记录。"
    
    lines = [f"查询到 {len(rows)} 条记录："]
    for i, row in enumerate(rows, 1):
        fields = [f"{k}: {v}" for k, v in row.items()]
        lines.append(f"{i}. " + " | ".join(fields))
    
    return "\n".join(lines)


@tool
def db_query(question: str, config: RunnableConfig = None) -> str:
    """
    通用数据库查询工具。可查询学生信息、成绩、课程、教师等数据。
    
    权限说明：
    - 游客(guest)：无数据库查询权限
    - 学生(student)：仅可查询自己的信息
    - 教师(teacher)：可查询本院系学生
    - 管理员(admin)：可查询全部数据
    
    参数:
        question: 自然语言描述的查询需求
    """
    user = _get_user_context(config)
    role = user["role"]
    
    # 权限检查
    if role == "guest":
        return "[权限不足] 游客无法查询数据库。请以学生/教师身份登录后重试。"
    
    # 学生只能查自己的数据：在问题中附加限制
    if role == "student" and user.get("student_id"):
        original_question = question
        # 智能注入身份限制
        if any(kw in question for kw in ["我", "我的", "自己的"]):
            question = question.replace("我", f"学号为 {user['student_id']} 的学生")
        elif not any(kw in question for kw in ["学号", "student_no"]):
            # 如果没指定具体学号，自动限制为查询者本人
            question = f"{question}（仅限学号为 {user['student_id']} 的学生）"
    
    sql = gen_sql(question)
    if not sql:
        return "[错误] 无法理解查询意图，请换一种方式描述。"
    
    result = execute_sql(sql)
    return _format_db_result(result)
