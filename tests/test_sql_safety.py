"""Tests: SQL Audit Safety - Zero external dependencies"""
import sys, re

# Inline CAMPUS_SCHEMA and audit_sql from database/db.py
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
        ]
    },
    "courses": {
        "description": "Courses",
        "columns": [
            ("course_id", "INT PK AUTO_INCREMENT", "Course ID"),
            ("course_name", "VARCHAR(100)", "Course"),
            ("teacher_name", "VARCHAR(50)", "Teacher"),
            ("credit", "DECIMAL(3,1)", "Credits"),
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
            return False, "Dangerous operation: {}".format(name)
    if not sql.strip().upper().startswith("SELECT"):
        return False, "Only SELECT allowed"
    tables = re.findall(r"\bFROM\s+(\w+)", sql, re.IGNORECASE)
    tables += re.findall(r"\bJOIN\s+(\w+)", sql, re.IGNORECASE)
    for tbl in tables:
        if tbl.lower() not in CAMPUS_SCHEMA:
            return False, "Table not allowed: {}".format(tbl)
    return True, "OK"


def test_select_allowed():
    ok, msg = audit_sql("SELECT * FROM students")
    assert ok, "Safe SELECT blocked: {}".format(msg)
    ok, msg = audit_sql("SELECT student_name FROM students WHERE student_name = 'Zhang San'")
    assert ok, "SELECT with WHERE blocked: {}".format(msg)
    ok, msg = audit_sql("SELECT s.student_name, c.course_name FROM students s JOIN courses c ON s.student_id = c.course_id")
    assert ok, "JOIN query blocked: {}".format(msg)

def test_insert_blocked():
    ok, msg = audit_sql("INSERT INTO students VALUES (1, 'test', 'test')")
    assert not ok, "INSERT should be blocked"

def test_delete_blocked():
    ok, msg = audit_sql("DELETE FROM students WHERE student_id = 1")
    assert not ok, "DELETE should be blocked"

def test_update_blocked():
    ok, msg = audit_sql("UPDATE students SET student_name = 'hacker' WHERE student_id = 1")
    assert not ok, "UPDATE should be blocked"

def test_drop_blocked():
    ok, msg = audit_sql("DROP TABLE students")
    assert not ok, "DROP should be blocked"

def test_truncate_blocked():
    ok, msg = audit_sql("TRUNCATE TABLE students")
    assert not ok, "TRUNCATE should be blocked"

def test_alter_blocked():
    ok, msg = audit_sql("ALTER TABLE students ADD COLUMN secret VARCHAR(100)")
    assert not ok, "ALTER should be blocked"

def test_create_blocked():
    ok, msg = audit_sql("CREATE TABLE hack (id INT)")
    assert not ok, "CREATE should be blocked"

def test_exec_blocked():
    ok, msg = audit_sql("EXEC('SELECT 1')")
    assert not ok, "EXEC should be blocked"

def test_unknown_table_blocked():
    ok, msg = audit_sql("SELECT * FROM users")
    assert not ok, "Unknown table should be blocked: {}".format(msg)

def test_case_insensitive_attack():
    ok, msg = audit_sql("DeLeTe FrOm students")
    assert not ok, "Case-insensitive DELETE not caught: {}".format(msg)

def test_known_tables_all_pass():
    for table_name in CAMPUS_SCHEMA:
        ok, msg = audit_sql("SELECT * FROM {} LIMIT 1".format(table_name))
        assert ok, "Valid table {} blocked: {}".format(table_name, msg)

def test_non_select_rejected():
    ok, msg = audit_sql("EXPLAIN SELECT * FROM students")
    assert not ok, "Non-SELECT should be blocked"


if __name__ == "__main__":
    all_tests = [f for f in dir() if f.startswith('test_')]
    passed = 0
    failed = 0
    for test_name in all_tests:
        try:
            globals()[test_name]()
            print("  PASS  {}".format(test_name))
            passed += 1
        except AssertionError as e:
            print("  FAIL  {}: {}".format(test_name, e))
            failed += 1
        except Exception as e:
            print("  ERROR {}: {}".format(test_name, e))
            failed += 1
    print("\n{} passed, {} failed out of {}".format(passed, failed, len(all_tests)))
    sys.exit(1 if failed else 0)
