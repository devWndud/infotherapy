from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import os
from dotenv import load_dotenv
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pytz
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
    
    # 한국 시간대 설정
    seoul_tz = pytz.timezone('Asia/Seoul')
    app.config["ASSET_VERSION"] = os.getenv("ASSET_VERSION") or datetime.now(seoul_tz).strftime("%Y%m%d%H%M%S")
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB 파일 크기 제한
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # 30일간 로그인 유지

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
              admin INTEGER DEFAULT 0,
              interests TEXT DEFAULT '[]'
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
              file_paths TEXT DEFAULT '[]',
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
              category TEXT,
              file_path TEXT,
              file_paths TEXT DEFAULT '[]'
            )
            """
        )

        # 기존 테이블에 file_path 컬럼 추가 (이미 존재하면 무시됨)
        try:
            cx.execute("ALTER TABLE assignments ADD COLUMN file_path TEXT")
        except sqlite3.OperationalError:
            pass
        
        # 기존 테이블에 file_paths 컬럼 추가 (이미 존재하면 무시됨)
        try:
            cx.execute("ALTER TABLE assignments ADD COLUMN file_paths TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재하는 경우
        
        # 기존 submissions 테이블에 file_paths 컬럼 추가 (이미 존재하면 무시됨)
        try:
            cx.execute("ALTER TABLE submissions ADD COLUMN file_paths TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재하는 경우
        
        # 기존 users 테이블에 interests 컬럼 추가 (이미 존재하면 무시됨)
        try:
            cx.execute("ALTER TABLE users ADD COLUMN interests TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재하는 경우
        
        # 포트폴리오 테이블 생성
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolios (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL UNIQUE,
              github_url TEXT,
              discord_id TEXT,
              contacts TEXT DEFAULT '[]',
              bio TEXT,
              projects TEXT DEFAULT '[]',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        
        # 기존 테이블에 contacts 컬럼 추가 (이미 존재하면 무시됨)
        try:
            cx.execute("ALTER TABLE portfolios ADD COLUMN contacts TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재하는 경우

    url_regex = re.compile(r"(https?://[^\s]+)")

    def autolink(text: str) -> Markup:
        if not text:
            return Markup("")
        html = escape(text)
        html = url_regex.sub(lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>', html)
        html = html.replace("\r\n", "\n").replace("\n", "<br>")
        return Markup(html)

    app.jinja_env.filters["autolink"] = autolink
    
    def from_json_filter(json_str):
        if not json_str or not json_str.strip():
            return []
        try:
            return json.loads(json_str)
        except:
            return []
    
    app.jinja_env.filters["from_json"] = from_json_filter

    @app.context_processor
    def inject_static_url():
        def static_url(filename: str) -> str:
            base_url = url_for("static", filename=filename)
            version = app.config.get("ASSET_VERSION", "20251011")
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}v={version}"
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
            from zoneinfo import ZoneInfo
            seoul = ZoneInfo("Asia/Seoul")
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=seoul)
            else:
                dt = dt.astimezone(seoul)
        except Exception:
            for f in fmts:
                try:
                    dt = datetime.strptime(value, f)
                    dt = dt.replace(tzinfo=ZoneInfo("Asia/Seoul"))
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
    
    def is_image_filter(path: str) -> bool:
        if not path:
            return False
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
        return any(path.lower().endswith(ext) for ext in image_extensions)
    
    def category_display_filter(category: str) -> str:
        category_map = {
            'unity': 'Unity',
            'ml': '머신러닝',
            'dl': '딥러닝',
            'web': 'Web'
        }
        return category_map.get(category, category)
    
    app.jinja_env.filters["basename"] = basename_filter
    app.jinja_env.filters["file_size"] = file_size_filter
    app.jinja_env.filters["is_video"] = is_video_filter
    app.jinja_env.filters["is_image"] = is_image_filter
    app.jinja_env.filters["category_display"] = category_display_filter

    @app.route("/")
    def index():
        return render_template("index.html")
    
    @app.route("/menu")
    def menu():
        return render_template("menu.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            name = request.form.get("name")
            password = request.form.get("password")
            with get_db() as cx:
                row = cx.execute("SELECT id, password_hash, admin, name FROM users WHERE name=?", (name,)).fetchone()
            if row and check_password_hash(row["password_hash"], password):
                session.permanent = True
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
                    # 모든 분야를 기본값으로 설정
                    default_interests = '["unity", "ml", "dl", "web"]'
                    cx.execute(
                        "INSERT INTO users (name, student_id, password_hash, admin, interests) VALUES (?,?,?,?,?)",
                        (name, student_id, generate_password_hash(password), admin_flag, default_interests),
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
        
        # 여러 파일 처리
        uploaded_files = request.files.getlist("files")
        file_paths = []
        
        for uploaded_file in uploaded_files:
            if uploaded_file and uploaded_file.filename and uploaded_file.filename.strip():
                # 한글 파일명 지원을 위해 secure_filename 대신 직접 처리
                filename = uploaded_file.filename
                # 위험한 문자만 제거
                filename = filename.replace('..', '').replace('/', '').replace('\\', '')
                
                # 파일명 중복 방지를 위해 타임스탬프 추가
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now(seoul_tz).strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 밀리초까지
                unique_filename = f"{name}_{timestamp}{ext}"
                
                # 실제 파일 저장
                full_dest = os.path.join(uploads_dir, unique_filename)
                uploaded_file.save(full_dest)
                
                # 데이터베이스에는 파일명만 저장 (상대 경로)
                file_paths.append(unique_filename)
        
        with get_db() as cx:
            exists = cx.execute(
                "SELECT 1 FROM submissions WHERE user_id=? AND assignment_title=? AND IFNULL(category,'')=IFNULL(?, '')",
                (session.get("uid"), title, category),
            ).fetchone()
        if exists:
            flash("이미 제출한 과제입니다.", "info")
            return redirect(url_for("learn"))
        with get_db() as cx:
            seoul_time = datetime.now(seoul_tz).isoformat()
            cx.execute(
                "INSERT INTO submissions (user_id, name, assignment_title, category, text_content, file_paths, created_at) VALUES (?,?,?,?,?,?,?)",
                (session.get("uid"), session.get("name"), title, category, text_content, json.dumps(file_paths), seoul_time),
            )
        flash("제출 완료", "info")
        
        email_subject = f"{session.get('name')} - {title} 제출"
        body_lines = [
            f"제출자: {session.get('name')}",
            f"과제명: {title}",
            f"카테고리: {category or '없음'}",
            f"제출 시간: {datetime.now(seoul_tz).strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "[제출 내용]",
            text_content if text_content else "(텍스트 없음)",
        ]
        
        if file_paths:
            body_lines.extend([
                "",
                "[첨부파일]",
                f"파일 개수: {len(file_paths)}개"
            ])
            for file_path in file_paths:
                body_lines.append(f"- {os.path.basename(file_path)}")
        
        try:
            send_admin_email(subject=email_subject, body="\n".join(body_lines), attachments=None)
        except Exception:
            pass
        return redirect(url_for("learn"))

    @app.route("/resubmit", methods=["POST"])
    def resubmit_assignment():
        if not session.get("uid"):
            flash("로그인이 필요합니다.", "info")
            return redirect(url_for("login"))
        
        title = request.form.get("title")
        category = request.form.get("category")
        text_content = request.form.get("text_content") or ""
        
        # 여러 파일 처리
        uploaded_files = request.files.getlist("files")
        file_paths = []
        
        for uploaded_file in uploaded_files:
            if uploaded_file and uploaded_file.filename and uploaded_file.filename.strip():
                # 한글 파일명 지원을 위해 secure_filename 대신 직접 처리
                filename = uploaded_file.filename
                # 위험한 문자만 제거
                filename = filename.replace('..', '').replace('/', '').replace('\\', '')
                
                # 파일명 중복 방지를 위해 타임스탬프 추가
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now(seoul_tz).strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 밀리초까지
                unique_filename = f"{name}_{timestamp}{ext}"
                
                # 실제 파일 저장
                full_dest = os.path.join(uploads_dir, unique_filename)
                uploaded_file.save(full_dest)
                
                # 데이터베이스에는 파일명만 저장 (상대 경로)
                file_paths.append(unique_filename)
        
        with get_db() as cx:
            # 기존 제출 삭제
            existing_submission = cx.execute(
                "SELECT file_paths FROM submissions WHERE user_id=? AND assignment_title=? AND IFNULL(category,'')=IFNULL(?, '')",
                (session.get("uid"), title, category),
            ).fetchone()
            
            if existing_submission and existing_submission[0]:
                try:
                    old_file_paths = json.loads(existing_submission[0])
                    for old_file in old_file_paths:
                        old_file_path = os.path.join(uploads_dir, old_file)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                except:
                    pass  # 파일 삭제 실패해도 계속 진행
            
            # 기존 제출 삭제
            cx.execute(
                "DELETE FROM submissions WHERE user_id=? AND assignment_title=? AND IFNULL(category,'')=IFNULL(?, '')",
                (session.get("uid"), title, category),
            )
            
            # 새 제출 추가
            seoul_time = datetime.now(seoul_tz).isoformat()
            cx.execute(
                "INSERT INTO submissions (user_id, name, assignment_title, category, text_content, file_paths, created_at) VALUES (?,?,?,?,?,?,?)",
                (session.get("uid"), session.get("name"), title, category, text_content, json.dumps(file_paths), seoul_time),
            )
        
        flash("과제가 수정되었습니다.", "success")
        
        email_subject = f"{session.get('name')} - {title} 수정 제출"
        body_lines = [
            f"제출자: {session.get('name')}",
            f"과제명: {title}",
            f"카테고리: {category or '없음'}",
            f"수정 제출 시간: {datetime.now(seoul_tz).strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "[수정된 제출 내용]",
            text_content if text_content else "(텍스트 없음)",
        ]
        
        if file_paths:
            body_lines.extend([
                "",
                "[첨부파일]",
                f"파일 개수: {len(file_paths)}개"
            ])
            for file_path in file_paths:
                body_lines.append(f"- {os.path.basename(file_path)}")
        
        try:
            send_admin_email(subject=email_subject, body="\n".join(body_lines), attachments=None)
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
            assignments_rows = cx.execute("SELECT id, title, due, description, category, file_path, file_paths FROM assignments ORDER BY id DESC").fetchall()
        def is_overdue(due_str: str) -> bool:
            if not due_str:
                return False
            try:
                from zoneinfo import ZoneInfo
                seoul = ZoneInfo("Asia/Seoul")
                now_local = datetime.now(seoul_tz)
            except Exception:
                seoul = None
                now_local = datetime.now(seoul_tz)
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
        user_interests = []
        if session.get("uid"):
            with get_db() as cx:
                user_row = cx.execute("SELECT interests FROM users WHERE id=?", (session.get("uid"),)).fetchone()
                if user_row and user_row['interests']:
                    try:
                        user_interests = json.loads(user_row['interests'])
                    except:
                        user_interests = []
        
        # 분야별 제출 통계 데이터 생성 (GitHub 잔디 스타일)
        category_stats = {}
        categories = ['unity', 'ml', 'dl', 'web']
        
        for category in categories:
            # 해당 분야의 과제 수
            category_assignments = [a for a in assignments if a.get('category') == category]
            total_assignments = len(category_assignments)
            
            # 해당 분야의 제출한 과제 수
            submitted_assignments = [a for a in category_assignments if a.get('submitted_at')]
            submitted_count = len(submitted_assignments)
            
            # 제출률 계산
            submission_rate = (submitted_count / total_assignments * 100) if total_assignments > 0 else 0
            
            # 제출 내역이 있는 경우만 표시
            if submitted_count > 0:
                category_stats[category] = {
                    'total': total_assignments,
                    'submitted': submitted_count,
                    'rate': round(submission_rate, 1),
                    'assignments': category_assignments
                }
        
        return render_template("learn.html", materials=materials, assignments=assignments, user_interests=user_interests, category_stats=category_stats)

    @app.route("/api/interests", methods=["GET", "POST"])
    def user_interests():
        if not session.get("uid"):
            return {"error": "로그인이 필요합니다."}, 401
        
        if request.method == "GET":
            with get_db() as cx:
                user_row = cx.execute("SELECT interests FROM users WHERE id=?", (session.get("uid"),)).fetchone()
                if user_row and user_row['interests']:
                    try:
                        interests = json.loads(user_row['interests'])
                    except:
                        interests = []
                else:
                    interests = []
            return {"interests": interests}
        
        elif request.method == "POST":
            data = request.get_json()
            interests = data.get("interests", [])
            
            if not isinstance(interests, list):
                return {"error": "관심 분야는 배열 형태여야 합니다."}, 400
            
            valid_interests = ["unity", "ml", "dl", "web"]
            for interest in interests:
                if interest not in valid_interests:
                    return {"error": f"유효하지 않은 분야: {interest}"}, 400
            with get_db() as cx:
                cx.execute("UPDATE users SET interests = ? WHERE id = ?", 
                          (json.dumps(interests), session.get("uid")))
                cx.commit()
            
            return {"success": True, "interests": interests}

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
            a = cx.execute("SELECT id, title, due, description, category, file_path, file_paths FROM assignments WHERE id=?", (item_id,)).fetchone()
        if not a:
            return redirect(url_for("learn"))
        a = dict(a)
        def is_overdue(due_str: str) -> bool:
            if not due_str:
                return False
            try:
                from zoneinfo import ZoneInfo
                seoul = ZoneInfo("Asia/Seoul")
                now_local = datetime.now(seoul_tz)
            except Exception:
                seoul = None
                now_local = datetime.now(seoul_tz)
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
        submission_text = None
        if session.get("uid"):
            with get_db() as cx:
                row = cx.execute(
                    "SELECT created_at, text_content FROM submissions WHERE user_id=? AND assignment_title=? AND IFNULL(category,'')=IFNULL(?, '')",
                    (session.get("uid"), a["title"], a["category"]),
                ).fetchone()
            if row:
                submitted = True
                submitted_at = row["created_at"]
                submission_text = row["text_content"]
        return render_template("assignment_detail.html", a=a, submitted=submitted, submitted_at=submitted_at, overdue=overdue, submission_text=submission_text)

    @app.route("/assignment/<int:assignment_id>/download")
    def download_assignment_file(assignment_id: int):
        with get_db() as cx:
            assignment = cx.execute("SELECT file_path FROM assignments WHERE id=?", (assignment_id,)).fetchone()
            if not assignment or not assignment['file_path']:
                flash("파일을 찾을 수 없습니다.", "error")
                return redirect(url_for("learn"))
            
            file_path = assignment['file_path']
            if not os.path.exists(file_path):
                flash("파일이 존재하지 않습니다.", "error")
                return redirect(url_for("learn"))
            
            filename = os.path.basename(file_path)
            return send_from_directory(os.path.dirname(file_path), filename, as_attachment=True)
    
    @app.route("/assignment/file/<path:filename>")
    def download_assignment_file_by_path(filename: str):
        from urllib.parse import unquote
        
        # URL 디코딩
        decoded_filename = unquote(filename)
        
        # 보안을 위해 파일명 검증 (상대 경로만 허용)
        if '..' in decoded_filename or '/' in decoded_filename or '\\' in decoded_filename:
            flash("잘못된 파일명입니다.", "error")
            return redirect(url_for("learn"))
        
        # 실제 파일명 찾기
        actual_filename = None
        try:
            for f in os.listdir(uploads_dir):
                # 정확한 매칭
                if f == decoded_filename or f == filename:
                    actual_filename = f
                    break
                
                # 따옴표 제거 후 매칭
                clean_f = f.strip("'\"")
                if clean_f == decoded_filename or clean_f == filename:
                    actual_filename = f
                    break
                
                # 부분 매칭 (확장자 제외)
                base_name = decoded_filename.split('.')[0]
                if f.startswith(base_name) or clean_f.startswith(base_name):
                    actual_filename = f
                    break
                    
        except Exception as e:
            print(f"DEBUG: Error listing directory: {e}")
        
        if actual_filename:
            return send_from_directory(uploads_dir, actual_filename, as_attachment=True)
        else:
            flash("파일이 존재하지 않습니다.", "error")
            return redirect(url_for("learn"))
    
    @app.route("/assignment/preview/<path:filename>")
    def preview_assignment_file_by_path(filename: str):
        from urllib.parse import unquote
        
        # URL 디코딩
        decoded_filename = unquote(filename)
        
        print(f"DEBUG ASSIGNMENT: Original filename: {filename}")
        print(f"DEBUG ASSIGNMENT: Decoded filename: {decoded_filename}")
        
        # 보안을 위해 파일명 검증 (상대 경로만 허용)
        if '..' in decoded_filename or '/' in decoded_filename or '\\' in decoded_filename:
            return "잘못된 파일명입니다.", 404
        
        # 실제 파일명 찾기
        actual_filename = None
        try:
            for f in os.listdir(uploads_dir):
                print(f"DEBUG ASSIGNMENT: Checking file: {repr(f)}")
                
                # 정확한 매칭
                if f == decoded_filename or f == filename:
                    actual_filename = f
                    break
                
                # 따옴표 제거 후 매칭
                clean_f = f.strip("'\"")
                if clean_f == decoded_filename or clean_f == filename:
                    actual_filename = f
                    break
                
                # 부분 매칭 (확장자 제외)
                base_name = decoded_filename.split('.')[0]
                if f.startswith(base_name) or clean_f.startswith(base_name):
                    actual_filename = f
                    break
                    
        except Exception as e:
            print(f"DEBUG ASSIGNMENT: Error listing directory: {e}")
        
        if actual_filename:
            print(f"DEBUG ASSIGNMENT: Found actual filename: {actual_filename}")
            return send_from_directory(uploads_dir, actual_filename, as_attachment=False)
        else:
            print(f"DEBUG ASSIGNMENT: File not found, listing uploads directory:")
            try:
                for f in os.listdir(uploads_dir):
                    print(f"  - {repr(f)}")
            except Exception as e:
                print(f"  Error listing directory: {e}")
            return "파일이 존재하지 않습니다.", 404

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
            file_paths = []
            
            # 여러 파일 처리
            if 'files' in request.files:
                files = request.files.getlist('files')
                for file in files:
                    if file and file.filename and file.filename.strip():
                        # 한글 파일명 지원을 위해 secure_filename 대신 직접 처리
                        filename = file.filename
                        # 위험한 문자만 제거
                        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
                        
                        # 파일명 중복 방지를 위해 타임스탬프 추가
                        name, ext = os.path.splitext(filename)
                        timestamp = datetime.now(seoul_tz).strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 밀리초까지
                        unique_filename = f"{name}_{timestamp}{ext}"
                        
                        # 실제 파일 저장
                        full_file_path = os.path.join(uploads_dir, unique_filename)
                        file.save(full_file_path)
                        
                        # 데이터베이스에는 파일명만 저장 (상대 경로)
                        file_paths.append(unique_filename)
            
            with get_db() as cx:
                cx.execute("INSERT INTO assignments (title, due, description, category, file_paths) VALUES (?,?,?,?,?)",
                           (request.form.get("title"), request.form.get("due"), request.form.get("description"), request.form.get("category"), json.dumps(file_paths)))
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_assignment_form.html", item=None)

    @app.route("/admin/assignment/<int:item_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_assignment_edit(item_id: int):
        with get_db() as cx:
            item = cx.execute("SELECT id, title, due, description, category, file_path, file_paths FROM assignments WHERE id=?", (item_id,)).fetchone()
        if request.method == "POST":
            # 기존 파일 경로들 가져오기
            existing_file_paths = []
            if item['file_paths'] and item['file_paths'].strip():
                try:
                    existing_file_paths = json.loads(item['file_paths'])
                except:
                    existing_file_paths = []
            
            # 삭제할 파일들 처리
            remove_files = request.form.get('remove_files', '')
            if remove_files:
                files_to_remove = remove_files.split(',')
                for filename in files_to_remove:
                    if filename.strip():
                        # 실제 파일 삭제
                        full_file_path = os.path.join(uploads_dir, filename.strip())
                        if os.path.exists(full_file_path):
                            try:
                                os.remove(full_file_path)
                            except Exception:
                                pass
                        # 기존 파일 목록에서 제거
                        if filename.strip() in existing_file_paths:
                            existing_file_paths.remove(filename.strip())
            
            # 새 파일들 추가
            new_file_paths = []
            if 'files' in request.files:
                files = request.files.getlist('files')
                for file in files:
                    if file and file.filename and file.filename.strip():
                        # 한글 파일명 지원을 위해 secure_filename 대신 직접 처리
                        filename = file.filename
                        # 위험한 문자만 제거
                        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
                        
                        # 파일명 중복 방지를 위해 타임스탬프 추가
                        name, ext = os.path.splitext(filename)
                        timestamp = datetime.now(seoul_tz).strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 밀리초까지
                        unique_filename = f"{name}_{timestamp}{ext}"
                        
                        # 실제 파일 저장
                        full_file_path = os.path.join(uploads_dir, unique_filename)
                        file.save(full_file_path)
                        
                        # 데이터베이스에는 파일명만 저장 (상대 경로)
                        new_file_paths.append(unique_filename)
            
            # 최종 파일 목록 (기존 파일 + 새 파일)
            final_file_paths = existing_file_paths + new_file_paths
            
            with get_db() as cx:
                cx.execute("UPDATE assignments SET title=?, due=?, description=?, category=?, file_paths=? WHERE id=?",
                           (request.form.get("title"), request.form.get("due"), request.form.get("description"), request.form.get("category"), json.dumps(final_file_paths), item_id))
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_assignment_form.html", item=item)

    @app.route("/admin/assignment/<int:item_id>/delete", methods=["POST"])
    @admin_required
    def admin_assignment_delete(item_id: int):
        with get_db() as cx:
            assignment = cx.execute("SELECT file_path, file_paths FROM assignments WHERE id=?", (item_id,)).fetchone()
            
            # 기존 단일 파일 삭제
            if assignment and assignment['file_path'] and os.path.exists(assignment['file_path']):
                try:
                    os.remove(assignment['file_path'])
                except Exception:
                    pass
            
            # 여러 파일 삭제
            if assignment and assignment['file_paths']:
                try:
                    file_paths = json.loads(assignment['file_paths'])
                    for file_path in file_paths:
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except Exception:
                                pass
                except:
                    pass
            
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
                SELECT s.id, s.name, s.assignment_title, s.category, s.text_content, s.file_path, s.file_paths, s.created_at
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
                SELECT s.id, s.name, s.assignment_title, s.category, s.text_content, s.file_path, s.file_paths, s.created_at
                FROM submissions s
                WHERE s.id = ?
            """, (submission_id,)).fetchone()
            
            if not submission:
                flash("제출을 찾을 수 없습니다.", "info")
                return redirect(url_for("admin_dashboard"))
        
        return render_template("admin_submission_detail.html", submission=submission)

    @app.route("/admin/submission/<int:submission_id>/delete", methods=["POST"])
    @admin_required
    def admin_submission_delete(submission_id: int):
        with get_db() as cx:
            submission = cx.execute("SELECT id, file_path FROM submissions WHERE id=?", (submission_id,)).fetchone()
            if not submission:
                flash("제출을 찾을 수 없습니다.", "error")
                return redirect(url_for("admin_dashboard"))
            
            if submission['file_path'] and os.path.exists(submission['file_path']):
                try:
                    os.remove(submission['file_path'])
                except Exception:
                    pass
            
            cx.execute("DELETE FROM submissions WHERE id=?", (submission_id,))
            cx.commit()
            
        flash("제출이 삭제되었습니다.", "success")
        return redirect(url_for("admin_dashboard"))

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

    @app.route("/submission/file/<path:filename>")
    @admin_required
    def download_submission_file_by_path(filename: str):
        """제출 파일을 파일명으로 다운로드 (as attachment)"""
        from urllib.parse import unquote
        
        # URL 디코딩
        decoded_filename = unquote(filename)
        
        # 실제 파일명 찾기
        actual_filename = None
        try:
            for f in os.listdir(uploads_dir):
                # 정확한 매칭
                if f == decoded_filename or f == filename:
                    actual_filename = f
                    break
                
                # 따옴표 제거 후 매칭
                clean_f = f.strip("'\"")
                if clean_f == decoded_filename or clean_f == filename:
                    actual_filename = f
                    break
                
                # 부분 매칭 (확장자 제외)
                base_name = decoded_filename.split('.')[0]
                if f.startswith(base_name) or clean_f.startswith(base_name):
                    actual_filename = f
                    break
                    
        except Exception as e:
            print(f"DEBUG: Error listing directory: {e}")
        
        if actual_filename:
            return send_from_directory(uploads_dir, actual_filename, as_attachment=True)
        else:
            flash("파일을 찾을 수 없습니다.", "info")
            return redirect(url_for("admin_dashboard"))

    @app.route("/submission/preview/<path:filename>")
    @admin_required
    def preview_submission_file_by_path(filename: str):
        """제출 파일을 파일명으로 미리보기 (inline)"""
        from urllib.parse import unquote
        
        # URL 디코딩
        decoded_filename = unquote(filename)
        
        print(f"DEBUG: Original filename: {filename}")
        print(f"DEBUG: Decoded filename: {decoded_filename}")
        
        # 실제 파일명 찾기
        actual_filename = None
        try:
            for f in os.listdir(uploads_dir):
                print(f"DEBUG: Checking file: {repr(f)}")
                
                # 정확한 매칭
                if f == decoded_filename or f == filename:
                    actual_filename = f
                    break
                
                # 따옴표 제거 후 매칭
                clean_f = f.strip("'\"")
                if clean_f == decoded_filename or clean_f == filename:
                    actual_filename = f
                    break
                
                # 부분 매칭 (확장자 제외)
                base_name = decoded_filename.split('.')[0]
                if f.startswith(base_name) or clean_f.startswith(base_name):
                    actual_filename = f
                    break
                    
        except Exception as e:
            print(f"DEBUG: Error listing directory: {e}")
        
        if actual_filename:
            print(f"DEBUG: Found actual filename: {actual_filename}")
            return send_from_directory(uploads_dir, actual_filename, as_attachment=False)
        else:
            print(f"DEBUG: File not found, listing uploads directory:")
            try:
                for f in os.listdir(uploads_dir):
                    print(f"  - {repr(f)}")
            except Exception as e:
                print(f"  Error listing directory: {e}")
            flash("파일을 찾을 수 없습니다.", "info")
            return redirect(url_for("admin_dashboard"))

    @app.route("/admin/submission/<int:submission_id>/download-all")
    @admin_required
    def admin_submission_download_all(submission_id: int):
        """제출의 모든 파일을 ZIP으로 다운로드"""
        import zipfile
        import tempfile
        from io import BytesIO
        
        with get_db() as cx:
            submission = cx.execute("SELECT file_paths FROM submissions WHERE id=?", (submission_id,)).fetchone()
            
            if not submission or not submission['file_paths']:
                flash("파일을 찾을 수 없습니다.", "info")
                return redirect(url_for("admin_dashboard"))
            
            try:
                file_paths = json.loads(submission['file_paths'])
            except (json.JSONDecodeError, TypeError):
                flash("파일 정보를 읽을 수 없습니다.", "info")
                return redirect(url_for("admin_dashboard"))
            
            if not file_paths:
                flash("다운로드할 파일이 없습니다.", "info")
                return redirect(url_for("admin_dashboard"))
            
            # ZIP 파일 생성
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename in file_paths:
                    file_path = os.path.join(uploads_dir, filename)
                    if os.path.exists(file_path):
                        zip_file.write(file_path, filename)
            
            zip_buffer.seek(0)
            
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'submission_{submission_id}_files.zip'
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

    @app.route("/portfolios")
    def portfolios():
        """포트폴리오 목록 페이지 - 비회원도 접근 가능"""
        def get_grade(student_id):
            """student_id에서 학년 추출 - 5자리 학번의 맨 앞 숫자가 학년"""
            try:
                if student_id and len(str(student_id)) >= 1:
                    # 맨 앞 숫자가 학년
                    grade = int(str(student_id)[0])
                    # 1-3학년만 유효
                    if 1 <= grade <= 3:
                        return grade
            except Exception as e:
                pass
            return None
        
        with get_db() as cx:
            portfolios_data = cx.execute("""
                SELECT p.*, u.name, u.student_id
                FROM portfolios p
                JOIN users u ON p.user_id = u.id
                ORDER BY u.student_id ASC, u.name ASC
            """).fetchall()
        
        # 학년별로 그룹화
        portfolios_by_grade = {}
        for portfolio in portfolios_data:
            # 연락처 JSON 파싱
            contacts = []
            try:
                contacts_raw = portfolio['contacts'] if 'contacts' in portfolio.keys() else None
            except:
                contacts_raw = None
            
            if contacts_raw and str(contacts_raw).strip() and str(contacts_raw) != 'None':
                try:
                    contacts = json.loads(str(contacts_raw))
                    if not isinstance(contacts, list):
                        contacts = []
                except:
                    contacts = []
            
            portfolio_dict = dict(portfolio)
            portfolio_dict['contacts'] = contacts
            
            grade = get_grade(portfolio['student_id'])
            # 학년을 계산할 수 없거나 3학년 이상인 경우 0으로 처리
            if not grade:
                grade = 0  # 기타/알 수 없음
            if grade not in portfolios_by_grade:
                portfolios_by_grade[grade] = []
            portfolios_by_grade[grade].append(portfolio_dict)
        
        return render_template("portfolios.html", portfolios_by_grade=portfolios_by_grade)

    @app.route("/portfolio/<int:user_id>")
    def portfolio_detail(user_id):
        """포트폴리오 상세 페이지 - 비회원도 접근 가능"""
        with get_db() as cx:
            portfolio = cx.execute("""
                SELECT p.id, p.user_id, p.github_url, p.discord_id, p.contacts, p.bio, p.projects, 
                       p.created_at, p.updated_at, u.name, u.student_id
                FROM portfolios p
                JOIN users u ON p.user_id = u.id
                WHERE p.user_id = ?
            """, (user_id,)).fetchone()
            
            if not portfolio:
                flash("포트폴리오를 찾을 수 없습니다.", "error")
                return redirect(url_for("portfolios"))
            
            # 연락처 및 프로젝트 JSON 파싱
            contacts = []
            try:
                contacts_raw = portfolio['contacts'] if 'contacts' in portfolio.keys() else None
            except:
                contacts_raw = None
            
            if contacts_raw and str(contacts_raw).strip() and str(contacts_raw) != 'None':
                try:
                    contacts = json.loads(str(contacts_raw))
                    if not isinstance(contacts, list):
                        contacts = []
                except Exception as e:
                    contacts = []
            
            projects = []
            try:
                projects_raw = portfolio['projects'] if 'projects' in portfolio.keys() else None
            except:
                projects_raw = None
            
            if projects_raw and str(projects_raw).strip() and str(projects_raw) != 'None':
                try:
                    projects = json.loads(str(projects_raw))
                    if not isinstance(projects, list):
                        projects = []
                except:
                    projects = []
            
            portfolio_dict = dict(portfolio)
            portfolio_dict['contacts'] = contacts
            portfolio_dict['projects'] = projects
            
            # 본인 포트폴리오인지 확인
            is_owner = session.get('uid') == user_id
            
        return render_template("portfolio_detail.html", portfolio=portfolio_dict, is_owner=is_owner)

    @app.route("/portfolio/edit")
    def portfolio_edit():
        """포트폴리오 편집 페이지 - 로그인 필요"""
        if not session.get('uid'):
            flash("로그인이 필요합니다.", "info")
            return redirect(url_for('login'))
        
        user_id = session.get('uid')
        with get_db() as cx:
            portfolio = cx.execute("""
                SELECT p.id, p.user_id, p.github_url, p.discord_id, p.contacts, p.bio, p.projects, 
                       p.created_at, p.updated_at, u.name, u.student_id
                FROM portfolios p
                JOIN users u ON p.user_id = u.id
                WHERE p.user_id = ?
            """, (user_id,)).fetchone()
            
            # 연락처 및 프로젝트 JSON 파싱
            if portfolio:
                contacts = []
                try:
                    contacts_raw = portfolio['contacts'] if 'contacts' in portfolio.keys() else None
                except:
                    contacts_raw = None
                
                if contacts_raw and str(contacts_raw).strip() and str(contacts_raw) != 'None':
                    try:
                        contacts = json.loads(str(contacts_raw))
                        if not isinstance(contacts, list):
                            contacts = []
                    except:
                        contacts = []
                
                projects = []
                try:
                    projects_raw = portfolio['projects'] if 'projects' in portfolio.keys() else None
                except:
                    projects_raw = None
                
                if projects_raw and str(projects_raw).strip() and str(projects_raw) != 'None':
                    try:
                        projects = json.loads(str(projects_raw))
                        if not isinstance(projects, list):
                            projects = []
                    except:
                        projects = []
                
                portfolio_dict = dict(portfolio)
                portfolio_dict['contacts'] = contacts
                portfolio_dict['projects'] = projects
            else:
                portfolio_dict = None
            
        return render_template("portfolio_edit.html", portfolio=portfolio_dict)

    @app.route("/portfolio/update", methods=["POST"])
    def portfolio_update():
        """포트폴리오 업데이트 - 로그인 필요"""
        if not session.get('uid'):
            flash("로그인이 필요합니다.", "info")
            return redirect(url_for('login'))
        
        user_id = session.get('uid')
        bio = request.form.get('bio', '').strip()
        
        # 연락처 데이터 처리
        contact_types = request.form.getlist('contact_type[]')
        contact_values = request.form.getlist('contact_value[]')
        
        contacts = []
        for i in range(len(contact_types)):
            if contact_types[i].strip() and contact_values[i].strip():
                contacts.append({
                    'type': contact_types[i].strip(),
                    'value': contact_values[i].strip()
                })
        
        contacts_json = json.dumps(contacts, ensure_ascii=False)
        
        # 프로젝트 데이터 처리
        project_titles = request.form.getlist('project_title[]')
        project_descriptions = request.form.getlist('project_description[]')
        project_urls = request.form.getlist('project_url[]')
        
        projects = []
        for i in range(len(project_titles)):
            if project_titles[i].strip():
                projects.append({
                    'title': project_titles[i].strip(),
                    'description': project_descriptions[i].strip() if i < len(project_descriptions) else '',
                    'url': project_urls[i].strip() if i < len(project_urls) else ''
                })
        
        projects_json = json.dumps(projects, ensure_ascii=False)
        now = datetime.now(seoul_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        with get_db() as cx:
            # 기존 포트폴리오 확인
            existing = cx.execute("SELECT id FROM portfolios WHERE user_id = ?", (user_id,)).fetchone()
            
            if existing:
                # 업데이트
                cx.execute("""
                    UPDATE portfolios
                    SET contacts = ?, bio = ?, projects = ?, updated_at = ?
                    WHERE user_id = ?
                """, (contacts_json, bio, projects_json, now, user_id))
            else:
                # 새로 생성
                cx.execute("""
                    INSERT INTO portfolios (user_id, contacts, bio, projects, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, contacts_json, bio, projects_json, now, now))
            cx.commit()
        
        flash("포트폴리오가 저장되었습니다.", "success")
        return redirect(url_for('portfolio_detail', user_id=user_id))

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
        
        now = datetime.now(seoul_tz).strftime("%Y-%m-%d")
        
        urls = [
            {"loc": "https://infotherapy.kro.kr/", "changefreq": "daily", "priority": "1.0", "lastmod": now},
            {"loc": "https://infotherapy.kro.kr/activities", "changefreq": "weekly", "priority": "0.9", "lastmod": now},
            {"loc": "https://infotherapy.kro.kr/learn", "changefreq": "weekly", "priority": "0.8", "lastmod": now},
            {"loc": "https://infotherapy.kro.kr/portfolios", "changefreq": "weekly", "priority": "0.8", "lastmod": now},
            {"loc": "https://infotherapy.kro.kr/contact", "changefreq": "monthly", "priority": "0.6", "lastmod": now},
            {"loc": "https://infotherapy.kro.kr/terms", "changefreq": "yearly", "priority": "0.4", "lastmod": now},
            {"loc": "https://infotherapy.kro.kr/privacy", "changefreq": "yearly", "priority": "0.4", "lastmod": now},
        ]
        
        with get_db() as cx:
            # 포트폴리오 페이지 추가 (실제 수정 날짜 사용)
            portfolio_data = cx.execute("""
                SELECT DISTINCT p.user_id, 
                       COALESCE(p.updated_at, p.created_at, ?) as lastmod_date
                FROM portfolios p
            """, (now,)).fetchall()
            for portfolio in portfolio_data:
                # 날짜 형식 변환 (YYYY-MM-DD)
                lastmod = portfolio['lastmod_date']
                if lastmod:
                    try:
                        # 다양한 날짜 형식 처리
                        if 'T' in str(lastmod):
                            lastmod = str(lastmod).split('T')[0]
                        elif ' ' in str(lastmod):
                            lastmod = str(lastmod).split(' ')[0]
                        lastmod = lastmod[:10]  # YYYY-MM-DD 형식으로 제한
                    except:
                        lastmod = now
                else:
                    lastmod = now
                
                urls.append({
                    "loc": f"https://infotherapy.kro.kr/portfolio/{portfolio['user_id']}",
                    "changefreq": "monthly",
                    "priority": "0.7",
                    "lastmod": lastmod
                })
            
            # 학습 자료 추가 (date 컬럼 사용)
            materials = cx.execute("SELECT id, date FROM materials").fetchall()
            for material in materials:
                lastmod = material['date'] if material['date'] else now
                if lastmod:
                    try:
                        if 'T' in str(lastmod):
                            lastmod = str(lastmod).split('T')[0]
                        elif ' ' in str(lastmod):
                            lastmod = str(lastmod).split(' ')[0]
                        lastmod = lastmod[:10]
                    except:
                        lastmod = now
                else:
                    lastmod = now
                
                urls.append({
                    "loc": f"https://infotherapy.kro.kr/material/{material['id']}",
                    "changefreq": "monthly",
                    "priority": "0.7",
                    "lastmod": lastmod
                })
            
            # 과제 추가 (due 컬럼 사용, 없으면 오늘 날짜)
            assignments = cx.execute("SELECT id, due FROM assignments").fetchall()
            for assignment in assignments:
                lastmod = assignment['due'] if assignment['due'] else now
                if lastmod:
                    try:
                        if 'T' in str(lastmod):
                            lastmod = str(lastmod).split('T')[0]
                        elif ' ' in str(lastmod):
                            lastmod = str(lastmod).split(' ')[0]
                        lastmod = lastmod[:10]
                    except:
                        lastmod = now
                else:
                    lastmod = now
                
                urls.append({
                    "loc": f"https://infotherapy.kro.kr/assignment/{assignment['id']}",
                    "changefreq": "weekly",
                    "priority": "0.7",
                    "lastmod": lastmod
                })
        
        for url_data in urls:
            url_elem = ET.SubElement(root, "url")
            ET.SubElement(url_elem, "loc").text = url_data["loc"]
            ET.SubElement(url_elem, "lastmod").text = url_data.get("lastmod", now)
            ET.SubElement(url_elem, "changefreq").text = url_data["changefreq"]
            ET.SubElement(url_elem, "priority").text = url_data["priority"]
        
        xml_str = ET.tostring(root, encoding='unicode')
        return Response(xml_str, mimetype='application/xml')

    @app.route("/robots.txt")
    def robots_txt():
        return """User-agent: *
Allow: /
Allow: /activities
Allow: /learn
Allow: /portfolios
Allow: /contact
Allow: /terms
Allow: /privacy
Allow: /material/
Allow: /assignment/
Allow: /portfolio/

# Disallow admin and private areas
Disallow: /admin/
Disallow: /login
Disallow: /signup

# Sitemap
Sitemap: https://infotherapy.kro.kr/sitemap.xml
"""

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


