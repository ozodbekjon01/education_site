from flask import Blueprint, render_template, request, session, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint('auth', __name__)

# ================= LOGIN =================
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if "user_id" in session:
        if session["role"] == "student":
                return redirect("/student/dashboard")
        elif session["role"] == "admin":
                return redirect("/admin/dashboard")
        

    error = None

    if request.method == 'POST':
        login_input = request.form.get('login')
        password_input = request.form.get('password')

        if not login_input or not password_input:
            error = "Barcha maydonlarni to‘ldiring."
            return render_template("login.html", error=error)

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

            if user["role"] == "admin":
                return redirect("/admin/dashboard")
            elif user["role"] == "student":
                return redirect("/student/dashboard")
            else:
                return redirect("/dashboard")
        else:
            error = "Login yoki parol noto‘g‘ri."

    return render_template("login.html", error=error)


# ================= REGISTER =================
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if "user_id" in session:
        if session["role"] == "admin":
                return redirect("/admin/dashboard")
        elif session["role"] == "student":
                return redirect("/student/dashboard")
        return redirect("/dashboard")

    error = None

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        number = request.form.get('number')
        login_input = request.form.get('login')
        password = request.form.get('password')
        password2 = request.form.get('password2')

        if not all([full_name, number, login_input, password, password2]):
            error = "Barcha maydonlarni to‘ldiring."
            return render_template("register.html", error=error)

        if password != password2:
            error = "Parollar bir xil emas."
            return render_template("register.html", error=error)

        hashed = generate_password_hash(password)

        with sqlite3.connect("database.db") as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE login=?", (login_input,))
            existing_user = c.fetchone()

            if existing_user:
                error = "Bu login allaqachon band."
                return render_template("register.html", error=error)

            c.execute("""
                INSERT INTO users (login, password, full_name, number, role)
                VALUES (?, ?, ?, ?, ?)
            """, (login_input, hashed, full_name, number, "student"))

            conn.commit()

            user_id = c.lastrowid

        session['user_id'] = user_id
        session['name'] = full_name
        session['role'] = "student"

        return redirect("/student/dashboard")

    return render_template("register.html", error=error)


# ================= LOGOUT =================
@bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')