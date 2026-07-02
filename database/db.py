"""
Database layer - connection, SQL audit, execution
"""
import re
from config.settings import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

CAMPUS_SCHEMA = {
    "students": {
        "description": "Student information",
        "columns": [
            ("student_id", "INT PK AUTO_INCREMENT", "Student ID"),
            ("student_no", "VARCHAR(20)", "Student Number"),
            ("student_name", "VARCHAR(50)", "Name"),
            ("gender", "VARCHAR(4)", "Gender M/F"),
            ("major", "VARCHAR(100)", "Major"),
            ("class_name", "VARCHAR(50)", "Class"),
            ("email", "VARCHAR(100)", "Email"),
            ("phone", "VARCHAR(20)", "Phone"),
            ("enrollment_year", "INT", "Year"),
        ]
    },
    "scores": {
        "description": "Exam scores",
        "columns": [
            ("score_id", "INT PK AUTO_INCREMENT", "Score ID"),
            ("student_id", "INT FK->students", "Student ID"),
            ("course_name", "VARCHAR(100)", "Course"),
            ("score", "DECIMAL(5,2)", "Score"),
            ("semester", "VARCHAR(20)", "Semester"),
            ("exam_time", "DATE", "Exam Date"),
        ]
    },
    "courses": {
        "description": "Courses",
        "columns": [
            ("course_id", "INT PK AUTO_INCREMENT", "Course ID"),
            ("course_name", "VARCHAR(100)", "Course"),
            ("teacher_name", "VARCHAR(50)", "Teacher"),
            ("credit", "DECIMAL(3,1)", "Credits"),
            ("semester", "VARCHAR(20)", "Semester"),
            ("classroom", "VARCHAR(50)", "Classroom"),
            ("schedule", "VARCHAR(100)", "Schedule"),
        ]
    },
    "teachers": {
        "description": "Faculty",
        "columns": [
            ("teacher_id", "INT PK AUTO_INCREMENT", "Teacher ID"),
            ("teacher_name", "VARCHAR(50)", "Name"),
            ("department", "VARCHAR(100)", "Department"),
            ("title", "VARCHAR(50)", "Title"),
            ("email", "VARCHAR(100)", "Email"),
        ]
    },
}

def get_schema_description():
    lines = ["Database tables:"]
    for t, info in CAMPUS_SCHEMA.items():
        lines.append(f"\n### {t} - {info['description']}")
        lines.append("| Column | Type | Description |")
        lines.append("|--------|------|-------------|")
        for col, typ, desc in info["columns"]:
            lines.append(f"| {col} | {typ} | {desc} |")
    return "\n".join(lines)

DANGER_PATTERNS = [
    (r"\bdrop\b\s+\w+", "DROP"),
    (r"\btruncate\b", "TRUNCATE"),
    (r"\bdelete\b\s+from\b", "DELETE"),
    (r"\binsert\b\s+into\b", "INSERT"),
    (r"\bupdate\b\s+\w+\s+set\b", "UPDATE"),
    (r"\balter\b\s+\w+", "ALTER"),
    (r"\bcreate\b\s+\w+", "CREATE"),
    (r"\bexec\b\s*\(", "EXEC"),
]

def audit_sql(sql):
    for pattern, name in DANGER_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"Dangerous operation: {name}"
    if not sql.strip().upper().startswith("SELECT"):
        return False, "Only SELECT allowed"
    tables = re.findall(r"\bFROM\s+(\w+)", sql, re.IGNORECASE)
    tables += re.findall(r"\bJOIN\s+(\w+)", sql, re.IGNORECASE)
    for tbl in tables:
        if tbl.lower() not in CAMPUS_SCHEMA:
            return False, f"Table not allowed: {tbl}"
    return True, "OK"

_pymysql = None

def _get_pymysql():
    global _pymysql
    if _pymysql is None:
        import pymysql as _pm
        _pymysql = _pm
    return _pymysql


def get_conn():
    conn = _get_pymysql().connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, db=MYSQL_DB,
        charset="utf8mb4", use_unicode=True, autocommit=False
    )
    # 确保连接编码正确，防止中文乱码
    with conn.cursor() as cur:
        cur.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
    return conn

def execute_sql(sql, params=None):
    ok, reason = audit_sql(sql)
    if not ok:
        return {"status": "error", "message": f"SQL audit failed: {reason}"}
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return {
            "status": "success",
            "columns": cols,
            "rows": [dict(zip(cols, r)) for r in rows],
            "row_count": len(rows)
        }
    except _get_pymysql().Error as e:
        return {"status": "error", "message": f"DB error: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"{e}"}
    finally:
        if conn:
            conn.close()