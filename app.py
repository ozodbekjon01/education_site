from flask import Flask, session, redirect, url_for, request
from routes import auth, admin, dashboard, forum, resources, student, sql_lab

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
app.permanent_session_lifetime = 18000

# Blueprint-larni ro'yxatdan o'tkazish
app.register_blueprint(auth.bp)
app.register_blueprint(admin.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(student.bp)
app.register_blueprint(forum.bp)
app.register_blueprint(resources.bp)
app.register_blueprint(sql_lab.bp, url_prefix="/student/sql-lab")


@app.route('/google72f449df3299647f.html')
def google_verification():
    return "google-site-verification: google72f449df3299647f.html"

@app.route('/')

def index():
    return redirect('/student/dashboard')

# App ishga tushirish
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5300, debug=True)
