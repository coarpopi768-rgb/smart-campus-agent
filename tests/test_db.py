from database.db import execute_sql

sql = "select * from students"
res = execute_sql(sql)
print(res)


