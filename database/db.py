import pymysql
from config.settings import *

def get_conn():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        db="oa_demo",
        charset="utf8mb4"
    )
def execute_sql(sql:str,params=None):

    #sql安全限制
    danger_words = ["drop","truncate"]

    for word in danger_words:
        if word in sql.lower():
            raise ValueError(f"SQL语句中包含危险关键词: {word}")
    
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(sql,params or ())

    if sql.strip().lower().startswith("select"):
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        result = []
        result.append("|".join(cols))
        result.append("-"*50)
        for row in rows:
            result.append("|".join(str(x) for x in row))
        cursor.close()
        conn.close()
        return "\n".join(result)
    else:
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        return f"操作成功,影响 {affected} 行"