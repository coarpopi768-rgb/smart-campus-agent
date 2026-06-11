import json
import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from config.settings import *
from dotenv import load_dotenv

load_dotenv()
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

def gen_sql(question):
    sys_prompt = """
    你是一个SQL生成器,只返回纯SQL语句,不要加任何其他文字、符号、注释、标签
    绝对禁止输出 </arg_value> 这类标签！
    表:
    students:
    student_id,student_name,student_no,gender,major,class_name,email,phone
    scores:
    score_id,student_id,course_name,score,semester,exam_time
    规则:
    1. 查询成绩必须使用 JSON student 和 score
    2. 用 student_name 作为查询条件
    3. 支持 AVG,COUNT 等聚合函数
    4. 支持MySQL的增删改查操作(INSERT,DELETE,UPDATE,SELECT)
    5. MySQL的版本是 8
    """
    response = client.chat.completions.create(
        model = "glm-4-plus",
        messages = [
            {"role":"system","content":sys_prompt},
            {"role":"user","content":question}
        ]
    )
    try:
        sql = response.choices[0].message.content
    except (IndexError, AttributeError) as e:
        print(f"Error parsing response: {e}")
        return  None

    sql = sql.replace("```sql","")
    sql = sql.replace("```","")
    sql = sql.strip()

    return sql