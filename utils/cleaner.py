def clean_sql(sql):
    sql = sql.replace("```sql","")
    sql = sql.replace("```","")
    
    sql = sql.strip()
    return sql