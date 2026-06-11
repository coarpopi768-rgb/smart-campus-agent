from langchain_core.tools import tool

from database.sql_generator import gen_sql
from database.db import execute_sql

@tool
def score_query(question:str):
    """查询成绩"""
    sql = gen_sql(question)
    result = execute_sql(sql)
    return result
    