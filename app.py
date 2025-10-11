from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
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
import io
import csv
from openpyxl import Workbook
import re
from markupsafe import Markup, escape


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-change-me")
    app.config["ASSET_VERSION"] = os.getenv("ASSET_VERSION") or datetime.utcnow().strftime("%Y%m%d%H%M%S")
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB 파일 크기 제한

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

    url_regex = re.compile(r"(https?://[^\s]+)")

    def autolink(text: str) -> Markup:
        if not text:
            return Markup("")
        html = escape(text)
        html = url_regex.sub(lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>', html)
        html = html.replace("\r\n", "\n").replace("\n", "<br>")
        return Markup(html)

    app.jinja_env.filters["autolink"] = autolink

    @app.context_processor
    def inject_static_url():
        def static_url(filename: str) -> str:
            return url_for("static", filename=filename, v=app.config.get("ASSET_VERSION"))
        return {"static_url": static_url}

    def format_datetime_short(value: str) -> str:
        if not value:
            return ""
        fmts = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ]
        dt = None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            for f in fmts:
                try:
                    dt = datetime.strptime(value, f)
                    break
                except Exception:
                    continue
        if not dt:
            return value
        if dt.hour != 0 or dt.minute != 0:
            return dt.strftime("%m-%d %H:%M")
        return dt.strftime("%m-%d")

    app.jinja_env.filters["short_dt"] = format_datetime_short
    
    def basename_filter(path: str) -> str:
        return os.path.basename(path) if path else ""
    
    def file_size_filter(path: str) -> str:
        if not path or not os.path.exists(path):
            return "0"
        size_mb = os.path.getsize(path) / (1024 * 1024)
        return f"{size_mb:.2f}"
    
    def is_video_filter(path: str) -> bool:
        if not path:
            return False
        video_extensions = ['.mp4', '.avi', '.mov', '.webm', '.mkv', '.wmv', '.flv']
        return any(path.lower().endswith(ext) for ext in video_extensions)
    
    app.jinja_env.filters["basename"] = basename_filter
    app.jinja_env.filters["file_size"] = file_size_filter
    app.jinja_env.filters["is_video"] = is_video_filter

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

    def send_admin_email(subject: str, body: str, attachments: list | None = None):
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASS")
        sender = os.getenv("SMTP_FROM", user or "noreply@localhost")
        admin_emails = [e.strip() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
        if not (host and admin_emails):
            return
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(admin_emails)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", _charset="utf-8"))
        for att in attachments or []:
            try:
                from email.mime.base import MIMEBase
                from email import encoders
                path = att.get("path")
                mime = att.get("mime", "application/octet-stream")
                if not path or not os.path.isfile(path):
                    continue
                part = MIMEBase(*mime.split("/", 1))
                with open(path, "rb") as f:
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename=\"{os.path.basename(path)}\"")
                msg.attach(part)
            except Exception:
                continue
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
        with get_db() as cx:
            exists = cx.execute(
                "SELECT 1 FROM submissions WHERE user_id=? AND assignment_title=? AND IFNULL(category,'')=IFNULL(?, '')",
                (session.get("uid"), title, category),
            ).fetchone()
        if exists:
            flash("이미 제출한 과제입니다.", "info")
            return redirect(url_for("learn"))
        if uploaded_file and uploaded_file.filename:
            # 영상 파일 타입 검증
            allowed_video_types = ['video/mp4', 'video/avi', 'video/quicktime', 'video/webm', 'video/x-msvideo', 'video/x-ms-wmv', 'video/x-flv', 'video/x-matroska']
            file_type = uploaded_file.content_type
            
            if file_type not in allowed_video_types:
                flash("지원하지 않는 파일 형식입니다. 영상 파일만 업로드 가능합니다.", "info")
                return redirect(url_for("learn"))
            
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
        body_lines = [
            f"제출자: {session.get('name')} (user_id={session.get('uid')})",
            f"과제: {title}",
            f"카테고리: {category}",
            f"제출시간(UTC): {datetime.utcnow().isoformat(timespec='seconds')}",
            "",
            "[제출 내용]",
            text_content if text_content else "(텍스트 없음)",
        ]
        
        if file_path:
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB 단위
            body_lines.extend([
                "",
                "[첨부 파일]",
                f"파일명: {os.path.basename(file_path)}",
                f"파일 크기: {file_size:.2f}MB",
                f"파일 타입: 영상 파일",
                f"파일 경로: {file_path}"
            ])
        try:
            attachments = []
            if file_path:
                import mimetypes
                mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                attachments.append({"path": file_path, "mime": mime})
            send_admin_email(subject=f"{session.get('name')} - {title} 제출", body="\n".join(body_lines), attachments=attachments)
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
        with get_db() as cx:
            materials = cx.execute("SELECT id, title, type, category, date, content FROM materials ORDER BY date DESC").fetchall()
            assignments_rows = cx.execute("SELECT id, title, due, description, category FROM assignments ORDER BY due ASC").fetchall()
        def is_overdue(due_str: str) -> bool:
            if not due_str:
                return False
            try:
                from zoneinfo import ZoneInfo
                seoul = ZoneInfo("Asia/Seoul")
                now_local = datetime.now(seoul)
            except Exception:
                seoul = None
                now_local = datetime.now()
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    due_dt = datetime.strptime(due_str.strip(), fmt)
                    if fmt == "%Y-%m-%d":
                        due_dt = due_dt.replace(hour=23, minute=59, second=59)
                    if seoul:
                        due_dt = due_dt.replace(tzinfo=seoul)
                    return now_local > due_dt
                except Exception:
                    continue
            return False
        assignments = []
        submission_map = {}
        if session.get("uid"):
            with get_db() as cx:
                rows = cx.execute(
                    "SELECT assignment_title, IFNULL(category,'') AS category, created_at FROM submissions WHERE user_id=?",
                    (session.get("uid"),),
                ).fetchall()
            submission_map = {f"{r['assignment_title']}|{r['category']}": r["created_at"] for r in rows}
        for a in assignments_rows:
            d = dict(a)
            d["overdue"] = is_overdue(d.get("due", ""))
            key = f"{d.get('title')}|{d.get('category') or ''}"
            d["submitted_at"] = submission_map.get(key)
            assignments.append(d)
        return render_template("learn.html", materials=materials, assignments=assignments)

    @app.route("/activities")
    def activities():
        return render_template("activities.html")


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
        a = dict(a)
        def is_overdue(due_str: str) -> bool:
            if not due_str:
                return False
            try:
                from zoneinfo import ZoneInfo
                seoul = ZoneInfo("Asia/Seoul")
                now_local = datetime.now(seoul)
            except Exception:
                seoul = None
                now_local = datetime.now()
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    due_dt = datetime.strptime(due_str.strip(), fmt)
                    if fmt == "%Y-%m-%d":
                        due_dt = due_dt.replace(hour=23, minute=59, second=59)
                    if seoul:
                        due_dt = due_dt.replace(tzinfo=seoul)
                    return now_local > due_dt
                except Exception:
                    continue
            return False
        overdue = is_overdue(a.get("due", ""))
        submitted = False
        submitted_at = None
        if session.get("uid"):
            with get_db() as cx:
                row = cx.execute(
                    "SELECT created_at FROM submissions WHERE user_id=? AND assignment_title=? AND IFNULL(category,'')=IFNULL(?, '')",
                    (session.get("uid"), a["title"], a["category"]),
                ).fetchone()
            if row:
                submitted = True
                submitted_at = row["created_at"]
        return render_template("assignment_detail.html", a=a, submitted=submitted, submitted_at=submitted_at, overdue=overdue)

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

    @app.route("/admin/assignment/<int:item_id>/submissions")
    @admin_required
    def admin_assignment_submissions(item_id: int):
        with get_db() as cx:
            assignment = cx.execute("SELECT id, title, due, description, category FROM assignments WHERE id=?", (item_id,)).fetchone()
            if not assignment:
                flash("과제를 찾을 수 없습니다.", "info")
                return redirect(url_for("admin_dashboard"))
            
            submissions = cx.execute("""
                SELECT s.id, s.name, s.assignment_title, s.category, s.text_content, s.file_path, s.created_at
                FROM submissions s
                WHERE s.assignment_title = ? AND IFNULL(s.category, '') = IFNULL(?, '')
                ORDER BY s.created_at DESC
            """, (assignment['title'], assignment['category'])).fetchall()
        
        return render_template("admin_assignment_submissions.html", assignment=assignment, submissions=submissions)

    @app.route("/admin/submission/<int:submission_id>")
    @admin_required
    def admin_submission_detail(submission_id: int):
        with get_db() as cx:
            submission = cx.execute("""
                SELECT s.id, s.name, s.assignment_title, s.category, s.text_content, s.file_path, s.created_at
                FROM submissions s
                WHERE s.id = ?
            """, (submission_id,)).fetchone()
            
            if not submission:
                flash("제출을 찾을 수 없습니다.", "info")
                return redirect(url_for("admin_dashboard"))
        
        return render_template("admin_submission_detail.html", submission=submission)

    @app.route("/admin/submission/<int:submission_id>/download")
    @admin_required
    def admin_submission_download(submission_id: int):
        with get_db() as cx:
            submission = cx.execute("SELECT file_path FROM submissions WHERE id=?", (submission_id,)).fetchone()
            
            if not submission or not submission['file_path']:
                flash("파일을 찾을 수 없습니다.", "info")
                return redirect(url_for("admin_dashboard"))
            
            if not os.path.exists(submission['file_path']):
                flash("파일이 존재하지 않습니다.", "info")
                return redirect(url_for("admin_dashboard"))
            
            return send_from_directory(
                os.path.dirname(submission['file_path']),
                os.path.basename(submission['file_path']),
                as_attachment=True
            )

    @app.route("/admin/invites/export")
    @admin_required
    def export_invites_csv():
        try:
            with open(invites_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["name", "code", "admin"])
        for item in data:
            writer.writerow([item.get("name", ""), item.get("code", ""), "TRUE" if item.get("admin") else "FALSE"])
        csv_bytes = output.getvalue().encode("utf-8-sig")
        from flask import Response
        return Response(csv_bytes, mimetype="text/csv", headers={
            "Content-Disposition": "attachment; filename=invites.csv"
        })

    @app.route("/admin/invites/export.xlsx")
    @admin_required
    def export_invites_xlsx():
        try:
            with open(invites_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []
        wb = Workbook()
        ws = wb.active
        ws.title = "invites"
        ws.append(["name", "code", "admin"])
        for item in data:
            ws.append([item.get("name", ""), item.get("code", ""), bool(item.get("admin"))])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        from flask import send_file
        return send_file(bio, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="invites.xlsx")

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

    @app.route("/google813ed25fdce8f7cd.html")
    def google_verification():
        return "google-site-verification: google813ed25fdce8f7cd.html"

    @app.route("/googled4feaeeec5cf3d2e.html")
    def google_verification2():
        return "google-site-verification: googled4feaeeec5cf3d2e.html"

    @app.route("/sitemap.xml")
    def sitemap():
        from flask import Response
        import xml.etree.ElementTree as ET
        
        root = ET.Element("urlset")
        root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        
        urls = [
            {"loc": "https://infotherapy.kro.kr/", "changefreq": "daily", "priority": "1.0"},
            {"loc": "https://infotherapy.kro.kr/learn", "changefreq": "weekly", "priority": "0.8"},
            {"loc": "https://infotherapy.kro.kr/contact", "changefreq": "monthly", "priority": "0.6"},
            {"loc": "https://infotherapy.kro.kr/terms", "changefreq": "yearly", "priority": "0.4"},
            {"loc": "https://infotherapy.kro.kr/privacy", "changefreq": "yearly", "priority": "0.4"},
        ]
        
        with get_db() as cx:
            materials = cx.execute("SELECT id FROM materials").fetchall()
            assignments = cx.execute("SELECT id FROM assignments").fetchall()
            
            for material in materials:
                urls.append({
                    "loc": f"https://infotherapy.kro.kr/material/{material['id']}",
                    "changefreq": "monthly",
                    "priority": "0.7"
                })
            
            for assignment in assignments:
                urls.append({
                    "loc": f"https://infotherapy.kro.kr/assignment/{assignment['id']}",
                    "changefreq": "weekly",
                    "priority": "0.7"
                })
        
        for url_data in urls:
            url_elem = ET.SubElement(root, "url")
            ET.SubElement(url_elem, "loc").text = url_data["loc"]
            ET.SubElement(url_elem, "changefreq").text = url_data["changefreq"]
            ET.SubElement(url_elem, "priority").text = url_data["priority"]
        
        xml_str = ET.tostring(root, encoding='unicode')
        return Response(xml_str, mimetype='application/xml')

    @app.route("/robots.txt")
    def robots_txt():
        return "User-agent: *\nAllow: /\n\nSitemap: https://infotherapy.kro.kr/sitemap.xml"

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


