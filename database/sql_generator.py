"""
NL2SQL - natural language to SQL via ZhipuAI GLM
"""
from zhipuai import ZhipuAI
from config.settings import ZHIPUAI_API_KEY
from database.db import get_schema_description

client = ZhipuAI(api_key=ZHIPUAI_API_KEY)
_schema_cache = None

def _get_schema():
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = get_schema_description()
    return _schema_cache

def gen_sql(question):
    schema = _get_schema()
    sys = f"""You are a SQL generator. Generate ONLY a SELECT statement based on the user question and schema.

{schema}

Rules:
1. ONLY SELECT statements - no INSERT/UPDATE/DELETE/DROP
2. Return ONLY the raw SQL - no markdown, no ```, no explanation
3. Use student_name (not student_no) as the default search condition
4. Use JOIN to combine students+scores when needed
5. Always add LIMIT 50
6. Use MySQL 8.0 syntax
7. Student and course names may be in Chinese
"""
    try:
        resp = client.chat.completions.create(
            model="glm-4-plus",
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": question}
            ],
            temperature=0.1
        )
        sql = resp.choices[0].message.content
    except Exception as e:
        print(f"[sql_generator] LLM error: {e}")
        return None

    sql = sql.replace("```sql", "").replace("```", "").strip()
    import re
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE).strip()
    return sql if sql else None
