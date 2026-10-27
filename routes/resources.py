from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

bp = Blueprint("resources", __name__)

UPLOAD_FOLDER = "static/resources"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect("database.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def ensure_order_column():
    """Ensure order_index column exists in resources table"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            cols = [r[1] for r in c.execute("PRAGMA table_info(resources)").fetchall()]
            if "order_index" not in cols:
                c.execute("ALTER TABLE resources ADD COLUMN order_index INTEGER DEFAULT 0")
                conn.commit()
    except Exception:
        pass

ensure_order_column()

@bp.route("/admin/resources", methods=["GET", "POST"])
def admin_resources():
    if session.get("role") != "admin":
        return redirect("/login")

    ensure_order_column()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        file = request.files.get("file")

        if not title:
            title = file.filename if file else "Nomsiz resurs"

        if file and file.filename:
            filename = secure_filename(file.filename)
            # Ensure unique filename if already exists
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            base_name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(filepath):
                filename = f"{base_name}_{counter}{ext}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                counter += 1

            file.save(filepath)

            with get_db() as conn:
                c = conn.cursor()
                # Get current max order_index
                max_order = c.execute("SELECT MAX(order_index) FROM resources").fetchone()[0]
                next_order = (max_order + 1) if max_order is not None else 0

                c.execute(
                    "INSERT INTO resources(title, file, order_index) VALUES (?, ?, ?)",
                    (title, filename, next_order)
                )
                conn.commit()

            flash("Resurs muvaffaqiyatli yuklandi ✅", "success")

            # If request is AJAX (XHR upload)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.form.get("is_ajax") == "1":
                return jsonify({
                    "status": "success",
                    "message": "Resurs muvaffaqiyatli yuklandi ✅",
                    "filename": filename,
                    "title": title
                })

        return redirect(url_for("resources.admin_resources"))

    # GET
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, title, file, COALESCE(order_index, 0) as ord
            FROM resources
            ORDER BY ord ASC, id ASC
        """)
        resources_raw = c.fetchall()

    # Calculate file sizes if available
    resources = []
    for r in resources_raw:
        res_id, r_title, r_file, r_order = r[0], r[1], r[2], r[3]
        file_path = os.path.join(UPLOAD_FOLDER, r_file) if r_file else ""
        size_str = ""
        if file_path and os.path.exists(file_path):
            size_bytes = os.path.getsize(file_path)
            if size_bytes >= 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            elif size_bytes >= 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes} B"
        resources.append({
            "id": res_id,
            "title": r_title,
            "file": r_file,
            "order": r_order,
            "size": size_str
        })

    return render_template(
        "admin/resources.html",
        resources=resources
    )

@bp.route("/admin/resources/reorder", methods=["POST"])
def reorder_resources():
    """Update custom order of resources via Drag & Drop or API"""
    if session.get("role") != "admin":
        return jsonify({"status": "error", "message": "Ruxsat yo'q"}), 403

    ensure_order_column()
    data = request.get_json() or {}
    order_ids = data.get("order", [])

    if not order_ids or not isinstance(order_ids, list):
        return jsonify({"status": "error", "message": "Tartib ro'yxati noto'g'ri"}), 400

    with get_db() as conn:
        c = conn.cursor()
        for index, res_id in enumerate(order_ids):
            c.execute("UPDATE resources SET order_index = ? WHERE id = ?", (index, int(res_id)))
        conn.commit()

    return jsonify({"status": "success", "message": "Resurslar tartibi muvaffaqiyatli saqlandi ✅"})

@bp.route("/admin/resources/move/<int:res_id>/<direction>", methods=["POST", "GET"])
def move_resource(res_id, direction):
    """Move a single resource up or down relative to adjacent neighbors"""
    if session.get("role") != "admin":
        return redirect("/login")

    ensure_order_column()

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, COALESCE(order_index, 0) FROM resources ORDER BY COALESCE(order_index, 0) ASC, id ASC")
        rows = c.fetchall()

        ids = [r[0] for r in rows]
        if res_id in ids:
            curr_idx = ids.index(res_id)
            if direction == "up" and curr_idx > 0:
                # Swap with previous
                ids[curr_idx], ids[curr_idx - 1] = ids[curr_idx - 1], ids[curr_idx]
            elif direction == "down" and curr_idx < len(ids) - 1:
                # Swap with next
                ids[curr_idx], ids[curr_idx + 1] = ids[curr_idx + 1], ids[curr_idx]

            for new_pos, item_id in enumerate(ids):
                c.execute("UPDATE resources SET order_index = ? WHERE id = ?", (new_pos, item_id))
            conn.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"status": "success"})
    return redirect(url_for("resources.admin_resources"))

@bp.route("/admin/resources/delete/<int:res_id>", methods=["GET", "POST"])
def delete_resource(res_id):
    if session.get("role") != "admin":
        return redirect("/login")

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT file FROM resources WHERE id = ?", (res_id,))
        file_row = c.fetchone()

        if file_row and file_row[0]:
            path = os.path.join(UPLOAD_FOLDER, file_row[0])
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        c.execute("DELETE FROM resources WHERE id = ?", (res_id,))
        conn.commit()

    flash("Resurs o‘chirildi ✅", "success")
    return redirect(url_for("resources.admin_resources"))
