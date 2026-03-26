from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename

bp = Blueprint("resources", __name__)

UPLOAD_FOLDER = "static/resources"

@bp.route("/admin/resources", methods=["GET","POST"])
def admin_resources():

    # admin tekshirish (o'zingizning login tizimingizga moslashtiring)
    if session.get("role") != "admin":
        return redirect("/login")

    if request.method == "POST":

        title = request.form.get("title")
        file = request.files.get("file")

        if file:

            filename = secure_filename(file.filename)

            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            with sqlite3.connect("database.db") as conn:
                c = conn.cursor()

                c.execute(
                    "INSERT INTO resources(title,file) VALUES (?,?)",
                    (title, filename)
                )

                conn.commit()

        return redirect(url_for("resources.admin_resources"))

    # GET
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute("SELECT * FROM resources ORDER BY id DESC")
        resources = c.fetchall()

    return render_template(
        "admin/resources.html",
        resources=resources
    )
    
@bp.route("/admin/resources/delete/<int:res_id>")
def delete_resource(res_id):

    if session.get("role") != "admin":
        return redirect("/login")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute("SELECT file FROM resources WHERE id=?", (res_id,))
        file = c.fetchone()

        if file:
            path = f"static/resources/{file[0]}"

            if os.path.exists(path):
                os.remove(path)

        c.execute("DELETE FROM resources WHERE id=?", (res_id,))
        conn.commit()

    return redirect("/admin/resources")



