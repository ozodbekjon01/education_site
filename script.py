import sqlite3
import re

DB_NAME = "database.db"
TXT_FILE = "data.txt"

conn = sqlite3.connect(DB_NAME)
c = conn.cursor()


# ----------------------------
# 1. Test yaratish (agar kerak bo'lsa)
# ----------------------------
test_name = "10-test"
test_title = "TXT import"
time_limit = 60
min_score = 60

c.execute("""
INSERT INTO tests (name, title, time, min_score, openness)
VALUES (?, ?, ?, ?, ?)
""", (test_name, test_title, time_limit, min_score, "open"))

test_id = c.lastrowid


# ----------------------------
# 2. TXT o'qish
# ----------------------------
with open(TXT_FILE, "r", encoding="utf-8") as f:
    content = f.read()


# ----------------------------
# 3. Savollarni ajratish
# ----------------------------
pattern = r"\d+\.\s*(.*?)\nA\)\s*(.*?)\nB\)\s*(.*?)\nC\)\s*(.*?)\nD\)\s*(.*?)\nJavob:\s*([ABCD])"

matches = re.findall(pattern, content, re.S)


# ----------------------------
# 4. Bazaga yozish
# ----------------------------
for q_text, a, b, c_ans, d, correct in matches:

    # question insert
    c.execute("""
    INSERT INTO questions (text, test_id)
    VALUES (?, ?)
    """, (q_text.strip(), test_id))

    question_id = c.lastrowid

    answers = [
        ("A", a),
        ("B", b),
        ("C", c_ans),
        ("D", d)
    ]

    for key, text in answers:
        is_correct = 1 if key == correct else 0

        c.execute("""
        INSERT INTO answers (text, question_id, is_correct)
        VALUES (?, ?, ?)
        """, (text.strip(), question_id, is_correct))


conn.commit()
conn.close()

print("✅ Ma'lumotlar muvaffaqiyatli import qilindi!")