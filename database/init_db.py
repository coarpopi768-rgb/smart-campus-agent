"""
Database initializer - create tables and seed data
Usage: python database/init_db.py
"""

import pymysql
from config.settings import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB


cfg = {
    "host": MYSQL_HOST,
    "port": MYSQL_PORT,
    "user": MYSQL_USER,
    "password": MYSQL_PASSWORD,
    "charset": "utf8mb4",
    "autocommit": True,
}

db = MYSQL_DB

# Step 1: Create database
c = pymysql.connect(**cfg)
c.cursor().execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
c.close()
cfg["db"] = db

# Step 2: Drop tables in correct order (child first)
conn = pymysql.connect(**cfg)
cur = conn.cursor()
for t in ["scores", "courses", "teachers", "students"]:
    cur.execute(f"DROP TABLE IF EXISTS `{t}`")
conn.commit()

# Step 3: Create tables
ddl = [
    """CREATE TABLE students (
        student_id INT AUTO_INCREMENT PRIMARY KEY,
        student_no VARCHAR(20) UNIQUE NOT NULL,
        student_name VARCHAR(50) NOT NULL,
        gender VARCHAR(4),
        major VARCHAR(100),
        class_name VARCHAR(50),
        email VARCHAR(100),
        phone VARCHAR(20),
        enrollment_year INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE scores (
        score_id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        course_name VARCHAR(100) NOT NULL,
        score DECIMAL(5,2),
        semester VARCHAR(20),
        exam_time DATE,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE courses (
        course_id INT AUTO_INCREMENT PRIMARY KEY,
        course_name VARCHAR(100) NOT NULL,
        teacher_name VARCHAR(50),
        credit DECIMAL(3,1),
        semester VARCHAR(20),
        classroom VARCHAR(50),
        schedule VARCHAR(100)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE teachers (
        teacher_id INT AUTO_INCREMENT PRIMARY KEY,
        teacher_name VARCHAR(50) NOT NULL,
        department VARCHAR(100),
        title VARCHAR(50),
        email VARCHAR(100)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]

for stmt in ddl:
    try:
        cur.execute(stmt)
    except pymysql.Error as e:
        print(f"[SKIP] {str(e)[:80]}")

conn.commit()

# Step 4: Insert seed data
data = [
    # students
    ("INSERT INTO students VALUES (1,'2024001','张三','M','计算机科学与技术','CS2401','zhangsan@campus.edu.cn','13800001001',2024)", []),
    ("INSERT INTO students VALUES (2,'2024002','李四','F','计算机科学与技术','CS2401','lisi@campus.edu.cn','13800001002',2024)", []),
    ("INSERT INTO students VALUES (3,'2024003','王五','M','软件工程','SE2401','wangwu@campus.edu.cn','13800001003',2024)", []),
    ("INSERT INTO students VALUES (4,'2024004','赵六','F','数据科学','DS2401','zhaoliu@campus.edu.cn','13800001004',2024)", []),
    ("INSERT INTO students VALUES (5,'2024005','孙七','M','人工智能','AI2401','sunqi@campus.edu.cn','13800001005',2024)", []),
    ("INSERT INTO students VALUES (6,'2024006','周八','F','计算机科学与技术','CS2402','zhouba@campus.edu.cn','13800001006',2024)", []),
    ("INSERT INTO students VALUES (7,'2024007','吴九','M','软件工程','SE2402','wujiu@campus.edu.cn','13800001007',2024)", []),
    ("INSERT INTO students VALUES (8,'2024008','郑十','F','人工智能','AI2401','zhengshi@campus.edu.cn','13800001008',2024)", []),
    # scores
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (1,'高等数学',92,'2024-2025-1','2025-01-10')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (1,'大学英语',88,'2024-2025-1','2025-01-12')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (1,'Python程序设计',95,'2024-2025-1','2025-01-15')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (1,'数据结构',85,'2024-2025-1','2025-01-08')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (2,'高等数学',78,'2024-2025-1','2025-01-10')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (2,'大学英语',82,'2024-2025-1','2025-01-12')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (2,'Python程序设计',90,'2024-2025-1','2025-01-15')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (2,'数据结构',91,'2024-2025-1','2025-01-08')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (3,'高等数学',65,'2024-2025-1','2025-01-10')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (3,'Java程序设计',88,'2024-2025-1','2025-01-15')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (4,'高等数学',94,'2024-2025-1','2025-01-10')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (4,'Python程序设计',97,'2024-2025-1','2025-01-15')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (5,'高等数学',76,'2024-2025-1','2025-01-10')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (5,'人工智能导论',91,'2024-2025-1','2025-01-17')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (8,'人工智能导论',95,'2024-2025-1','2025-01-17')", []),
    ("INSERT INTO scores (student_id, course_name, score, semester, exam_time) VALUES (8,'计算机网络',92,'2024-2025-1','2025-01-19')", []),
    # courses
    ("INSERT INTO courses VALUES (1,'高等数学','刘教授',5.0,'2024-2025-1','教学楼301','周一/周三 8:00-10:00')", []),
    ("INSERT INTO courses VALUES (2,'大学英语','陈老师',4.0,'2024-2025-1','教学楼302','周二/周四 10:00-12:00')", []),
    ("INSERT INTO courses VALUES (3,'Python程序设计','王老师',3.0,'2024-2025-1','实验楼201','周一/周三 14:00-16:00')", []),
    ("INSERT INTO courses VALUES (4,'数据结构','张教授',4.0,'2024-2025-1','教学楼101','周二/周四 8:00-10:00')", []),
    ("INSERT INTO courses VALUES (5,'操作系统','李教授',3.0,'2024-2025-1','教学楼301','周五 14:00-16:00')", []),
    ("INSERT INTO courses VALUES (6,'计算机网络','孙老师',3.0,'2024-2025-1','教学楼302','周三 16:00-18:00')", []),
    ("INSERT INTO courses VALUES (7,'Java程序设计','周老师',3.0,'2024-2025-1','实验楼202','周二/周四 14:00-16:00')", []),
    # teachers
    ("INSERT INTO teachers VALUES (1,'刘教授','计算机科学与技术系','教授','liu@campus.edu.cn')", []),
    ("INSERT INTO teachers VALUES (2,'陈老师','计算机科学与技术系','副教授','chen@campus.edu.cn')", []),
    ("INSERT INTO teachers VALUES (3,'王老师','数学与统计学院','讲师','wang@campus.edu.cn')", []),
    ("INSERT INTO teachers VALUES (4,'张教授','计算机学院','教授','zhang@campus.edu.cn')", []),
    ("INSERT INTO teachers VALUES (5,'孙老师','网络空间安全','讲师','sun@campus.edu.cn')", []),
    ("INSERT INTO teachers VALUES (6,'周老师','网络空间安全','讲师','zhou@campus.edu.cn')", []),
    ("INSERT INTO teachers VALUES (7,'李教授','数学学院','教授','li@campus.edu.cn')", []),
]

for sql_text, params in data:
    try:
        cur.execute(sql_text, params)
    except pymysql.Error as e:
        print(f"[WARN] {str(e)[:100]}")

conn.commit()

# Step 5: Verify
for t in ["students", "scores", "courses", "teachers"]:
    cur.execute(f"SELECT COUNT(*) FROM `{t}`")
    print(f"[OK] {t}: {cur.fetchone()[0]} rows")

conn.close()
print("[DONE]")