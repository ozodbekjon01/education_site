from flask import Blueprint, render_template, request, session, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint('auth', __name__)

# ================= LOGIN =================
@bp.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next')  # qayerdan kelganini olish

    if "user_id" in session:
        return redirect(next_page or "/")

    error = None

    if request.method == 'POST':
        login_input = request.form.get('login')
        password_input = request.form.get('password')
        next_page = request.form.get('next')  # POST dan ham olish

        if not login_input or not password_input:
            error = "Barcha maydonlarni to‘ldiring."
            return render_template("login.html", error=error, next=next_page)

        with sqlite3.connect("database.db") as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, password, full_name, role FROM users WHERE login=?",
                      (login_input,))
            user = c.fetchone()

        if user and check_password_hash(user["password"], password_input):
            session['user_id'] = user["id"]
            session['name'] = user["full_name"]
            session['role'] = user["role"]

            if session['role'] == "admin":
                return redirect("/admin/dashboard")
            
            # 🔥 ASOSIY QISM
            return redirect(next_page or (
                "/admin/dashboard" if user["role"] == "admin"
                else "/student/dashboard"
            ))
        else:
            error = "Login yoki parol noto‘g‘ri."

    return render_template("login.html", error=error, next=next_page)


# ================= REGISTER =================
@bp.route('/register', methods=['GET', 'POST'])
def register():
    next_page = request.args.get('next')

    if "user_id" in session:
        return redirect(next_page or "/")

    error = None

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        number = request.form.get('number')
        login_input = request.form.get('login')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        next_page = request.form.get('next')

        if not all([full_name, login_input, password, password2]):
            error = "Barcha maydonlarni to‘ldiring."
            return render_template("register.html", error=error, next=next_page)

        if password != password2:
            error = "Parollar bir xil emas."
            return render_template("register.html", error=error, next=next_page)

        hashed = generate_password_hash(password)

        with sqlite3.connect("database.db") as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE login=?", (login_input,))
            if c.fetchone():
                error = "Bu login allaqachon band."
                return render_template("register.html", error=error, next=next_page)

            c.execute("""
                INSERT INTO users (login, password, full_name, number, role)
                VALUES (?, ?, ?, ?, ?)
            """, (login_input, hashed, full_name, None, "student"))

            conn.commit()
            user_id = c.lastrowid

        session['user_id'] = user_id
        session['name'] = full_name
        session['role'] = "student"

        return redirect(next_page or "/student/dashboard")

    return render_template("register.html", error=error, next=next_page)


# ================= LOGOUT =================
@bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
