import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('database.db')
conn.execute("PRAGMA foreign_keys = ON")   # ✅ TO‘G‘RI JOY
c = conn.cursor()

# ================= USERS =================
c.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    number TEXT,
    role TEXT NOT NULL DEFAULT 'student',
    date TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# ================= COURSES =================
c.execute("""
CREATE TABLE IF NOT EXISTS courses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    title TEXT NOT NULL,
    img TEXT
)
""")

# ================= ENROLLMENTS =================
c.execute("""
CREATE TABLE IF NOT EXISTS enrollments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    value TEXT,
    UNIQUE(user_id, course_id),
    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,
    FOREIGN KEY(course_id)
        REFERENCES courses(id)
        ON DELETE CASCADE
)
""")

# ================= CERTIFICATES =================
c.execute("""
CREATE TABLE IF NOT EXISTS certificates(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    date TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, course_id),
    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,
    FOREIGN KEY(course_id)
        REFERENCES courses(id)
        ON DELETE CASCADE
)
""")

# ================= CHAPTERS =================
c.execute("""
CREATE TABLE IF NOT EXISTS chapters(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    title TEXT,
    number INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    UNIQUE(number, course_id),
    FOREIGN KEY(course_id)
        REFERENCES courses(id)
        ON DELETE CASCADE
)
""")

# ================= TOPICS =================
c.execute("""
CREATE TABLE IF NOT EXISTS topics(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    video TEXT,
    content TEXT,
    time INTEGER,
    number INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    UNIQUE(number, chapter_id),
    FOREIGN KEY(chapter_id)
        REFERENCES chapters(id)
        ON DELETE CASCADE
)
""")

# ================= PDFS =================
c.execute("""
CREATE TABLE IF NOT EXISTS pdfs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pdf TEXT NOT NULL,
    topic_id INTEGER NOT NULL,
    FOREIGN KEY(topic_id)
        REFERENCES topics(id)
        ON DELETE CASCADE
)
""")

# ================= STUDIES =================
c.execute("""
CREATE TABLE IF NOT EXISTS studies(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    value TEXT,
    UNIQUE(user_id, topic_id),
    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,
    FOREIGN KEY(topic_id)
        REFERENCES topics(id)
        ON DELETE CASCADE
)
""")

# ================= TEST SYSTEM =================
c.execute("""
CREATE TABLE IF NOT EXISTS tests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    title TEXT,
    time INTEGER NOT NULL,
    min_score INTEGER NOT NULL,
    openness TEXT DEFAULT 'open'
)
""")
#---------------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS questions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    test_id INTEGER NOT NULL,
    FOREIGN KEY(test_id)
        REFERENCES tests(id)
        ON DELETE CASCADE
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS answers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    is_correct INTEGER DEFAULT 0,
    FOREIGN KEY(question_id)
        REFERENCES questions(id)
        ON DELETE CASCADE
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS exams(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,
    score INTEGER,
    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,
    FOREIGN KEY(test_id)
        REFERENCES tests(id)
        ON DELETE CASCADE
)
""")


c.execute("""
CREATE TABLE IF NOT EXISTS forum_posts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
)
""")

c.execute(""" create table if not exists forum_comments(
    id integer primary key autoincrement,
    user_id integer not null,
    post_id integer not null,
    content text not null,
    created_at text default current_timestamp,
    foreign key(user_id) references users(id) on delete cascade,
    foreign key(post_id) references forum_posts(id) on delete cascade
)""")


c.execute("""
CREATE TABLE IF NOT EXISTS resources(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    file TEXT NOT NULL
)
""")



# ================= INDEXES (PERFORMANCE) =================
c.execute("CREATE INDEX IF NOT EXISTS idx_chapter_course ON chapters(course_id)")
c.execute("CREATE INDEX IF NOT EXISTS idx_topic_chapter ON topics(chapter_id)")
c.execute("CREATE INDEX IF NOT EXISTS idx_question_test ON questions(test_id)")
c.execute("CREATE INDEX IF NOT EXISTS idx_answer_question ON answers(question_id)")

# ================= DEFAULT ADMIN =================
# login = "admin"
# password = "2006..eerr"
# hashed = generate_password_hash(password)

# try:
#     c.execute("""
#         INSERT INTO users (login,password,full_name,role)
#         VALUES (?,?,?,?)
#     """, (login, hashed, "Administrator", "admin"))
# except:
#     pass

# conn.commit()
# conn.close()





# import sqlite3

# conn = sqlite3.connect("database.db")
# c = conn.cursor()

# # topics jadvaliga test nomli yangi ustun qo'shish
# try:
#     c.execute("ALTER TABLE topics ADD COLUMN test_id TEXT")
#     print("Ustun muvaffaqiyatli qo‘shildi ✅")
# except sqlite3.OperationalError as e:
#     print("Xato:", e)

# conn.commit()
# conn.close()


# import sqlite3

# conn = sqlite3.connect('database.db')
# c = conn.cursor()

# try:
#     c.execute("ALTER TABLE studies ADD COLUMN date TEXT DEFAULT CURRENT_TIMESTAMP")
#     print("Ustun muvaffaqiyatli qo‘shildi ✅")
# except sqlite3.OperationalError as e:
#     print("Xato:", e)

# conn.commit()
# conn.close()


# conn = sqlite3.connect('database.db')
# c = conn.cursor()
# c.execute("UPDATE studies SET date = CURRENT_TIMESTAMP WHERE date IS NULL")
# conn.commit()
# conn.close()







import sqlite3
from datetime import datetime, timedelta

# DB bilan ulanish
conn = sqlite3.connect('database.db')
c = conn.cursor()

# UTC -> UTC+5 qo‘shish funksiyasi
def add_utc5(value):
    if value is None:
        return datetime.utcnow() + timedelta(hours=5)
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S") + timedelta(hours=5)

# 1️⃣ USERS jadvali
c.execute("ALTER TABLE users RENAME TO old_users")
c.execute("""
CREATE TABLE users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    number TEXT,
    role TEXT NOT NULL DEFAULT 'student',
    date TEXT DEFAULT (DATETIME('now', '+5 hours'))
)
""")
# ma’lumotlarni ko‘chirish
c.execute("SELECT * FROM old_users")
rows = c.fetchall()
for r in rows:
    id, login, password, full_name, number, role, date = r
    c.execute("INSERT INTO users (id,login,password,full_name,number,role,date) VALUES (?,?,?,?,?,?,?)",
              (id, login, password, full_name, number, role, (add_utc5(date).strftime("%Y-%m-%d %H:%M:%S"))))
c.execute("DROP TABLE old_users")


# 2️⃣ CERTIFICATES jadvali
c.execute("ALTER TABLE certificates RENAME TO old_certificates")
c.execute("""
CREATE TABLE certificates(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    date TEXT DEFAULT (DATETIME('now', '+5 hours')),
    UNIQUE(user_id, course_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
)
""")
c.execute("SELECT * FROM old_certificates")
rows = c.fetchall()
for r in rows:
    id, user_id, course_id, date = r
    c.execute("INSERT INTO certificates (id,user_id,course_id,date) VALUES (?,?,?,?)",
              (id,user_id,course_id,(add_utc5(date).strftime("%Y-%m-%d %H:%M:%S"))))
c.execute("DROP TABLE old_certificates")


# 3️⃣ FORUM POSTS jadvali
c.execute("ALTER TABLE forum_posts RENAME TO old_forum_posts")
c.execute("""
CREATE TABLE forum_posts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (DATETIME('now', '+5 hours')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
""")
c.execute("SELECT * FROM old_forum_posts")
rows = c.fetchall()
for r in rows:
    id, user_id, title, content, created_at = r
    c.execute("INSERT INTO forum_posts (id,user_id,title,content,created_at) VALUES (?,?,?,?,?)",
              (id,user_id,title,content,(add_utc5(created_at).strftime("%Y-%m-%d %H:%M:%S"))))
c.execute("DROP TABLE old_forum_posts")


# 4️⃣ FORUM COMMENTS jadvali
c.execute("ALTER TABLE forum_comments RENAME TO old_forum_comments")
c.execute("""
CREATE TABLE forum_comments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (DATETIME('now', '+5 hours')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(post_id) REFERENCES forum_posts(id) ON DELETE CASCADE
)
""")
c.execute("SELECT * FROM old_forum_comments")
rows = c.fetchall()
for r in rows:
    id, user_id, post_id, content, created_at = r
    c.execute("INSERT INTO forum_comments (id,user_id,post_id,content,created_at) VALUES (?,?,?,?,?)",
              (id,user_id,post_id,content,(add_utc5(created_at).strftime("%Y-%m-%d %H:%M:%S"))))
c.execute("DROP TABLE old_forum_comments")


# 5️⃣ STUDIES jadvali
c.execute("ALTER TABLE studies RENAME TO old_studies")
c.execute("""
CREATE TABLE studies(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    value TEXT,
    date TEXT DEFAULT (DATETIME('now', '+5 hours')),
    UNIQUE(user_id, topic_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE
)
""")
c.execute("SELECT * FROM old_studies")
rows = c.fetchall()
for r in rows:
    id, user_id, topic_id, value, *rest = r
    # rest may include date if exists
    old_date = rest[0] if rest else None
    c.execute("INSERT INTO studies (id,user_id,topic_id,value,date) VALUES (?,?,?,?,?)",
              (id,user_id,topic_id,value,(add_utc5(old_date).strftime("%Y-%m-%d %H:%M:%S"))))
c.execute("DROP TABLE old_studies")


# commit va close
conn.commit()
conn.close()

print("Barcha jadvallar UTC+5 bilan yangilandi ✅")