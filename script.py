import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime
import random

conn = sqlite3.connect("database.db")
c = conn.cursor()

# ================== USERS ==================
print("Users qo'shilmoqda...")

admin_password = generate_password_hash("admin123")

c.execute("""
INSERT OR IGNORE INTO users (login, password, full_name, number, role, date)
VALUES (?, ?, ?, ?, ?, ?)
""", (
    "admin",
    admin_password,
    "Admin User",
    "998900000000",
    "admin",
    datetime.now().strftime("%Y-%m-%d")
))

students = [
    ("ali", "Ali Valiyev"),
    ("vali", "Vali Aliyev"),
    ("sardor", "Sardor Karimov"),
    ("malika", "Malika Xasanova"),
    ("jamshid", "Jamshid Rahimov"),
]

for login, fullname in students:
    c.execute("""
    INSERT OR IGNORE INTO users (login, password, full_name, number, role, date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        login,
        generate_password_hash("123456"),
        fullname,
        "998901234567",
        "student",
        datetime.now().strftime("%Y-%m-%d")
    ))

# ================== COURSES ==================
print("Courses qo'shilmoqda...")

courses = [
    ("python", "Python Dasturlash", "python.jpg"),
    ("flask", "Flask Web Dasturlash", "flask.jpg"),
]

for name, title, img in courses:
    c.execute("""
    INSERT INTO courses (name, title, img)
    VALUES (?, ?, ?)
    """, (name, title, img))

# ================== CHAPTERS ==================
print("Chapters qo'shilmoqda...")

c.execute("SELECT id FROM courses")
course_ids = c.fetchall()

chapter_id_list = []

for course in course_ids:
    for i in range(1, 3):
        c.execute("""
        INSERT INTO chapters (name, title, number, course_id)
        VALUES (?, ?, ?, ?)
        """, (
            f"chapter{i}",
            f"Bo'lim {i}",
            i,
            course[0]
        ))
        chapter_id_list.append(c.lastrowid)

# ================== TOPICS ==================
print("Topics qo'shilmoqda...")

for chapter_id in chapter_id_list:
    for i in range(1, 3):
        c.execute("""
        INSERT INTO topics (name, video, content, time, number, chapter_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"topic{i}",
            "video.mp4",
            "Bu test mavzusi uchun namunaviy matn.",
            10,
            i,
            chapter_id
        ))

# ================== TEST ==================
print("Test qo'shilmoqda...")

c.execute("""
INSERT INTO tests (name, title, time, min_score, openness)
VALUES (?, ?, ?, ?, ?)
""", (
    "python_test",
    "Python Asoslari Testi",
    20,
    60,
    "open"
))

test_id = c.lastrowid

# ================== QUESTIONS + ANSWERS ==================

questions = [
    "Python qaysi turdagi til?",
    "Flask nima?",
    "print() funksiyasi nima qiladi?"
]

for q in questions:
    c.execute("""
    INSERT INTO questions (text, test_id)
    VALUES (?, ?)
    """, (q, test_id))

    question_id = c.lastrowid

    answers = [
        ("Interpretatorli til", 1),
        ("Kompilyatorli til", 0),
        ("Operatsion tizim", 0),
    ]

    for text, correct in answers:
        c.execute("""
        INSERT INTO answers (text, question_id, is_correct)
        VALUES (?, ?, ?)
        """, (text, question_id, correct))

# ================== ENROLLMENTS ==================

print("Enrollments qo'shilmoqda...")

c.execute("SELECT id FROM users WHERE role='student'")
student_ids = c.fetchall()

c.execute("SELECT id FROM courses")
course_ids = c.fetchall()

for student in student_ids:
    for course in course_ids:
        c.execute("""
        INSERT INTO enrollments (user_id, course_id, value)
        VALUES (?, ?, ?)
        """, (student[0], course[0], "active"))

# ================== EXAMS ==================

print("Exam natijalari qo'shilmoqda...")

for student in student_ids:
    c.execute("""
    INSERT INTO exams (user_id, test_id, score)
    VALUES (?, ?, ?)
    """, (student[0], test_id, random.randint(50, 100)))

# ================== CERTIFICATES ==================

print("Certificates qo'shilmoqda...")

for student in student_ids[:3]:
    c.execute("""
    INSERT INTO certificates (user_id, course_id, date)
    VALUES (?, ?, ?)
    """, (
        student[0],
        course_ids[0][0],
        datetime.now().strftime("%Y-%m-%d")
    ))

conn.commit()
conn.close()

print("Barcha namunaviy ma'lumotlar muvaffaqiyatli qo'shildi!")