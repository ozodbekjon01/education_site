from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, send_file
import sqlite3
import math
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from werkzeug.utils import secure_filename

import io


bp = Blueprint("admin", __name__, url_prefix="/admin")


# ================= DATABASE HELPER =================

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    conn = sqlite3.connect("database.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ================= ADMIN DECORATOR =================


# ================= DASHBOARD =================
@bp.route("/dashboard")
@admin_required
def dashboard():
    conn = get_db()
    c = conn.cursor()

    # Umumiy statistika
    students = c.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    courses = c.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    tests = c.execute("SELECT COUNT(*) FROM tests").fetchone()[0]

    # Faol o‘quvchilar (oxirgi 7 kun)
    active_students_rows = c.execute("""
        SELECT u.id, u.full_name, u.login
        FROM users u
        JOIN studies s ON u.id = s.user_id
        WHERE u.role='student' AND s.date >= date('now','-7 days')
        GROUP BY u.id
        ORDER BY MAX(s.date) DESC
        LIMIT 50
    """).fetchall()
    active_students_count = len(active_students_rows)

    # Kurslar bo‘yicha o‘rtacha progress
    total_topics = c.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
    avg_progress = 0
    if total_topics > 0 and students > 0:
        learned_topics = c.execute("SELECT COUNT(*) FROM studies WHERE value='succesfully'").fetchone()[0]
        avg_progress = round(learned_topics / (total_topics * students) * 100, 1)

    # Testlar bo‘yicha o‘rtacha ball
    avg_test_score = c.execute("SELECT AVG(score) FROM exams").fetchone()[0] or 0
    avg_test_score = round(avg_test_score, 1)

    conn.close()

    return render_template(
        "admin/dashboard.html",
        students=students,
        courses=courses,
        tests=tests,
        active_students_count=active_students_count,
        active_students=active_students_rows,
        avg_progress=avg_progress,
        avg_test_score=avg_test_score
    )

# ================= CERTIFICATE TEKSHIRISH =================
@bp.route("/dashboard/certificate_check", methods=["POST"])
@admin_required
def dashboard_certificate_check():
    certificate_id = request.form.get("certificate_id")
    
    conn = get_db()
    c = conn.cursor()

    # Umumiy statistika (shunchaki qayta ishlatish)
    students_count = c.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    courses_count = c.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    tests_count = c.execute("SELECT COUNT(*) FROM tests").fetchone()[0]

    # Faol o‘quvchilar (oxirgi 7 kun)
    active_students_rows = c.execute("""
        SELECT u.id, u.full_name, u.login
        FROM users u
        JOIN studies s ON u.id = s.user_id
        WHERE u.role='student' AND s.date >= date('now','-7 days')
        GROUP BY u.id
        ORDER BY MAX(s.date) DESC
        LIMIT 50
    """).fetchall()
    active_students_count = len(active_students_rows)

    # Kurslar bo‘yicha o‘rtacha progress
    total_topics = c.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
    avg_progress = 0
    if total_topics > 0 and students_count > 0:
        learned_topics = c.execute("SELECT COUNT(*) FROM studies WHERE value='succesfully'").fetchone()[0]
        avg_progress = round(learned_topics / (total_topics * students_count) * 100, 1)

    # Testlar bo‘yicha o‘rtacha ball
    avg_test_score = c.execute("SELECT AVG(score) FROM exams").fetchone()[0] or 0
    avg_test_score = round(avg_test_score, 1)

    # Sertifikat ma'lumotlari
    certificate = c.execute("""
        SELECT cert.id, u.full_name, u.login, c.name, cert.date
        FROM certificates cert
        JOIN users u ON cert.user_id = u.id
        JOIN courses c ON cert.course_id = c.id
        WHERE cert.id = ?
    """, (certificate_id,)).fetchone()

    conn.close()

    return render_template(
        "admin/dashboard.html",
        students=students_count,
        courses=courses_count,
        tests=tests_count,
        active_students_count=active_students_count,
        active_students=active_students_rows,
        avg_progress=avg_progress,
        avg_test_score=avg_test_score,
        certificate_info=certificate if certificate else None,
        certificate_error=None if certificate else "Sertifikat topilmadi ❌"
    )    
    
# ================= COURSES LIST =================
@bp.route("/courses")
@admin_required
def courses():

    conn = get_db()
    c = conn.cursor()

    search = request.args.get("search", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 30
    offset = (page - 1) * per_page

    # ---------------------------
    # SEARCH BOR HOLAT
    # ---------------------------
    if search:
        courses = c.execute("""
            SELECT courses.id,
                   courses.name,
                   courses.title,
                   courses.img,
                   COUNT(enrollments.id) as student_count
            FROM courses
            LEFT JOIN enrollments
                ON courses.id = enrollments.course_id
            WHERE courses.title LIKE ?
            GROUP BY courses.id
            LIMIT ? OFFSET ?
        """, (f"%{search}%", per_page, offset)).fetchall()

        total = c.execute("""
            SELECT COUNT(*)
            FROM courses
            WHERE title LIKE ?
        """, (f"%{search}%",)).fetchone()[0]

    # ---------------------------
    # SEARCH YO‘Q HOLAT
    # ---------------------------
    else:
        courses = c.execute("""
            SELECT courses.id,
                   courses.name,
                   courses.title,
                   courses.img,
                   COUNT(enrollments.id) as student_count
            FROM courses
            LEFT JOIN enrollments
                ON courses.id = enrollments.course_id
            GROUP BY courses.id
            LIMIT ? OFFSET ?
        """, (per_page, offset)).fetchall()

        total = c.execute(
            "SELECT COUNT(*) FROM courses"
        ).fetchone()[0]

    conn.close()

    total_pages = math.ceil(total / per_page)

    return render_template(
        "admin/courses.html",
        courses=courses,
        page=page,
        total_pages=total_pages,
        search=search
    )
    
    
@bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@admin_required
def delete_course(course_id):
    conn = get_db()
    c = conn.cursor()

    # Kurs mavjudligini tekshirish
    course = c.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        flash("Kurs topilmadi ❌", "error")
        conn.close()
        return redirect(url_for("admin.courses_list"))

    # Kursni o'chirish (cascade bilan bog'liq yozuvlar ham o'chadi)
    c.execute("DELETE FROM courses WHERE id=?", (course_id,))
    conn.commit()
    conn.close()

    flash(f"Kurs '{course[1]}' muvaffaqiyatli o‘chirildi ✅", "success")  # course[1] = name
    return redirect(url_for("admin.courses"))

# ================= ADD COURSE =================

import os
from flask import current_app

@bp.route("/courses/add", methods=["GET", "POST"])
@admin_required
def add_course():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        title = request.form.get("title", "").strip()
        img_file = request.files.get("img")  # faylni olamiz

        if not name or not title:
            return "Name va Title majburiy", 400

        conn = get_db()
        # dastlab rasm maydonini bo‘sh qoldirib kursni qo‘shamiz
        cursor = conn.execute(
            "INSERT INTO courses (name, title, img) VALUES (?, ?, ?)",
            (name, title, "")  # img maydoni hozircha bo‘sh
        )
        course_id = cursor.lastrowid  # yangi kurs id sini olamiz
        conn.commit()

        # Agar rasm yuklangan bo‘lsa, saqlaymiz
        if img_file and img_file.filename != "":
            filename = f"{course_id}.png"  # rasmni course_id bilan nomlaymiz, .png default
            save_path = os.path.join(current_app.root_path, "static/icons", filename)
            img_file.save(save_path)

            # bazada img maydonini yangilaymiz
            conn.execute(
                "UPDATE courses SET img=? WHERE id=?",
                (filename, course_id)
            )
            conn.commit()

        conn.close()
        return redirect(url_for("admin.courses"))

    return render_template("admin/add_course.html")


# ================= EDIT COURSE =================

@bp.route('/courses/<int:id>/edit', methods=["GET","POST"])
@admin_required
def edit_course(id):
    conn = get_db()
    c = conn.cursor()

    course = c.execute("SELECT * FROM courses WHERE id = ?", (id,)).fetchone()
    if not course:
        conn.close()
        abort(404)

    # ================= POST =================
    if request.method == "POST":
        course_name = request.form.get("course_name")
        course_title = request.form.get("course_title")
        img_file = request.files.get("course_img")

        old_img = course[3]  # eski rasm nomi

        # Agar yangi rasm yuklangan bo‘lsa
        if img_file and img_file.filename != "":
            # Fayl kengaytmasini olish (.png, .jpg ...)
            ext = os.path.splitext(img_file.filename)[1]
            filename = f"{id}{ext}"

            save_path = os.path.join(current_app.root_path, "static/icons", filename)

            # Eski rasmni o‘chirish (agar mavjud bo‘lsa)
            if old_img:
                old_path = os.path.join(current_app.root_path, "static/icons", old_img)
                if os.path.exists(old_path):
                    os.remove(old_path)

            # Yangi rasmni saqlash
            img_file.save(save_path)

            # Baza yangilash
            c.execute("""
                UPDATE courses
                SET name = ?, title = ?, img = ?
                WHERE id = ?
            """, (course_name, course_title, filename, id))
        else:
            # Rasm o‘zgarmagan bo‘lsa
            c.execute("""
                UPDATE courses
                SET name = ?, title = ?
                WHERE id = ?
            """, (course_name, course_title, id))

        conn.commit()
        flash("Kurs ma'lumotlari saqlandi ✅", "success")
        conn.close()
        return redirect(f"/admin/courses/{id}/edit")

    # ================= GET =================
    chapters = c.execute("SELECT * FROM chapters WHERE course_id = ?", (id,)).fetchall()

    course = list(course)
    new_chapters = []
    for ch in chapters:
        ch = list(ch)
        topics = c.execute("SELECT * FROM topics WHERE chapter_id = ?", (ch[0],)).fetchall()
        ch.append(list(topics))
        new_chapters.append(ch)
    course.append(new_chapters)

    conn.close()
    return render_template('admin/course_edit.html', course=course)




UPLOAD_FOLDER = "static/pdfs"

@bp.route('/courses/<int:course_id>/<int:chapter_id>/topicadd', methods=["GET","POST"])
@admin_required
def topic_add(course_id, chapter_id):

    conn = get_db()
    c = conn.cursor()

    chapter = c.execute(
        "SELECT * FROM chapters WHERE id=? AND course_id=?",
        (chapter_id, course_id)
    ).fetchone()

    if not chapter:
        conn.close()
        abort(404)

    tests = c.execute("SELECT id,name FROM tests").fetchall()

    if request.method == "POST":

        topic_name = request.form.get("topic_name")
        topic_video = request.form.get("topic_video")
        topic_content = request.form.get("topic_content")
        topic_time = request.form.get("topic_time")
        test_id = request.form.get("test_id") or None

        last_topic = c.execute(
            "SELECT MAX(number) FROM topics WHERE chapter_id=?",
            (chapter_id,)
        ).fetchone()[0]

        topic_number = (last_topic or 0) + 1

        # topic qo'shish
        c.execute("""
            INSERT INTO topics (name, video, content, time, number, chapter_id, test_id)
            VALUES (?,?,?,?,?,?,?)
        """,(topic_name,topic_video,topic_content,topic_time,topic_number,chapter_id,test_id))

        topic_id = c.lastrowid

        # papka yo'q bo'lsa yaratish
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # barcha PDFlarni olish
        pdf_files = request.files.getlist("topic_pdf[]")

        for pdf in pdf_files:

            if pdf and pdf.filename != "":

                filename = secure_filename(pdf.filename)

                filepath = os.path.join(UPLOAD_FOLDER, filename)

                pdf.save(filepath)

                c.execute(
                    "INSERT INTO pdfs (pdf,topic_id) VALUES (?,?)",
                    (filepath, topic_id)
                )

        conn.commit()
        conn.close()

        flash("Mavzu va PDFlar qo‘shildi ✅","success")

        return redirect(f"/admin/courses/{course_id}/edit")

    conn.close()

    return render_template(
        "admin/topic_add.html",
        course_id=course_id,
        chapter_id=chapter_id,
        chapter=chapter,
        tests=tests
    )


import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "static/pdfs"

@bp.route('/courses/<int:course_id>/<int:chapter_id>/<int:topic_id>/edit', methods=["GET","POST"])
@admin_required
def topic_edit(course_id, chapter_id, topic_id):

    conn = get_db()
    c = conn.cursor()

    chapter = c.execute(
        "SELECT * FROM chapters WHERE id=? AND course_id=?",
        (chapter_id, course_id)
    ).fetchone()

    topic = c.execute(
        "SELECT * FROM topics WHERE id=? AND chapter_id=?",
        (topic_id, chapter_id)
    ).fetchone()

    if not chapter or not topic:
        conn.close()
        abort(404)

    tests = c.execute("SELECT id,name FROM tests").fetchall()

    # MAVJUD PDFLAR
    pdfs = c.execute(
        "SELECT * FROM pdfs WHERE topic_id=?",
        (topic_id,)
    ).fetchall()

    if request.method == "POST":

        topic_name = request.form.get("topic_name")
        topic_video = request.form.get("topic_video")
        topic_content = request.form.get("topic_content")
        topic_time = request.form.get("topic_time")
        topic_number = request.form.get("topic_number")
        test_id = request.form.get("test_id") or None

        c.execute("""
            UPDATE topics
            SET name=?, video=?, content=?, time=?, number=?, test_id=?
            WHERE id=? AND chapter_id=?
        """,(topic_name,topic_video,topic_content,topic_time,topic_number,test_id,topic_id,chapter_id))

        # YANGI PDFLAR
        pdf_files = request.files.getlist("topic_pdf[]")

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        for pdf in pdf_files:

            if pdf and pdf.filename != "":

                filename = secure_filename(pdf.filename)

                filepath = os.path.join(UPLOAD_FOLDER, filename)

                pdf.save(filepath)

                c.execute(
                    "INSERT INTO pdfs (pdf,topic_id) VALUES (?,?)",
                    (filepath, topic_id)
                )

        conn.commit()
        conn.close()

        flash("Mavzu tahrirlandi ✅","success")

        return redirect(f"/admin/courses/{course_id}/edit")

    conn.close()

    return render_template(
        "admin/topic_edit.html",
        course_id=course_id,
        chapter_id=chapter_id,
        topic=topic,
        chapter=chapter,
        tests=tests,
        pdfs=pdfs
    )


@bp.route('/pdf/<int:pdf_id>/delete')
@admin_required
def delete_pdf(pdf_id):

    conn = get_db()
    c = conn.cursor()

    pdf = c.execute("SELECT * FROM pdfs WHERE id=?", (pdf_id,)).fetchone()

    if pdf:

        try:
            os.remove(pdf[1])
        except:
            pass

        c.execute("DELETE FROM pdfs WHERE id=?", (pdf_id,))
        conn.commit()

    conn.close()

    flash("PDF o‘chirildi","success")

    return redirect(request.referrer)



@bp.route('/courses/<int:course_id>/<int:chapter_id>/<int:topic_id>/delete', methods=["POST","GET"])
@admin_required
def topic_delete(course_id, chapter_id, topic_id):
    conn = get_db()
    c = conn.cursor()

    # Mavzu mavjudligini tekshirish
    topic = c.execute("SELECT * FROM topics WHERE id=? AND chapter_id=?", (topic_id, chapter_id)).fetchone()
    if not topic:
        conn.close()
        abort(404, description="Mavzu topilmadi")

    # O'chirish
    c.execute("DELETE FROM topics WHERE id=? AND chapter_id=?", (topic_id, chapter_id))
    conn.commit()
    conn.close()
    flash("Mavzu o‘chirildi ✅", "success")
    return redirect(f"/admin/courses/{course_id}/edit")




@bp.route("/courses/<int:course_id>/addchapter", methods=["GET", "POST"])
@admin_required
def add_chapter(course_id):

    conn = get_db()
    c = conn.cursor()

    # Kurs mavjudligini tekshiramiz
    course = c.execute(
        "SELECT * FROM courses WHERE id = ?",
        (course_id,)
    ).fetchone()

    if not course:
        conn.close()
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        title = request.form.get("title", "").strip()
        number = request.form.get("number", "").strip()

        if not name or not number:
            flash("Bo‘lim nomi va tartib raqami majburiy!", "danger")
            return redirect(request.url)

        try:
            c.execute("""
                INSERT INTO chapters (name, title, number, course_id)
                VALUES (?, ?, ?, ?)
            """, (name, title, int(number), course_id))

            conn.commit()
            flash("Bo‘lim muvaffaqiyatli qo‘shildi ✅", "success")

            return redirect(f"/admin/courses/{course_id}/edit")

        except sqlite3.IntegrityError:
            flash("Bu tartib raqam allaqachon mavjud!", "danger")

    conn.close()
    return render_template(
        "admin/add_chapter.html",
        course=course
    )



@bp.route("/admin/courses/<int:course_id>/followers")
@admin_required
def course_followers(course_id):
    conn = get_db()
    c = conn.cursor()

    # Kurs nomini olish
    course = c.execute("SELECT name FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        flash("Kurs topilmadi ❌", "danger")
        return redirect("/admin/courses")

    # Qidiruv va pagination parametrlari
    search_query = request.args.get("search", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    # SQL tayyorlash
    base_sql = """
        SELECT u.id, u.full_name, u.login, u.number
        FROM enrollments e
        JOIN users u ON e.user_id = u.id
        WHERE e.course_id = ?
    """
    params = [course_id]

    if search_query:
        base_sql += " AND (u.full_name LIKE ? OR u.login LIKE ? OR u.number LIKE ?)"
        like_query = f"%{search_query}%"
        params.extend([like_query, like_query, like_query])

    # Jami yozuvlar soni
    total = c.execute(f"SELECT COUNT(*) FROM ({base_sql})", params).fetchone()[0]

    # O‘quvchilarni olish
    base_sql += " ORDER BY u.full_name LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    followers = c.execute(base_sql, params).fetchall()

    total_pages = (total + per_page - 1) // per_page

    conn.close()

    return render_template(
        "admin/course_followers.html",
        course_name=course[0],
        followers=followers,
        course_id=course_id,
        search_query=search_query,
        page=page,
        total_pages=total_pages
    )





@bp.route("/courses/<int:course_id>/editchapter/<int:chapter_id>", methods=["GET", "POST"])
@admin_required
def edit_chapter(course_id, chapter_id):

    conn = get_db()
    c = conn.cursor()

    # Chapter mavjudligini tekshiramiz
    chapter = c.execute("""
        SELECT * FROM chapters
        WHERE id = ? AND course_id = ?
    """, (chapter_id, course_id)).fetchone()

    if not chapter:
        conn.close()
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        title = request.form.get("title", "").strip()
        number = request.form.get("number", "").strip()

        if not name or not number:
            flash("Bo‘lim nomi va tartib raqami majburiy!", "danger")
            return redirect(request.url)

        try:
            c.execute("""
                UPDATE chapters
                SET name = ?, title = ?, number = ?
                WHERE id = ? AND course_id = ?
            """, (name, title, int(number), chapter_id, course_id))

            conn.commit()
            flash("Bo‘lim muvaffaqiyatli yangilandi ✅", "success")

            return redirect(f"/admin/courses/{course_id}/edit")

        except sqlite3.IntegrityError:
            flash("Bu tartib raqam allaqachon mavjud!", "danger")

    conn.close()
    return render_template(
        "admin/edit_chapter.html",
        chapter=chapter,
        course_id=course_id
    )


@bp.route("/courses/<int:course_id>/deletechapter/<int:chapter_id>")
@admin_required
def delete_chapter(course_id, chapter_id):

    conn = get_db()
    c = conn.cursor()

    # Chapter shu kursga tegishlimi tekshiramiz
    chapter = c.execute("""
        SELECT id FROM chapters
        WHERE id = ? AND course_id = ?
    """, (chapter_id, course_id)).fetchone()

    if not chapter:
        conn.close()
        abort(404)

    c.execute("""
        DELETE FROM chapters
        WHERE id = ? AND course_id = ?
    """, (chapter_id, course_id))

    conn.commit()
    conn.close()

    flash("Bo‘lim muvaffaqiyatli o‘chirildi 🗑", "success")

    return redirect(f"/admin/courses/{course_id}/edit")


# ================= TESTS =================

@bp.route("/tests")
@admin_required
def tests():

    conn = get_db()
    c = conn.cursor()

    search = request.args.get("search", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    base_query = """
        SELECT 
            t.*,
            (SELECT COUNT(*) FROM questions q WHERE q.test_id = t.id) as question_count,
            (SELECT COUNT(*) FROM exams e WHERE e.test_id = t.id) as attempt_count
        FROM tests t
    """

    if search:
        base_query += " WHERE t.name LIKE ? OR t.title LIKE ?"
        params = (f"%{search}%", f"%{search}%")
        tests = c.execute(
            base_query + " LIMIT ? OFFSET ?",
            (*params, per_page, offset)
        ).fetchall()

        total = c.execute(
            "SELECT COUNT(*) FROM tests WHERE name LIKE ? OR title LIKE ?",
            params
        ).fetchone()[0]
    else:
        tests = c.execute(
            base_query + " LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()

        total = c.execute("SELECT COUNT(*) FROM tests").fetchone()[0]

    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "admin/tests.html",
        tests=tests,
        page=page,
        total_pages=total_pages,
        search=search
    )
    

@bp.route("/tests/<int:test_id>/attempts")
@admin_required
def test_attempts(test_id):

    conn = get_db()
    c = conn.cursor()

    # Test mavjudligini tekshirish
    test = c.execute("SELECT * FROM tests WHERE id = ?", (test_id,)).fetchone()
    if not test:
        conn.close()
        abort(404)

    # Har bir user bo‘yicha statistika
    attempts = c.execute("""
        SELECT 
            u.id,
            u.full_name,
            u.login,
            COUNT(e.id) as total_attempts,
            MAX(e.score) as max_score
        FROM exams e
        JOIN users u ON u.id = e.user_id
        WHERE e.test_id = ?
        GROUP BY u.id
        ORDER BY max_score DESC
    """, (test_id,)).fetchall()

    conn.close()

    return render_template(
        "admin/test_attempts.html",
        attempts=attempts,
        test=test
    )



@bp.route("/tests/<int:test_id>/delete")
@admin_required
def delete_test(test_id):

    conn = get_db()
    c = conn.cursor()

    # Test mavjudligini tekshirish
    test = c.execute("SELECT id FROM tests WHERE id = ?", (test_id,)).fetchone()
    if not test:
        conn.close()
        abort(404)

    # O‘chirish
    c.execute("DELETE FROM tests WHERE id = ?", (test_id,))
    conn.commit()
    conn.close()

    flash("Test o‘chirildi ✅", "success")
    return redirect("/admin/tests")


    
@bp.route("/tests/add", methods=["GET", "POST"])
@admin_required
def add_test():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        title = request.form.get("title", "").strip()
        time = request.form.get("time", "").strip()
        min_score = request.form.get("min_score", "").strip()
        openness = request.form.get("openness", "open")

        # Validatsiya
        if not name or not time or not min_score:
            flash("Majburiy maydonlar to‘ldirilmagan", "danger")
            return redirect("/admin/tests/add")

        try:
            time = int(time)
            min_score = int(min_score)
        except:
            flash("Vaqt va Min score son bo‘lishi kerak", "danger")
            return redirect("/admin/tests/add")

        conn = get_db()
        conn.execute("""
            INSERT INTO tests (name, title, time, min_score, openness)
            VALUES (?, ?, ?, ?, ?)
        """, (name, title, time, min_score, openness))
        conn.commit()
        conn.close()

        flash("Test qo‘shildi ✅", "success")
        return redirect("/admin/tests")

    return render_template("admin/test_add.html")


@bp.route("/tests/<int:test_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_test(test_id):

    conn = get_db()
    c = conn.cursor()

    test = c.execute(
        "SELECT * FROM tests WHERE id = ?",
        (test_id,)
    ).fetchone()

    if not test:
        conn.close()
        abort(404)

    # ================= POST =================
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        title = request.form.get("title", "").strip()
        time = request.form.get("time", "").strip()
        min_score = request.form.get("min_score", "").strip()
        openness = request.form.get("openness", "open")

        if not name or not time or not min_score:
            flash("Majburiy maydonlar to‘ldirilmagan", "danger")
            return redirect(f"/admin/tests/{test_id}/edit")

        try:
            time = int(time)
            min_score = int(min_score)
        except:
            flash("Vaqt va Min score son bo‘lishi kerak", "danger")
            return redirect(f"/admin/tests/{test_id}/edit")

        c.execute("""
            UPDATE tests
            SET name = ?, title = ?, time = ?, min_score = ?, openness = ?
            WHERE id = ?
        """, (name, title, time, min_score, openness, test_id))

        conn.commit()
        conn.close()

        flash("Test yangilandi ✅", "success")
        return redirect("/admin/tests")

    conn.close()
    return render_template("admin/test_edit.html", test=test)


@bp.route("/tests/<int:test_id>/questions")
@admin_required
def manage_test_questions(test_id):

    conn = get_db()
    c = conn.cursor()

    test = c.execute(
        "SELECT * FROM tests WHERE id = ?",
        (test_id,)
    ).fetchone()

    if not test:
        conn.close()
        abort(404)

    questions = c.execute("""
        SELECT * FROM questions
        WHERE test_id = ?
        ORDER BY id ASC
    """, (test_id,)).fetchall()

    # Har bir savolga variantlarni biriktiramiz
    question_list = []
    for q in questions:
        q = list(q)
        answers = c.execute("""
            SELECT * FROM answers
            WHERE question_id = ?
        """, (q[0],)).fetchall()
        q.append(list(answers))
        question_list.append(q)

    conn.close()

    return render_template(
        "admin/test_questions.html",
        test=test,
        questions=question_list
    )


@bp.route("/questions/<int:question_id>/answers/add", methods=["GET", "POST"])
@admin_required
def add_answer(question_id):

    conn = get_db()
    c = conn.cursor()

    question = c.execute(
        "SELECT * FROM questions WHERE id = ?",
        (question_id,)
    ).fetchone()

    if not question:
        conn.close()
        abort(404)

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        is_correct = 1 if request.form.get("is_correct") else 0

        if not text:
            flash("Variant matni bo‘sh bo‘lishi mumkin emas", "danger")
            return redirect(f"/admin/questions/{question_id}/answers/add")

        # Agar bu variant to‘g‘ri bo‘lsa, avval boshqalarni 0 qilamiz
        if is_correct == 1:
            c.execute("""
                UPDATE answers
                SET is_correct = 0
                WHERE question_id = ?
            """, (question_id,))

        c.execute("""
            INSERT INTO answers (text, question_id, is_correct)
            VALUES (?, ?, ?)
        """, (text, question_id, is_correct))

        conn.commit()
        conn.close()

        flash("Variant qo‘shildi ✅", "success")

        # Orqaga savollar sahifasiga qaytamiz
        return redirect(f"/admin/tests/{question[2]}/questions")

    conn.close()
    return render_template(
        "admin/answer_add.html",
        question=question
    )


@bp.route("/answers/<int:answer_id>/edit", methods=["GET","POST"])
@admin_required
def edit_answer(answer_id):
    conn = get_db()
    c = conn.cursor()

    # Javobni olish
    answer = c.execute(
        "SELECT * FROM answers WHERE id = ?",
        (answer_id,)
    ).fetchone()
    if not answer:
        conn.close()
        abort(404)

    # Savolni olish
    question = c.execute(
        "SELECT * FROM questions WHERE id = ?",
        (answer[2],)
    ).fetchone()
    if not question:
        conn.close()
        abort(404)

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        is_correct = 1 if request.form.get("is_correct") else 0

        if not text:
            flash("Variant matni bo‘sh bo‘lishi mumkin emas", "danger")
            return redirect(f"/admin/answers/{answer_id}/edit")

        # Agar bu javob to‘g‘ri bo‘lsa, avval boshqa javoblarni 0 qilamiz
        if is_correct == 1:
            c.execute("""
                UPDATE answers
                SET is_correct = 0
                WHERE question_id = ?
            """, (answer[2],))

        # Javobni yangilash
        c.execute("""
            UPDATE answers
            SET text = ?, is_correct = ?
            WHERE id = ?
        """, (text, is_correct, answer_id))

        conn.commit()
        conn.close()

        flash("Variant yangilandi ✅", "success")
        return redirect(f"/admin/tests/{question[2]}/questions")

    conn.close()
    return render_template(
        "admin/answer_edit.html",
        answer=answer,
        question=question
    )
    


@bp.route("/answers/<int:answer_id>/delete", methods=["POST","GET"])
@admin_required
def delete_answer(answer_id):
    conn = get_db()
    c = conn.cursor()

    # Javobni olish
    answer = c.execute("SELECT * FROM answers WHERE id = ?", (answer_id,)).fetchone()
    if not answer:
        conn.close()
        abort(404)

    # Savolni olish (ortga qaytish uchun)
    question = c.execute("SELECT * FROM questions WHERE id = ?", (answer[2],)).fetchone()
    if not question:
        conn.close()
        abort(404)

    # Javobni o'chirish
    c.execute("DELETE FROM answers WHERE id = ?", (answer_id,))
    conn.commit()
    conn.close()

    flash("Variant muvaffaqiyatli o‘chirildi ✅", "success")
    return redirect(f"/admin/tests/{question[2]}/questions")


@bp.route("/questions/<int:question_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_question(question_id):
    conn = get_db()
    c = conn.cursor()

    # Savolni olish
    question = c.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    if not question:
        conn.close()
        abort(404)

    # POST bo'lsa: savolni yangilash
    if request.method == "POST":
        text = request.form.get("question_text", "").strip()
        if not text:
            flash("Savol matni bo‘sh bo‘lishi mumkin emas!", "danger")
        else:
            c.execute("UPDATE questions SET text = ? WHERE id = ?", (text, question_id))
            conn.commit()
            flash("Savol muvaffaqiyatli yangilandi ✅", "success")
            return redirect(f"/admin/questions/{question_id}/edit")

    # Variantlarni olish
    answers = c.execute("SELECT * FROM answers WHERE question_id = ?", (question_id,)).fetchall()
    conn.close()

    return render_template(
        "admin/question_edit.html",
        question=question,
        answers=answers
    )


@bp.route("/questions/<int:question_id>/delete", methods=["POST", "GET"])
@admin_required
def delete_question(question_id):
    conn = get_db()
    c = conn.cursor()

    # Savol borligini tekshirish
    question = c.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    if not question:
        conn.close()
        abort(404)

    # Savolga bog‘liq variantlarni o‘chirish (CASCADE ishlasa bu qadam shart emas)
    # c.execute("DELETE FROM answers WHERE question_id = ?", (question_id,))

    # Savolni o‘chirish
    c.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()

    flash("Savol va unga bog‘liq variantlar o‘chirildi ❌", "success")

    # Test tahrirlash sahifasiga qaytish
    return redirect(f"/admin/tests/{question[2]}/questions")



@bp.route("/tests/<int:test_id>/questions/add", methods=["GET","POST"])
@admin_required
def add_question_with_answers(test_id):
    conn = get_db()
    c = conn.cursor()

    # Test mavjudligini tekshirish
    test = c.execute("SELECT * FROM tests WHERE id = ?", (test_id,)).fetchone()
    if not test:
        conn.close()
        abort(404)

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        answers = request.form.getlist("answers[]")  # List sifatida barcha variantlar
        correct_index = request.form.get("correct")  # To'g'ri javob indeksi

        if not text or not answers:
            flash("Savol va variantlar majburiy ❌", "danger")
            return redirect(f"/admin/tests/{test_id}/questions/add")

        # Savol qo‘shish
        c.execute("INSERT INTO questions (text, test_id) VALUES (?, ?)", (text, test_id))
        question_id = c.lastrowid

        # Variantlarni qo‘shish
        for idx, ans_text in enumerate(answers):
            if ans_text.strip():
                is_correct = 1 if str(idx) == correct_index else 0
                c.execute(
                    "INSERT INTO answers (text, question_id, is_correct) VALUES (?, ?, ?)",
                    (ans_text.strip(), question_id, is_correct)
                )

        conn.commit()
        conn.close()
        flash("Savol va variantlar qo‘shildi ✅", "success")
        return redirect(f"/admin/tests/{test_id}/questions")

    conn.close()
    return render_template("admin/add_question.html", test=test, question=None)



# ================= STUDENTS =================
@bp.route("/students")
@admin_required
def students():
    conn = get_db()
    c = conn.cursor()

    page = int(request.args.get("page", 1))
    per_page = 40
    offset = (page - 1) * per_page

    # Qidiruv
    search = request.args.get("search", "").strip()

    if search:
        students = c.execute("""
            SELECT * FROM users
            WHERE role='student' AND (login LIKE ? OR full_name LIKE ? OR number LIKE ?)
            LIMIT ? OFFSET ?
        """, (f"%{search}%", f"%{search}%", f"%{search}%", per_page, offset)).fetchall()

        total = c.execute("""
            SELECT COUNT(*) FROM users
            WHERE role='student' AND (login LIKE ? OR full_name LIKE ? OR number LIKE ?)
        """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchone()[0]
    else:
        students = c.execute("""
            SELECT * FROM users
            WHERE role='student'
            LIMIT ? OFFSET ?
        """, (per_page, offset)).fetchall()

        total = c.execute("""
            SELECT COUNT(*) FROM users
            WHERE role='student'
        """).fetchone()[0]

    students_data = []
    for s in students:
        s_id = s[0]

        # Kurslar va foiz mavzular
        courses_info = []
        enrollments = c.execute("""
            SELECT course_id FROM enrollments
            WHERE user_id = ?
        """, (s_id,)).fetchall()

        for e in enrollments:
            course_id = e[0]
            course = c.execute("SELECT name FROM courses WHERE id = ?", (course_id,)).fetchone()
            total_topics = c.execute("""
                SELECT COUNT(*) FROM topics
                WHERE chapter_id IN (
                    SELECT id FROM chapters WHERE course_id = ?
                )
            """, (course_id,)).fetchone()[0]

            learned_topics = c.execute("""
                SELECT COUNT(*) FROM studies
                WHERE user_id = ? AND topic_id IN (
                    SELECT id FROM topics
                    WHERE chapter_id IN (
                        SELECT id FROM chapters WHERE course_id = ?
                    )
                )
            """, (s_id, course_id)).fetchone()[0]

            percent_done = 0
            if total_topics > 0:
                percent_done = round(learned_topics / total_topics * 100, 1)

            # Sertifikat ma’lumotlari
            cert = c.execute("""
                SELECT date FROM certificates
                WHERE user_id = ? AND course_id = ?
            """, (s_id, course_id)).fetchone()

            courses_info.append({
                "course_id": course_id,
                "course_name": course[0],
                "percent_done": percent_done,
                "certificate_date": cert[0] if cert else None
            })

        # Test urinishlari (test nomi bilan)
        test_stats = c.execute("""
            SELECT e.test_id, t.name, COUNT(e.id) as attempts, MAX(e.score) as max_score
            FROM exams e
            JOIN tests t ON e.test_id = t.id
            WHERE e.user_id = ?
            GROUP BY e.test_id
        """, (s_id,)).fetchall()

        students_data.append((s, courses_info, test_stats))

    conn.close()
    total_pages = math.ceil(total / per_page)

    return render_template(
        "admin/students.html",
        students=students_data,
        page=page,
        total_pages=total_pages,
        search=search
    )    
    
    


# ================= O'QUVCHI TAHRIR =================

@bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_student(student_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  # <-- bu kerak
    c = conn.cursor()
    
    # Foydalanuvchi ma'lumotini olish
    student = c.execute("SELECT * FROM users WHERE id=? AND role='student'", (student_id,)).fetchone()
    if not student:
        conn.close()
        abort(404)
    
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        login = request.form.get("login", "").strip()
        number = request.form.get("number", "").strip()
        password = request.form.get("password", "").strip()
        
        if not full_name or not login:
            flash("Login va To‘liq ism majburiy", "danger")
            return redirect(f"/admin/students/{student_id}/edit")
        
        # Parolni faqat kiritilgan bo‘lsa yangilash
        if password:
            hashed = generate_password_hash(password)
            c.execute("""
                UPDATE users
                SET full_name=?, login=?, number=?, password=?
                WHERE id=?
            """, (full_name, login, number, hashed, student_id))
        else:
            c.execute("""
                UPDATE users
                SET full_name=?, login=?, number=?
                WHERE id=?
            """, (full_name, login, number, student_id))
        
        try:
            conn.commit()
            flash("O‘quvchi ma’lumotlari saqlandi ✅", "success")
        except sqlite3.IntegrityError:
            flash("Bu login allaqachon mavjud!", "danger")
        
        conn.close()
        return redirect("/admin/students")
    
    conn.close()
    return render_template("admin/student_edit.html", student=student)



@bp.route("/students/<int:student_id>/delete", methods=["POST", "GET"])
@admin_required
def delete_student(student_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Foydalanuvchi mavjudligini tekshirish
    student = c.execute("SELECT * FROM users WHERE id=? AND role='student'", (student_id,)).fetchone()
    if not student:
        conn.close()
        abort(404)

    # Foydalanuvchini o'chirish
    c.execute("DELETE FROM users WHERE id=?", (student_id,))
    conn.commit()
    conn.close()

    flash("O‘quvchi o‘chirildi ✅", "success")
    return redirect("/admin/students")



# ================= PROFILE =================


@bp.route("/profile", methods=["GET", "POST"])
@admin_required
def profile():
    print("Profil sahifasi chaqirildi")
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        number = request.form.get("number", "").strip()
        password = request.form.get("password", "").strip()
        password_confirm = request.form.get("password_confirm", "").strip()

        # Agar parol berilgan bo'lsa, tekshirish
        if password or password_confirm:
            if password != password_confirm:
                flash("Parol va tasdiqlash paroli mos emas ❌", "danger")
                admin = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
                conn.close()
                return render_template("admin/profile.html", admin=admin)

            hashed = generate_password_hash(password)
            c.execute(
                "UPDATE users SET full_name=?, number=?, password=? WHERE id=?",
                (full_name, number, hashed, user_id)
            )
            print("Parol yangilandi")
        else:
            c.execute(
                "UPDATE users SET full_name=?, number=? WHERE id=?",
                (full_name, number, 1)
            )
            print("Parol yangilanmaydi")

        conn.commit()
        flash("Profil ma'lumotlari yangilandi ✅", "success")
        print("Profil yangilandi")
        return redirect("/admin/profile")

    # GET: foydalanuvchi ma’lumotlarini olish
    admin = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()

    return render_template("admin/profile.html", admin=admin)
    
    









