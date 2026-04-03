from flask import Blueprint, render_template, session, redirect, request, flash, abort, url_for
import sqlite3
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash



bp = Blueprint('student', __name__,url_prefix="/student")

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

import sqlite3
from flask import g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('database.db')
        g.db.row_factory = sqlite3.Row
    return g.db

def login_required(f):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return wrapper


@bp.before_request
def require_login():
    open_routes = [
        "student.student_dashboard",
        "student.student_courses"
    ]

    # agar route ochiq bo‘lsa → tekshirmaymiz
    if request.endpoint in open_routes:
        return

    # qolganlari uchun login talab qilinadi
    if "user_id" not in session:
        return redirect(url_for('auth.login', next=request.path))



@bp.route('/dashboard')
def student_dashboard():
    db = get_db()

    # 🔹 1. Umumiy foydalanuvchilar soni
    users = db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]

    # 🔹 2. Kursga yozilganlar (unique userlar)
    enrolled = db.execute("""
        SELECT COUNT(DISTINCT user_id) FROM enrollments
    """).fetchone()[0]

    # 🔹 3. Sertifikat olganlar
    certified = db.execute("""
        SELECT COUNT(*) FROM certificates
    """).fetchone()[0]

    stats = {
        "users": users,
        "enrolled": enrolled,
        "certified": certified
    }

    return render_template(
        "student/dashboard.html",
        stats=stats
    )
    
    
    
@bp.route("/courses")
def student_courses():
    conn = get_db()
    c = conn.cursor()

    # Foydalanuvchi ID
    user_id = session.get("user_id")

    # Barcha kurslar va progress
    courses = c.execute("""
        SELECT 
            co.id,
            co.name,
            co.title,
            co.img,
            COUNT(t.id) as total_topics,
            SUM(CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END) as topics_done
        FROM courses co
        LEFT JOIN chapters ch ON ch.course_id = co.id
        LEFT JOIN topics t ON t.chapter_id = ch.id
        LEFT JOIN studies s ON s.topic_id = t.id AND s.user_id = ?
        GROUP BY co.id
    """, (user_id,)).fetchall()

    courses_list = []
    for course in courses:
        courses_list.append({
            "id": course[0],
            "name": course[1],
            "title": course[2],
            "img": course[3],
            "total_topics": course[4],
            "topics_done": course[5] or 0
        })

    conn.close()

    return render_template("student/courses.html", courses=courses_list)




@bp.route("/course/<int:course_id>")
def course_detail(course_id):

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    conn = get_db()
    c = conn.cursor()

    # -------- COURSE ----------
    c.execute("SELECT * FROM courses WHERE id=?", (course_id,))
    course = c.fetchone()

    if not course:
        conn.close()
        return "Course topilmadi"

    # -------- CHAPTERS ----------
    c.execute("""
        SELECT chapters.*, 
        (SELECT COUNT(*) FROM topics 
         WHERE topics.chapter_id = chapters.id) AS topic_count
        FROM chapters
        WHERE course_id=?
        ORDER BY number
    """, (course_id,))
    chapters = c.fetchall()

    # -------- ENROLLMENT CHECK ----------
    c.execute("""
        SELECT 1 FROM enrollments
        WHERE user_id=? AND course_id=?
        LIMIT 1
    """, (user_id, course_id))

    enrolled = True if c.fetchone() else False

    conn.close()

    return render_template(
        "student/course_detail.html",
        course=course,
        chapters=chapters,
        enrolled=enrolled
    )
    
    
@bp.route("/enroll/<int:course_id>")
def enroll_course(course_id):

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Kurs mavjudligini tekshirish
    c.execute("SELECT id FROM courses WHERE id=?", (course_id,))
    if not c.fetchone():
        conn.close()
        return "Course topilmadi"

    # Oldindan yozilganmi?
    c.execute("""
        SELECT id FROM enrollments
        WHERE user_id=? AND course_id=?
    """, (user_id, course_id))

    if not c.fetchone():
        # Yozib qo‘yamiz
        c.execute("""
            INSERT INTO enrollments (user_id, course_id)
            VALUES (?,?)
        """, (user_id, course_id))
        conn.commit()

    conn.close()

    # Qayta kurs sahifasiga yuboramiz
    return redirect(f"/student/course/{course_id}")
    
    

@bp.route('/continue/<int:course_id>')
def continue_course(course_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    # Kursdagi barcha topiclar (chapters va topics number bo'yicha)
    all_topics = c.execute("""
        SELECT t.id
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        WHERE ch.course_id=?
        ORDER BY ch.number, t.number
    """, (course_id,)).fetchall()
    all_topics = [t["id"] for t in all_topics]

    if not all_topics:
        return "Bu kursda mavzular mavjud emas"

    # Oxirgi o‘rganilgan mavzu
    last = c.execute("""
        SELECT topic_id FROM studies
        WHERE user_id=? AND topic_id IN ({seq})
        ORDER BY id DESC
        LIMIT 1
    """.format(seq=','.join('?'*len(all_topics))), [user_id]+all_topics).fetchone()

    if not last:
        # Hech narsa o‘rganilmagan bo‘lsa, birinchi topicga yo‘naltiramiz
        return redirect(url_for("student.topic", topic_id=all_topics[0]))

    last_id = last["topic_id"]

    # last_id all_topics ichida mavjudligini tekshirish
    if last_id in all_topics:
        idx = all_topics.index(last_id)
        # Keyingi topic
        next_topic = all_topics[idx + 1] if idx + 1 < len(all_topics) else all_topics[idx]
    else:
        # last_id hozirgi kursga tegishli emas → birinchi topicga yo‘naltiramiz
        next_topic = all_topics[0]

    return redirect(url_for("student.topic", topic_id=next_topic))







def get_all_topics(c,course_id):
    return c.execute("""
    SELECT topics.id
    FROM topics
    JOIN chapters ON topics.chapter_id=chapters.id
    WHERE chapters.course_id=?
    ORDER BY chapters.number, topics.number
    """,(course_id,)).fetchall()
    
    
    


@bp.route("/topic/<int:topic_id>")
def topic(topic_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    # Topicni olish
    topic = c.execute("""
        SELECT t.*, ch.course_id
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        WHERE t.id=?
    """, (topic_id,)).fetchone()
    if not topic:
        return "Bunday mavzu mavjud emas"

    course_id = topic["course_id"]

    # Kursdagi barcha topiclar
    all_topics = c.execute("""
        SELECT t.id
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        WHERE ch.course_id=?
        ORDER BY ch.number, t.number
    """, (course_id,)).fetchall()
    all_topics = [t["id"] for t in all_topics]

    # Avvalgi mavzu tugaganligini tekshirish
    index = all_topics.index(topic_id)
    if index > 0:
        prev_id = all_topics[index - 1]
        prev_status = c.execute("""
            SELECT value FROM studies
            WHERE user_id=? AND topic_id=?
        """, (user_id, prev_id)).fetchone()
        if not prev_status or prev_status["value"] != "succesfully":
            return redirect(url_for("student.topic", topic_id=prev_id-1 if prev_id-1 in all_topics else prev_id))

    # MAVZU OCHILDI → in_progress
    c.execute("""
        INSERT OR IGNORE INTO studies(user_id, topic_id, value)
        VALUES (?, ?, 'in_progress')
    """, (user_id, topic_id))
    conn.commit()

    # PDF lar
    pdfs = c.execute("SELECT * FROM pdfs WHERE topic_id=?", (topic_id,)).fetchall()

    # Sidebar chapters/topics
    chapters = c.execute("SELECT * FROM chapters WHERE course_id=? ORDER BY number", (course_id,)).fetchall()
    topics_dict = {}
    for ch in chapters:
        topics_dict[ch["id"]] = c.execute("SELECT * FROM topics WHERE chapter_id=? ORDER BY number", (ch["id"],)).fetchall()

    # Studies status
    studies = c.execute("SELECT topic_id, value FROM studies WHERE user_id=?", (user_id,)).fetchall()
    study_status = {s["topic_id"]: s["value"] for s in studies}

    # TEST
    test_id = topic["test_id"]
    questions = []
    answers = {}
    test = None
    test_result = None
    show_test = False

    if test_id:
        # Oxirgi test natijasi
        test_result = c.execute("""
            SELECT * FROM exams
            WHERE user_id=? AND test_id=?
            ORDER BY id DESC
            LIMIT 1
        """, (user_id, test_id)).fetchone()

        min_score_row = c.execute("SELECT min_score FROM tests WHERE id=?", (test_id,)).fetchone()
        min_score = min_score_row["min_score"] if min_score_row else 50

        # Testni ko‘rsatish sharti
        show_test = not test_result or test_result["score"] < min_score

        if show_test:
            # Savollarni olish va randomlashtirish
            all_questions = c.execute("SELECT * FROM questions WHERE test_id=?", (test_id,)).fetchall()
            all_questions = list(all_questions)
            import random
            random.shuffle(all_questions)
            questions = all_questions[:20] if len(all_questions) >= 20 else all_questions

            # Javoblar
            answers = {}
            for q in questions:
                ans = c.execute("SELECT * FROM answers WHERE question_id=?", (q["id"],)).fetchall()
                ans = list(ans)
                random.shuffle(ans)  # Javoblarni alohida randomlashtirish
                answers[q["id"]] = ans
            

            test = c.execute("SELECT * FROM tests WHERE id=?", (test_id,)).fetchone()



    last_topic = all_topics[-1]

    conn.close()

    return render_template(
        "student/topic.html",
        topic=topic,
        pdfs=pdfs,
        chapters=chapters,
        topics=topics_dict,
        study_status=study_status,
        questions=questions,
        answers=answers,
        test=test,
        test_result=test_result,
        show_test=show_test,
        last_topic=last_topic,
        course_id=course_id
    )








# Keyingi mavzu in_progress
def activate_next_topic(user_id, topic_id, all_topics):
    try:
        index = all_topics.index(topic_id)
        next_id = all_topics[index + 1]
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO studies(user_id, topic_id, value)
            VALUES (?, ?, ?)
        """, (user_id, next_id, "in_progress"))
        conn.commit()
        conn.close()
    except IndexError:
        # Oxirgi mavzu → keyingi mavzu yo'q
        pass





@bp.route("/submit_test/<int:test_id>", methods=["POST"])
def submit_test(test_id):
    user_id = session.get("user_id")
    topic_id = int(request.form.get("topic_id"))

    conn = get_db()
    c = conn.cursor()

    # Kursdagi barcha topiclar
    course_id = c.execute("""
        SELECT ch.course_id
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        WHERE t.id=?
    """, (topic_id,)).fetchone()["course_id"]

    all_topics = c.execute("""
        SELECT t.id
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        WHERE ch.course_id=?
        ORDER BY ch.number, t.number
    """, (course_id,)).fetchall()
    all_topics = [t["id"] for t in all_topics]

    # Savollar
    questions = c.execute("SELECT id FROM questions WHERE test_id=?", (test_id,)).fetchall()

    score = 0
    total = 0
    for q in questions:
        qid = q["id"]
        ans = request.form.get(str(qid))
        if not ans:
            continue
        correct = c.execute("SELECT is_correct FROM answers WHERE id=?", (ans,)).fetchone()
        if correct and correct["is_correct"] == 1:
            score += 1
        total += 1

    percent = int((score / total) * 100) if total else 0

    # Exam jadvaliga yozish
    c.execute("INSERT INTO exams(user_id, test_id, score) VALUES (?, ?, ?)", (user_id, test_id, percent))

    # Minimal ball
    min_score = c.execute("SELECT min_score FROM tests WHERE id=?", (test_id,)).fetchone()["min_score"]

    # Agar testdan o‘tsa → studies va keyingi mavzu
    if percent >= min_score:
        c.execute("UPDATE studies SET value='succesfully' WHERE user_id=? AND topic_id=?", (user_id, topic_id))
        # Keyingi mavzu
        try:
            idx = all_topics.index(topic_id)
            next_id = all_topics[idx + 1]
            c.execute("INSERT OR IGNORE INTO studies(user_id, topic_id, value) VALUES (?, ?, ?)", (user_id, next_id, "in_progress"))
        except IndexError:
            pass

    conn.commit()
    conn.close()
    return redirect(url_for("student.topic", topic_id=topic_id))



@bp.route("/finish_topic", methods=["POST"])
def finish_topic():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    topic_id = int(request.form.get("topic_id"))
    conn = get_db()
    c = conn.cursor()

    # Mavzuni tugallash
    c.execute("""
        INSERT OR IGNORE INTO studies(user_id, topic_id, value)
        VALUES (?, ?, 'in_progress')
    """, (user_id, topic_id))
    c.execute("UPDATE studies SET value='succesfully' WHERE user_id=? AND topic_id=?", (user_id, topic_id))

    # Keyingi mavzu
    course_id = c.execute("""
        SELECT ch.course_id
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        WHERE t.id=?
    """, (topic_id,)).fetchone()["course_id"]

    all_topics = c.execute("""
        SELECT t.id
        FROM topics t
        JOIN chapters ch ON t.chapter_id = ch.id
        WHERE ch.course_id=?
        ORDER BY ch.number, t.number
    """, (course_id,)).fetchall()
    all_topics = [t["id"] for t in all_topics]

    next_id = None
    try:
        idx = all_topics.index(topic_id)
        if idx + 1 < len(all_topics):
            next_id = all_topics[idx + 1]
            # Keyingi mavzuni in_progress holatiga keltirish
            c.execute("INSERT OR IGNORE INTO studies(user_id, topic_id, value) VALUES (?, ?, ?)", 
                      (user_id, next_id, "in_progress"))
    except ValueError:
        pass

    conn.commit()
    conn.close()

    # Agar next_id mavjud bo‘lsa, unga yo‘naltiramiz, aks holda hozirgi topicga
    return redirect(url_for("student.topic", topic_id=next_id if next_id else topic_id))










@bp.route("/finish_course",methods=["POST"])
def finish_course():

    user_id=session["user_id"]

    course_id=request.form.get("course_id")

    conn=sqlite3.connect("database.db")
    c=conn.cursor()


    c.execute("""

    INSERT OR IGNORE INTO certificates(user_id,course_id)

    VALUES(?,?)

    """,(user_id,course_id))


    conn.commit()


    return redirect("/student/dashboard")





@bp.route("/tests")
def tests():

    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    tests = cur.execute("""
        SELECT *
        FROM tests
        WHERE openness='open'
        ORDER BY id DESC
    """).fetchall()

    test_results = {}

    for t in tests:

        res = cur.execute("""
            SELECT *
            FROM exams
            WHERE user_id=? AND test_id=?
            ORDER BY id DESC
            LIMIT 1
        """,(user_id, t["id"])).fetchone()

        if res:
            test_results[t["id"]] = res

    return render_template(
        "student/tests.html",
        tests=tests,
        test_results=test_results
    )
    
    
@bp.route("/start_test/<int:test_id>", methods=["GET","POST"])
def start_test(test_id):

    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    test = cur.execute(
        "SELECT * FROM tests WHERE id=?",
        (test_id,)
    ).fetchone()

    questions = cur.execute(
        "SELECT * FROM questions WHERE test_id=?",
        (test_id,)
    ).fetchall()

    answers = {}

    for q in questions:

        ans = cur.execute(
            "SELECT * FROM answers WHERE question_id=?",
            (q["id"],)
        ).fetchall()

        ans = list(ans)
        random.shuffle(ans)

        answers[q["id"]] = ans


    if request.method == "POST":

        correct = 0

        for q in questions:

            user_answer = request.form.get(str(q["id"]))

            if user_answer:

                res = cur.execute("""
                    SELECT is_correct
                    FROM answers
                    WHERE id=? AND question_id=?
                """,(user_answer,q["id"])).fetchone()

                if res and res["is_correct"] == 1:
                    correct += 1

        total = len(questions)

        score = int((correct / total) * 100)

        cur.execute("""
            INSERT INTO exams(user_id,test_id,score)
            VALUES(?,?,?)
        """,(user_id,test_id,score))

        db.commit()

        return redirect(url_for("student.tests"))

    return render_template(
        "student/start_test.html",
        test=test,
        questions=questions,
        answers=answers
    )


@bp.route("/achievements")
def achievements():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # natijalarni dict kabi ishlatish uchun
    c = conn.cursor()

    # Sertifikatlar
    certificates = c.execute("""
        SELECT c.*, cr.name AS course_name
        FROM certificates c
        JOIN courses cr ON c.course_id = cr.id
        WHERE c.user_id=?
    """, (user_id,)).fetchall()

    # So‘nggi 7 kun davomiyligi va mavzular
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    recent_topics = c.execute("""
        SELECT t.id, t.name, t.time
        FROM studies s
        JOIN topics t ON s.topic_id=t.id
        WHERE s.user_id=? AND s.value='succesfully' AND s.date>=?
    """, (user_id, seven_days_ago)).fetchall()

    total_minutes = sum([t["time"] for t in recent_topics if t["time"]])
    total_topics = len(recent_topics)

    # Foydalanuvchi reytingi (jami yakunlangan vaqt bo‘yicha)
    all_users = c.execute("""
        SELECT s.user_id, SUM(t.time) AS total_time
        FROM studies s
        JOIN topics t ON s.topic_id=t.id
        WHERE s.value='succesfully'
        GROUP BY s.user_id
        ORDER BY total_time DESC
    """).fetchall()

    position = 1
    for idx, u in enumerate(all_users, 1):
        if u["user_id"] == user_id:
            position = idx
            break

    conn.close()

    return render_template(
        "student/achievements.html",
        certificates=certificates,
        total_topics=total_topics,
        total_minutes=total_minutes,
        position=position,
        recent_topics=recent_topics
    )
    
    

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn



@bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@bp.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        full_name = request.form.get("full_name")
        number = request.form.get("number")
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        user = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        
        # Parolni yangilash
        if old_password or new_password or confirm_password:
            if not check_password_hash(user["password"], old_password):
                flash("Eski parol noto‘g‘ri ❌")
            elif new_password != confirm_password:
                flash("Yangi parol va tasdiqlash mos emas ❌")
            else:
                hashed = generate_password_hash(new_password)
                c.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
                flash("Parol muvaffaqiyatli yangilandi ✅")

        # Ism va telefonni yangilash
        c.execute("UPDATE users SET full_name=?, number=? WHERE id=?", (full_name, number, user_id))
        conn.commit()
        flash("Profil yangilandi ✅")

    # Foydalanuvchi ma’lumotlari
    user = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    # Kurslar va ularning holati
    courses = c.execute("""
        SELECT cr.id, cr.name, cr.title,
               SUM(CASE WHEN s.value='succesfully' THEN 1 ELSE 0 END) AS completed,
               COUNT(t.id) AS total_topics
        FROM enrollments e
        JOIN courses cr ON e.course_id = cr.id
        LEFT JOIN chapters ch ON ch.course_id = cr.id
        LEFT JOIN topics t ON t.chapter_id = ch.id
        LEFT JOIN studies s ON s.topic_id = t.id AND s.user_id=?
        WHERE e.user_id=?
        GROUP BY cr.id
    """, (user_id, user_id)).fetchall()

    conn.close()
    return render_template("student/profile.html", user=user, courses=courses)




