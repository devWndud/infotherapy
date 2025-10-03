from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from dotenv import load_dotenv
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-change-me")

    # SQLite init
    db_path = os.path.join(os.path.dirname(__file__), "infotherapy.db")
    invites_path = os.path.join(os.path.dirname(__file__), "invites.json")
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    def get_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    with get_db() as cx:
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              student_id TEXT NOT NULL UNIQUE,
              email TEXT,
              password_hash TEXT NOT NULL,
              admin INTEGER DEFAULT 0
            )
            """
        )
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              name TEXT NOT NULL,
              assignment_title TEXT NOT NULL,
              category TEXT,
              text_content TEXT,
              file_path TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS materials (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              type TEXT,
              category TEXT,
              date TEXT,
              content TEXT
            )
            """
        )
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS assignments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              due TEXT,
              description TEXT,
              category TEXT
            )
            """
        )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            name = request.form.get("name")
            password = request.form.get("password")
            with get_db() as cx:
                row = cx.execute("SELECT id, password_hash, admin, name FROM users WHERE name=?", (name,)).fetchone()
            if row and check_password_hash(row["password_hash"], password):
                session["uid"] = row["id"]
                session["admin"] = bool(row["admin"])
                session["name"] = row["name"]
                flash("로그인되었습니다.", "info")
                return redirect(url_for("learn"))
            flash("이름 또는 비밀번호가 올바르지 않습니다.", "info")
        return render_template("login.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            name = request.form.get("name")
            student_id = request.form.get("student_id")
            invite_code = request.form.get("invite_code")
            password = request.form.get("password")
            password2 = request.form.get("password2")
            admin_flag = 0

            # Invite validation via invites.json
            try:
                with open(invites_path, "r", encoding="utf-8") as f:
                    invite_list = json.load(f)
            except FileNotFoundError:
                invite_list = []

            match = next((i for i in invite_list if i.get("name") == name and i.get("code") == invite_code), None)
            if not match:
                flash("초대 정보가 일치하지 않습니다.", "info")
                return redirect(url_for("signup"))
            admin_flag = 1 if match.get("admin") else 0
            if password != password2:
                flash("비밀번호가 일치하지 않습니다.", "info")
                return redirect(url_for("signup"))
            try:
                with get_db() as cx:
                    cx.execute(
                        "INSERT INTO users (name, student_id, password_hash, admin) VALUES (?,?,?,?)",
                        (name, student_id, generate_password_hash(password), admin_flag),
                    )
                flash("회원가입 완료", "info")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("이미 존재하는 학번입니다.", "info")
                return redirect(url_for("signup"))
        return render_template("signup.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("로그아웃되었습니다.", "info")
        return redirect(url_for("index"))

    def send_admin_email(subject: str, body: str):
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASS")
        sender = os.getenv("SMTP_FROM", user or "noreply@localhost")
        admin_emails = [e.strip() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
        if not (host and admin_emails):
            return  # skip if email not configured
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(admin_emails)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", _charset="utf-8"))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(sender, admin_emails, msg.as_string())

    @app.route("/submit", methods=["POST"])
    def submit_assignment():
        if not session.get("uid"):
            flash("로그인이 필요합니다.", "info")
            return redirect(url_for("login"))
        title = request.form.get("title")
        category = request.form.get("category")
        text_content = request.form.get("text_content") or ""
        uploaded_file = request.files.get("file")
        file_path = None
        # Prevent duplicate submissions per user per assignment/category
        with get_db() as cx:
            exists = cx.execute(
                "SELECT 1 FROM submissions WHERE user_id=? AND assignment_title=? AND IFNULL(category,'')=IFNULL(?, '')",
                (session.get("uid"), title, category),
            ).fetchone()
        if exists:
            flash("이미 제출한 과제입니다.", "info")
            return redirect(url_for("learn"))
        if uploaded_file and uploaded_file.filename:
            safe_name = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(uploaded_file.filename)
            dest = os.path.join(uploads_dir, safe_name)
            uploaded_file.save(dest)
            file_path = dest
        with get_db() as cx:
            cx.execute(
                "INSERT INTO submissions (user_id, name, assignment_title, category, text_content, file_path, created_at) VALUES (?,?,?,?,?,?,?)",
                (session.get("uid"), session.get("name"), title, category, text_content, file_path, datetime.utcnow().isoformat()),
            )
        flash("제출 완료", "info")
        # email notify
        body_lines = [
            f"제출자: {session.get('name')} (user_id={session.get('uid')})",
            f"과제: {title}",
            f"카테고리: {category}",
            f"내용: {text_content[:500]}" if text_content else "내용: (파일만 제출)",
            f"파일: {file_path}" if file_path else "파일: 없음",
        ]
        try:
            send_admin_email(subject=f"[Infotherapy] 과제 제출 - {title}", body="\n".join(body_lines))
        except Exception:
            pass
        return redirect(url_for("learn"))

    def admin_required(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("admin"):
                flash("관리자 권한이 필요합니다.", "info")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)
        return wrapper

    @app.route("/learn")
    def learn():
        # UI-only placeholder list data with categories
        with get_db() as cx:
            materials = cx.execute("SELECT id, title, type, category, date, content FROM materials ORDER BY date DESC NULLS LAST").fetchall()
            assignments = cx.execute("SELECT id, title, due, description, category FROM assignments ORDER BY due ASC NULLS LAST").fetchall()
        # fallback demo data if empty
        if not materials:
            materials = [
                {"id": 1, "title": "딥러닝 기초 슬라이드", "date": "2025-10-01", "type": "slides", "category": "dl", "content": "기초 개념"},
                {"id": 2, "title": "파이썬으로 데이터 전처리", "date": "2025-09-28", "type": "notebook", "category": "ml", "content": "pandas"},
            ]
        if not assignments:
            assignments = [
                {"id": 1, "title": "과제: 로지스틱 회귀 구현", "due": "2025-10-10 23:59", "description": "Numpy만 사용", "category": "ml"},
                {"id": 2, "title": "과제: CNN으로 MNIST 분류", "due": "2025-10-15 23:59", "description": "PyTorch 기본", "category": "dl"},
            ]
        # mark submitted status for current user
        submitted_keys = set()
        if session.get("uid"):
            with get_db() as cx:
                rows = cx.execute(
                    "SELECT assignment_title, category FROM submissions WHERE user_id=?",
                    (session.get("uid"),),
                ).fetchall()
            submitted_keys = {f"{r['assignment_title']}|{r['category'] or ''}" for r in rows}
        return render_template("learn.html", materials=materials, assignments=assignments, submitted_keys=submitted_keys)

    @app.route("/material/<int:item_id>")
    def material_detail(item_id: int):
        with get_db() as cx:
            m = cx.execute("SELECT id, title, type, category, date, content FROM materials WHERE id=?", (item_id,)).fetchone()
        if not m:
            return redirect(url_for("learn"))
        return render_template("material_detail.html", m=m)

    @app.route("/assignment/<int:item_id>")
    def assignment_detail(item_id: int):
        with get_db() as cx:
            a = cx.execute("SELECT id, title, due, description, category FROM assignments WHERE id=?", (item_id,)).fetchone()
        if not a:
            return redirect(url_for("learn"))
        submitted = False
        if session.get("uid"):
            with get_db() as cx:
                row = cx.execute(
                    "SELECT 1 FROM submissions WHERE user_id=? AND assignment_title=? AND IFNULL(category,'')=IFNULL(?, '')",
                    (session.get("uid"), a["title"], a["category"]),
                ).fetchone()
            submitted = bool(row)
        return render_template("assignment_detail.html", a=a, submitted=submitted)

    # Admin dashboard and CRUD
    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        with get_db() as cx:
            materials = cx.execute("SELECT id, title, category, type, date FROM materials ORDER BY date DESC").fetchall()
            assignments = cx.execute("SELECT id, title, category, due FROM assignments ORDER BY due ASC").fetchall()
        return render_template("admin_dashboard.html", materials=materials, assignments=assignments)

    @app.route("/admin/material/new", methods=["GET", "POST"])
    @admin_required
    def admin_material_new():
        if request.method == "POST":
            with get_db() as cx:
                cx.execute("INSERT INTO materials (title, type, category, date, content) VALUES (?,?,?,?,?)",
                           (request.form.get("title"), request.form.get("type"), request.form.get("category"), request.form.get("date"), request.form.get("content")))
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_material_form.html", item=None)

    @app.route("/admin/material/<int:item_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_material_edit(item_id: int):
        with get_db() as cx:
            item = cx.execute("SELECT id, title, type, category, date, content FROM materials WHERE id=?", (item_id,)).fetchone()
        if request.method == "POST":
            with get_db() as cx:
                cx.execute("UPDATE materials SET title=?, type=?, category=?, date=?, content=? WHERE id=?",
                           (request.form.get("title"), request.form.get("type"), request.form.get("category"), request.form.get("date"), request.form.get("content"), item_id))
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_material_form.html", item=item)

    @app.route("/admin/material/<int:item_id>/delete", methods=["POST"])
    @admin_required
    def admin_material_delete(item_id: int):
        with get_db() as cx:
            cx.execute("DELETE FROM materials WHERE id=?", (item_id,))
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/assignment/new", methods=["GET", "POST"])
    @admin_required
    def admin_assignment_new():
        if request.method == "POST":
            with get_db() as cx:
                cx.execute("INSERT INTO assignments (title, due, description, category) VALUES (?,?,?,?)",
                           (request.form.get("title"), request.form.get("due"), request.form.get("description"), request.form.get("category")))
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_assignment_form.html", item=None)

    @app.route("/admin/assignment/<int:item_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_assignment_edit(item_id: int):
        with get_db() as cx:
            item = cx.execute("SELECT id, title, due, description, category FROM assignments WHERE id=?", (item_id,)).fetchone()
        if request.method == "POST":
            with get_db() as cx:
                cx.execute("UPDATE assignments SET title=?, due=?, description=?, category=? WHERE id=?",
                           (request.form.get("title"), request.form.get("due"), request.form.get("description"), request.form.get("category"), item_id))
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_assignment_form.html", item=item)

    @app.route("/admin/assignment/<int:item_id>/delete", methods=["POST"])
    @admin_required
    def admin_assignment_delete(item_id: int):
        with get_db() as cx:
            cx.execute("DELETE FROM assignments WHERE id=?", (item_id,))
        return redirect(url_for("admin_dashboard"))

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            flash("문의가 접수되었습니다 (UI 데모).", "info")
            return redirect(url_for("contact"))
        return render_template("contact.html")

    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


