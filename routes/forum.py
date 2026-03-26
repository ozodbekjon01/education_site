from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3

bp = Blueprint("forum", __name__)



@bp.route("/student/forum", methods=["GET","POST"])
def forum():

    if "user_id" not in session:
        return redirect("/login")

    # POST -> yangi post
    if request.method == "POST":

        title = request.form.get("title")
        content = request.form.get("content")

        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()

            c.execute(
                "INSERT INTO forum_posts (user_id,title,content) VALUES (?,?,?)",
                (session["user_id"], title, content)
            )

            conn.commit()

        return redirect(url_for("forum.forum"))

    # FILTER + SEARCH + PAGINATION
    search = request.args.get("search","")
    filter_type = request.args.get("filter","all")

    page = request.args.get("page",1,type=int)

    per_page = 10
    offset = (page-1) * per_page

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        base_query = """
        SELECT DISTINCT forum_posts.*, users.full_name
        FROM forum_posts
        JOIN users ON forum_posts.user_id = users.id
        """

        where = []
        params = []

        # filter
        if filter_type == "mine":
            where.append("forum_posts.user_id=?")
            params.append(session["user_id"])

        elif filter_type == "commented":
            base_query += """
            LEFT JOIN forum_comments
            ON forum_comments.post_id = forum_posts.id
            """
            where.append("forum_comments.user_id=?")
            params.append(session["user_id"])

        # search
        if search:
            where.append("(forum_posts.title LIKE ? OR forum_posts.content LIKE ?)")
            params.append(f"%{search}%")
            params.append(f"%{search}%")

        if where:
            base_query += " WHERE " + " AND ".join(where)

        base_query += " ORDER BY forum_posts.created_at DESC LIMIT ? OFFSET ?"

        params.extend([per_page, offset])

        c.execute(base_query, params)
        posts = c.fetchall()

        # count
        count_query = """
        SELECT COUNT(DISTINCT forum_posts.id)
        FROM forum_posts
        """

        if filter_type == "commented":
            count_query += """
            LEFT JOIN forum_comments
            ON forum_comments.post_id = forum_posts.id
            """

        if where:
            count_query += " WHERE " + " AND ".join(where)

        c.execute(count_query, params[:-2])
        total_posts = c.fetchone()[0]

        total_pages = (total_posts + per_page - 1)//per_page

        # comments
        c.execute("""
        SELECT forum_comments.*, users.full_name
        FROM forum_comments
        JOIN users ON forum_comments.user_id = users.id
        ORDER BY created_at
        """)

        comments = c.fetchall()

    return render_template(
        "student/forum.html",
        posts=posts,
        comments=comments,
        page=page,
        total_pages=total_pages,
        search=search,
        filter_type=filter_type
    )


@bp.route("/student/forum/delete/<int:post_id>")
def delete_post(post_id):

    if "user_id" not in session:
        return redirect("/login")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute(
            "DELETE FROM forum_posts WHERE id=? AND user_id=?",
            (post_id, session["user_id"])
        )

        conn.commit()

    return redirect(url_for("forum.forum"))



@bp.route("/student/forum/edit/<int:post_id>", methods=["GET","POST"])
def edit_post(post_id):

    if "user_id" not in session:
        return redirect("/login")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        # postni olish
        c.execute(
            "SELECT * FROM forum_posts WHERE id=? AND user_id=?",
            (post_id, session["user_id"])
        )
        post = c.fetchone()

        # agar post topilmasa
        if not post:
            return redirect(url_for("forum.forum"))

        if request.method == "POST":

            title = request.form.get("title")
            content = request.form.get("content")

            c.execute(
                """
                UPDATE forum_posts
                SET title=?, content=?
                WHERE id=? AND user_id=?
                """,
                (title, content, post_id, session["user_id"])
            )

            conn.commit()

            return redirect(url_for("forum.forum"))

    return render_template("student/edit_post.html", post=post)




@bp.route("/student/forum/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):

    content = request.form.get("content")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute(
            """INSERT INTO forum_comments (user_id,post_id,content)
               VALUES (?,?,?)""",
            (session["user_id"],post_id,content)
        )

        conn.commit()

    return redirect(url_for("forum.forum"))


@bp.route("/student/forum/comment/delete/<int:comment_id>")
def delete_comment(comment_id):

    if "user_id" not in session:
        return redirect("/login")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute(
            "DELETE FROM forum_comments WHERE id=? AND user_id=?",
            (comment_id, session["user_id"])
        )

        conn.commit()

    return redirect(url_for("forum.forum"))






















@bp.route("/admin/forum/add", methods=["POST"])
def forum_add():

    if "user_id" not in session:
        return redirect("/login")

    text = request.form.get("text")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute("""
        INSERT INTO forum_posts(user_id, text)
        VALUES(?,?)
        """, (session["user_id"], text))

        conn.commit()

    return redirect("/admin/forum")



@bp.route("/admin/forum/comment/<int:post_id>", methods=["POST"])
def forum_comment(post_id):

    if "user_id" not in session:
        return redirect("/login")

    text = request.form.get("text")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute("""
        INSERT INTO forum_comments(user_id, post_id, content)
        VALUES(?,?,?)
        """, (session["user_id"], post_id, text))

        conn.commit()

    return redirect("/admin/forum")






























@bp.route("/student/resources")
def resources():

    if "user_id" not in session:
        return redirect("/login")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute("""
        SELECT *
        FROM resources
        ORDER BY id DESC
        """)

        resources = c.fetchall()

    return render_template(
        "student/resources.html",
        resources=resources
    )
    
    









































@bp.route("/admin/forum")
def admin_forum():

    if session.get("role") != "admin":
        return redirect("/login")

    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        # postlar pagination bilan
        c.execute("""
        SELECT forum_posts.*, users.full_name
        FROM forum_posts
        JOIN users ON forum_posts.user_id = users.id
        ORDER BY forum_posts.id DESC
        LIMIT ? OFFSET ?
        """, (per_page, offset))

        posts = c.fetchall()

        # commentlar
        c.execute("""
        SELECT forum_comments.*, users.full_name
        FROM forum_comments
        JOIN users ON forum_comments.user_id = users.id
        """)

        comments = c.fetchall()

        # jami postlar soni
        c.execute("SELECT COUNT(*) FROM forum_posts")
        total_posts = c.fetchone()[0]

    total_pages = (total_posts + per_page - 1) // per_page

    return render_template(
        "admin/forum.html",
        posts=posts,
        comments=comments,
        page=page,
        total_pages=total_pages
    )   
    
@bp.route("/admin/forum/delete/post/<int:post_id>")
def admin_delete_post(post_id):

    if session.get("role") != "admin":
        return redirect("/login")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute("DELETE FROM forum_posts WHERE id=?", (post_id,))
        c.execute("DELETE FROM forum_comments WHERE post_id=?", (post_id,))

        conn.commit()

    return redirect("/admin/forum")

@bp.route("/admin/forum/delete/comment/<int:comment_id>")
def admin_delete_comment(comment_id):

    if session.get("role") != "admin":
        return redirect("/login")

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()

        c.execute("DELETE FROM forum_comments WHERE id=?", (comment_id,))
        conn.commit()

    return redirect("/admin/forum")

