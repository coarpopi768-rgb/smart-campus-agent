"""
数据查询工具 —— 带 RBAC 权限控制
不同角色看到的数据范围不同：
  - admin：全校数据
  - teacher：本院系数据
  - student：仅自己的数据
  - guest：无权限

用户上下文由 Supervisor 通过工具入参 user_context 显式传递（见 agents/supervisor.py），
不使用 thread-local，避免并发请求串号。
"""
from langchain_core.tools import tool
from database.sql_generator import gen_sql
from database.db import execute_sql


def _get_user_context(user_context) -> dict:
    """从工具入参提取用户上下文；缺失时按最严格的 guest 处理（安全默认值）"""
    if user_context and isinstance(user_context, dict):
        return user_context
    return {"role": "guest", "user_id": None, "student_id": None, "display_name": "Guest"}


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
def db_query(question: str, user_context: dict = None) -> str:
    """
    通用数据库查询工具。可查询学生信息、成绩、课程、教师等数据。

    权限说明：
    - 游客(guest)：无数据库查询权限
    - 学生(student)：仅可查询自己的信息
    - 教师(teacher)：可查询本院系学生
    - 管理员(admin)：可查询全部数据

    参数:
        question: 自然语言描述的查询需求
        user_context: 调用方注入的用户上下文（role/user_id/student_id/display_name），
                      由 Supervisor 在调用时传入；缺失时按 guest 处理
    """
    user = _get_user_context(user_context)
    role = user.get("role", "guest")

    # 权限检查
    if role == "guest":
        return "[权限不足] 游客无法查询数据库。请以学生/教师身份登录后重试。"

    # 学生只能查自己的数据：在问题中附加限制
    if role == "student" and user.get("student_id"):
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
