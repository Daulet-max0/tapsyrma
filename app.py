"""
Түркістан жоғары көп салалы қол өнер колледжі
Оқытушылар рейтингі сайты — Flask backend
"""
import os
import sys
import uuid
from datetime import datetime, timedelta
from functools import wraps

# Windows консолінде UTF-8 қолдауы (emoji, кирилл, қазақ әріптері)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import config
import db
import schema
import mailer


app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=60)

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)


# =========================================================================
# Алғашқы іске қосу — test пайдаланушылар үшін парольдерді орнату
# =========================================================================
def check_db_connection() -> None:
    """MySQL қосылымын тексеру — сәтсіз болса қате шығарады."""
    db.fetch_one("SELECT 1 AS ok")


def ensure_seed_passwords():
    """Әдепкі парольдерді PasswordHash кестесіне орнату (PLACEHOLDER жазылған болса)."""
    admin_hash = generate_password_hash("admin123")
    teacher_hash = generate_password_hash("teacher123")
    db.execute(
        "UPDATE Admins SET PasswordHash = ? WHERE PasswordHash LIKE 'PLACEHOLDER%'",
        (admin_hash,)
    )
    db.execute(
        "UPDATE Teachers SET PasswordHash = ? WHERE PasswordHash = 'PLACEHOLDER'",
        (teacher_hash,)
    )


def ensure_admin_email_column():
    """Admins кестесіне Email бағанын қосу (бар болмаса) + әдепкі email-ді толтыру."""
    col = db.fetch_one(
        """
        SELECT 1 AS ok FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = 'email'
        """,
        ("Admins",),
    )
    if not col:
        db.execute('ALTER TABLE "Admins" ADD COLUMN "Email" VARCHAR(100)')
    db.execute("""
        UPDATE Admins
        SET Email = 'admin@tapsyrma.kz'
        WHERE Username = 'admin' AND (Email IS NULL OR TRIM(Email) = '')
    """)


# =========================================================================
# Көмекшілер
# =========================================================================
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS


def save_upload(file_storage, subfolder: str = "") -> str:
    """Файлды static/uploads/<subfolder>/ ішіне сақтап, салыстырмалы жолды қайтарады."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    unique = f"{uuid.uuid4().hex}.{ext}"
    target_dir = os.path.join(config.UPLOAD_FOLDER, subfolder) if subfolder else config.UPLOAD_FOLDER
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, unique)
    file_storage.save(path)
    rel = os.path.join("uploads", subfolder, unique) if subfolder else os.path.join("uploads", unique)
    return rel.replace("\\", "/")


ADMIN_ROLE_LEVEL = {"moderator": 1, "admin": 2, "superadmin": 3}


def current_academic_year() -> str:
    """Қыркүйек—тамыз оқу жылы."""
    now = datetime.now()
    if now.month >= 9:
        return f"{now.year}-{now.year + 1}"
    return f"{now.year - 1}-{now.year}"


def admin_role_level() -> int:
    if session.get("role") != "admin":
        return 0
    return ADMIN_ROLE_LEVEL.get(session.get("admin_role", "admin"), 0)


def login_required(role: str = None, min_admin_role: str = "moderator"):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login_page"))
            if role == "teacher" and session.get("role") != "teacher":
                flash("Бұл бетке кіру рұқсат етілмеген", "error")
                return redirect(url_for("index"))
            if role == "admin":
                if session.get("role") != "admin":
                    flash("Бұл бетке кіру рұқсат етілмеген", "error")
                    return redirect(url_for("index"))
                need = ADMIN_ROLE_LEVEL.get(min_admin_role, 1)
                if admin_role_level() < need:
                    flash("Бұл әрекетке рұқсатыңыз жоқ", "error")
                    return redirect(url_for("admin_panel"))
            elif role and session.get("role") != role:
                flash("Бұл бетке кіру рұқсат етілмеген", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _notify_teacher_approved(achievement_id: int) -> None:
    row = db.fetch_one(
        """
        SELECT t.Email, a.Title FROM Achievements a
        INNER JOIN Teachers t ON a.TeacherId = t.TeacherId
        WHERE a.AchievementId = ?
        """,
        (achievement_id,),
    )
    if row and row.get("Email"):
        mailer.notify_achievement_approved(row["Email"], row.get("Title") or "Жетістік")


def log_audit(user_type: str, user_id: int, action: str, details: str = ""):
    try:
        db.execute(
            "INSERT INTO AuditLog (UserType, UserId, Action, Details, IpAddress) VALUES (?,?,?,?,?)",
            (user_type, user_id, action, details, request.remote_addr or "")
        )
    except Exception:
        pass


@app.context_processor
def inject_globals():
    """Шаблондарда қолжетімді жаһандық айнымалылар."""
    announcement = None
    try:
        schema.ensure_schema()
        if schema.get_setting("announcement_active") == "1":
            announcement = {
                "title": schema.get_setting("announcement_title"),
                "body": schema.get_setting("announcement_body"),
            }
    except Exception:
        pass
    return {
        "current_user": {
            "id": session.get("user_id"),
            "name": session.get("user_name"),
            "role": session.get("role"),
            "admin_role": session.get("admin_role"),
        },
        "now_year": datetime.now().year,
        "site_announcement": announcement,
        "academic_year": current_academic_year(),
    }


# =========================================================================
# БЕТТЕР — Негізгі беттер
# =========================================================================
@app.route("/")
def index():
    """Басты бет — барлық оқытушылар карточкалары + іздеу."""
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "score")

    query = "SELECT * FROM vw_TeacherRating WHERE COALESCE(IsBlocked, FALSE) = FALSE"
    params = ()
    if search:
        query += " AND (FullName LIKE ? OR Department LIKE ?)"
        params = (f"%{search}%", f"%{search}%")

    if sort == "name":
        query += " ORDER BY FullName ASC"
    elif sort == "rank":
        query += " ORDER BY RankPosition ASC"
    else:
        query += " ORDER BY TotalScore DESC, FullName ASC"

    teachers = db.fetch_all(query, params)

    # Топ-3 подиум
    top3 = db.fetch_all(
        "SELECT * FROM vw_TeacherRating ORDER BY TotalScore DESC, FullName ASC LIMIT 3"
    )

    stats = db.fetch_one("""
        SELECT
            (SELECT COUNT(*) FROM Teachers) AS TeachersCount,
            (SELECT COUNT(*) FROM Achievements WHERE IsApproved = TRUE) AS ApprovedCount,
            (SELECT COUNT(*) FROM Achievements WHERE IsApproved = FALSE AND IsRejected = FALSE) AS PendingCount,
            (SELECT COALESCE(MAX(TotalScore), 0) FROM Teachers) AS MaxScore
    """)

    teacher_of_year = None
    try:
        schema.ensure_schema()
        y = current_academic_year()
        tid = schema.get_setting(f"teacher_of_year_{y}", "")
        if tid.isdigit():
            teacher_of_year = db.fetch_one(
                "SELECT * FROM vw_TeacherRating WHERE TeacherId = ?", (int(tid),)
            )
    except Exception:
        pass

    return render_template("index.html",
                           teachers=teachers, top3=top3, stats=stats,
                           search=search, sort=sort,
                           teacher_of_year=teacher_of_year,
                           teacher_of_year_label=current_academic_year())


@app.route("/teacher/<int:teacher_id>")
def teacher_profile_public(teacher_id: int):
    """Қоғамдық оқытушы профилі."""
    teacher = db.fetch_one("SELECT * FROM vw_TeacherRating WHERE TeacherId = ?", (teacher_id,))
    if not teacher:
        abort(404)

    achievements = db.fetch_all("""
        SELECT a.*, at.TypeName, at.Category
        FROM Achievements a
        INNER JOIN AchievementTypes at ON a.TypeId = at.TypeId
        WHERE a.TeacherId = ? AND a.IsApproved = TRUE
        ORDER BY a.ApprovedAt DESC
    """, (teacher_id,))

    badges = db.fetch_all("""
        SELECT b.* FROM TeacherBadges tb
        INNER JOIN Badges b ON tb.BadgeId = b.BadgeId
        WHERE tb.TeacherId = ?
        ORDER BY b.MinScore ASC
    """, (teacher_id,))

    # Келесі badge
    next_badge = db.fetch_one("""
        SELECT * FROM Badges
        WHERE MinScore > (SELECT TotalScore FROM Teachers WHERE TeacherId = ?)
        ORDER BY MinScore ASC
        LIMIT 1
    """, (teacher_id,))

    reviews = db.fetch_all("""
        SELECT r.*, t.FullName AS ReviewerName, t.PhotoPath AS ReviewerPhoto
        FROM Reviews r
        LEFT JOIN Teachers t ON r.ReviewerId = t.TeacherId
        WHERE r.TeacherId = ?
        ORDER BY r.CreatedAt DESC
    """, (teacher_id,))

    return render_template("teacher_profile.html",
                           teacher=teacher, achievements=achievements,
                           badges=badges, next_badge=next_badge, reviews=reviews)


# =========================================================================
# АУТЕНТИФИКАЦИЯ
# =========================================================================
@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_submit():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "teacher")

    if not email or not password:
        flash("Email мен парольді енгізіңіз", "error")
        return redirect(url_for("login_page"))

    if role == "admin":
        # Админ email немесе қолданыстағы Username арқылы кіре алады
        user = db.fetch_one(
            "SELECT * FROM Admins WHERE LOWER(Email) = ? OR LOWER(Username) = ?",
            (email, email)
        )
        if user and check_password_hash(user["PasswordHash"], password):
            session.permanent = True
            session["user_id"] = user["AdminId"]
            session["user_name"] = user.get("FullName") or user["Username"]
            session["role"] = "admin"
            session["admin_role"] = (user.get("Role") or "admin").lower()
            log_audit("admin", user["AdminId"], "login", "success")
            return redirect(url_for("admin_panel"))
    else:
        user = db.fetch_one(
            "SELECT * FROM Teachers WHERE LOWER(Email) = ?",
            (email,)
        )
        if user and user.get("IsBlocked"):
            flash("Аккаунтыңыз уақытша бұғатталған. Әкімшіге хабарласыңыз.", "error")
            return redirect(url_for("login_page"))
        if user and check_password_hash(user["PasswordHash"], password):
            session.permanent = True
            session["user_id"] = user["TeacherId"]
            session["user_name"] = user["FullName"]
            session["role"] = "teacher"
            db.execute(
                "UPDATE Teachers SET LastLoginAt = NOW() WHERE TeacherId = ?",
                (user["TeacherId"],),
            )
            log_audit("teacher", user["TeacherId"], "login", "success")
            return redirect(url_for("teacher_profile"))

    flash("Email немесе пароль қате", "error")
    log_audit(role, None, "login_failed", email)
    return redirect(url_for("login_page"))


@app.route("/register", methods=["GET", "POST"])
def register_page():
    """Жария тіркелу жабық — оқытушыларды тек админ қосады."""
    flash("Жария тіркелу жабық. Аккаунтты админ «Оқытушыларды басқару» бөлімінен қосады.", "info")
    return redirect(url_for("login_page"))


@app.route("/logout")
def logout():
    if "user_id" in session:
        log_audit(session.get("role", ""), session.get("user_id"), "logout", "")
    session.clear()
    return redirect(url_for("index"))


# =========================================================================
# ОҚЫТУШЫ ПРОФИЛІ (жеке кабинет)
# =========================================================================
@app.route("/profile")
@login_required(role="teacher")
def teacher_profile():
    teacher_id = session["user_id"]
    teacher = db.fetch_one("SELECT * FROM vw_TeacherRating WHERE TeacherId = ?", (teacher_id,))
    achievement_types = db.fetch_all("SELECT * FROM AchievementTypes ORDER BY Score DESC")
    achievements = db.fetch_all("""
        SELECT a.*, at.TypeName, at.Category
        FROM Achievements a
        INNER JOIN AchievementTypes at ON a.TypeId = at.TypeId
        WHERE a.TeacherId = ?
        ORDER BY a.SubmittedAt DESC
    """, (teacher_id,))
    badges = db.fetch_all("""
        SELECT b.* FROM TeacherBadges tb
        INNER JOIN Badges b ON tb.BadgeId = b.BadgeId
        WHERE tb.TeacherId = ?
        ORDER BY b.MinScore ASC
    """, (teacher_id,))
    next_badge = db.fetch_one("""
        SELECT * FROM Badges
        WHERE MinScore > (SELECT TotalScore FROM Teachers WHERE TeacherId = ?)
        ORDER BY MinScore ASC
        LIMIT 1
    """, (teacher_id,))
    return render_template("profile.html",
                           teacher=teacher, achievement_types=achievement_types,
                           achievements=achievements, badges=badges, next_badge=next_badge)


@app.route("/achievement/add", methods=["POST"])
@login_required(role="teacher")
def add_achievement():
    teacher_id = session["user_id"]
    type_id = request.form.get("type_id")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not type_id or not title:
        flash("Атауы мен түрі міндетті", "error")
        return redirect(url_for("teacher_profile"))

    image_path = None
    if "image" in request.files:
        image_path = save_upload(request.files["image"], "achievements")

    db.execute("""
        INSERT INTO Achievements (TeacherId, TypeId, Title, Description, ImagePath, IsApproved, AcademicYear)
        VALUES (?, ?, ?, ?, ?, FALSE, ?)
    """, (teacher_id, type_id, title, description, image_path, current_academic_year()))

    log_audit("teacher", teacher_id, "achievement_submit", title)
    flash("Жетістік қабылданды, админ тексеруін күтіңіз", "success")
    return redirect(url_for("teacher_profile"))


@app.route("/achievement/delete/<int:achievement_id>", methods=["POST"])
@login_required(role="teacher")
def delete_own_achievement(achievement_id: int):
    teacher_id = session["user_id"]
    db.execute(
        "DELETE FROM Achievements WHERE AchievementId = ? AND TeacherId = ? AND IsApproved = FALSE",
        (achievement_id, teacher_id)
    )
    flash("Жетістік өшірілді", "success")
    return redirect(url_for("teacher_profile"))


@app.route("/profile/photo", methods=["POST"])
@login_required(role="teacher")
def update_photo():
    teacher_id = session["user_id"]
    if "photo" not in request.files:
        flash("Файл жоқ", "error")
        return redirect(url_for("teacher_profile"))
    rel = save_upload(request.files["photo"], "teachers")
    if not rel:
        flash("Файл форматы қолдау таппайды", "error")
        return redirect(url_for("teacher_profile"))
    db.execute("UPDATE Teachers SET PhotoPath = ? WHERE TeacherId = ?", (rel, teacher_id))
    flash("Фото жаңартылды", "success")
    return redirect(url_for("teacher_profile"))


# =========================================================================
# АДМИН ПАНЕЛІ
# =========================================================================
@app.route("/admin")
@login_required(role="admin", min_admin_role="moderator")
def admin_panel():
    pending = db.fetch_all("""
        SELECT a.*, at.TypeName, at.Score AS TypeScore, t.FullName, t.PhotoPath
        FROM Achievements a
        INNER JOIN AchievementTypes at ON a.TypeId = at.TypeId
        INNER JOIN Teachers t ON a.TeacherId = t.TeacherId
        WHERE a.IsApproved = FALSE AND a.IsRejected = FALSE
        ORDER BY a.SubmittedAt DESC
    """)

    recent = db.fetch_all("""
        SELECT a.*, at.TypeName, t.FullName
        FROM Achievements a
        INNER JOIN AchievementTypes at ON a.TypeId = at.TypeId
        INNER JOIN Teachers t ON a.TeacherId = t.TeacherId
        WHERE a.IsApproved = TRUE OR a.IsRejected = TRUE
        ORDER BY COALESCE(a.ApprovedAt, a.SubmittedAt) DESC
        LIMIT 20
    """)

    stats = db.fetch_one("""
        SELECT
            (SELECT COUNT(*) FROM Teachers) AS TeachersCount,
            (SELECT COUNT(*) FROM Achievements) AS TotalAch,
            (SELECT COUNT(*) FROM Achievements WHERE IsApproved = TRUE) AS ApprovedCount,
            (SELECT COUNT(*) FROM Achievements WHERE IsApproved = FALSE AND IsRejected = FALSE) AS PendingCount
    """)
    return render_template("admin.html", pending=pending, recent=recent, stats=stats)


@app.route("/admin/approve/<int:achievement_id>", methods=["POST"])
@login_required(role="admin", min_admin_role="moderator")
def admin_approve(achievement_id: int):
    db.call_proc("sp_ApproveAchievement", (achievement_id,))
    _notify_teacher_approved(achievement_id)
    log_audit("admin", session["user_id"], "approve_achievement", str(achievement_id))
    return jsonify({"status": "ok"})


@app.route("/admin/reject/<int:achievement_id>", methods=["POST"])
@login_required(role="admin", min_admin_role="moderator")
def admin_reject(achievement_id: int):
    if request.is_json:
        reason = (request.json or {}).get("reason", "")
    else:
        reason = request.form.get("reason", "")
    db.call_proc("sp_RejectAchievement", (achievement_id, reason or "Расталмады"))
    log_audit("admin", session["user_id"], "reject_achievement", str(achievement_id))
    return jsonify({"status": "ok"})


@app.route("/admin/approve-batch", methods=["POST"])
@login_required(role="admin", min_admin_role="moderator")
def admin_approve_batch():
    ids = request.json.get("ids", []) if request.is_json else request.form.getlist("ids[]")
    count = 0
    for aid in ids:
        try:
            aid = int(aid)
            db.call_proc("sp_ApproveAchievement", (aid,))
            _notify_teacher_approved(aid)
            count += 1
        except Exception:
            pass
    log_audit("admin", session["user_id"], "batch_approve", f"count={count}")
    return jsonify({"status": "ok", "approved": count})


@app.route("/admin/reject-batch", methods=["POST"])
@login_required(role="admin", min_admin_role="moderator")
def admin_reject_batch():
    data = request.json if request.is_json else request.form
    ids = (request.json or {}).get("ids", []) if request.is_json else request.form.getlist("ids[]")
    reason = (data.get("reason") if request.is_json else request.form.get("reason")) or "Жаппай қабылданбады"
    count = 0
    for aid in ids:
        try:
            db.call_proc("sp_RejectAchievement", (int(aid), reason))
            count += 1
        except Exception:
            pass
    log_audit("admin", session["user_id"], "batch_reject", f"count={count}")
    return jsonify({"status": "ok", "rejected": count})


@app.route("/admin/delete-batch", methods=["POST"])
@login_required(role="admin", min_admin_role="moderator")
def admin_delete_batch():
    ids = (request.json or {}).get("ids", []) if request.is_json else request.form.getlist("ids[]")
    count = 0
    for aid in ids:
        try:
            n = db.execute(
                """
                DELETE FROM Achievements
                WHERE AchievementId = ? AND IsApproved = FALSE AND IsRejected = FALSE
                """,
                (int(aid),),
            )
            if n:
                count += 1
        except Exception:
            pass
    log_audit("admin", session["user_id"], "batch_delete_pending", f"count={count}")
    return jsonify({"status": "ok", "deleted": count})


@app.route("/admin/teachers", methods=["GET", "POST"])
@login_required(role="admin", min_admin_role="admin")
def admin_teachers():
    schema.ensure_schema()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            full_name = request.form.get("full_name", "").strip()
            login = request.form.get("login", "").strip()
            password = request.form.get("password", "")
            department = request.form.get("department", "").strip()
            position = request.form.get("position", "").strip()
            email = request.form.get("email", "").strip()
            yearly_goal = request.form.get("yearly_goal", "").strip()
            yg = int(yearly_goal) if yearly_goal.isdigit() else None
            if not full_name or not login or not password:
                flash("Барлық негізгі өрістерді толтырыңыз", "error")
            else:
                try:
                    db.execute("""
                        INSERT INTO Teachers (FullName, Login, PasswordHash, Department, Position, Email, YearlyGoal)
                        VALUES (?,?,?,?,?,?,?)
                    """, (full_name, login, generate_password_hash(password), department, position, email, yg))
                    flash("Оқытушы қосылды", "success")
                    log_audit("admin", session["user_id"], "teacher_create", login)
                except Exception as exc:
                    flash(f"Қате: {exc}", "error")
        elif action == "block":
            tid = int(request.form.get("teacher_id"))
            db.execute("UPDATE Teachers SET IsBlocked = TRUE WHERE TeacherId = ?", (tid,))
            flash("Аккаунт бұғатталды", "success")
            log_audit("admin", session["user_id"], "teacher_block", str(tid))
        elif action == "unblock":
            tid = int(request.form.get("teacher_id"))
            db.execute("UPDATE Teachers SET IsBlocked = FALSE WHERE TeacherId = ?", (tid,))
            flash("Бұғат алынды", "success")
            log_audit("admin", session["user_id"], "teacher_unblock", str(tid))
        elif action == "set_goal":
            tid = int(request.form.get("teacher_id"))
            goal = request.form.get("yearly_goal", "").strip()
            yg = int(goal) if goal.isdigit() else None
            db.execute("UPDATE Teachers SET YearlyGoal = ? WHERE TeacherId = ?", (yg, tid))
            flash("Жылдық мақсат сақталды", "success")
        elif action == "delete" and admin_role_level() >= ADMIN_ROLE_LEVEL["superadmin"]:
            teacher_id = int(request.form.get("teacher_id"))
            try:
                db.execute("DELETE FROM Achievements WHERE TeacherId = ?", (teacher_id,))
                db.execute("DELETE FROM TeacherBadges WHERE TeacherId = ?", (teacher_id,))
                db.execute("DELETE FROM Reviews WHERE TeacherId = ? OR ReviewerId = ?", (teacher_id, teacher_id))
                db.execute("DELETE FROM Teachers WHERE TeacherId = ?", (teacher_id,))
                flash("Оқытушы өшірілді", "success")
                log_audit("admin", session["user_id"], "teacher_delete", str(teacher_id))
            except Exception as exc:
                flash(f"Қате: {exc}", "error")
        elif action == "delete":
            flash("Тек суперадмин өшіре алады", "error")
        elif action == "import_csv":
            f = request.files.get("csv_file")
            if not f or not f.filename:
                flash("CSV файл таңдаңыз", "error")
            else:
                import csv
                import io
                text = f.read().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(text), delimiter=";")
                if not reader.fieldnames:
                    reader = csv.DictReader(io.StringIO(text), delimiter=",")
                ok, err = 0, 0
                for row in reader:
                    fn = (row.get("FullName") or row.get("full_name") or row.get("Аты") or "").strip()
                    login = (row.get("Login") or row.get("login") or "").strip()
                    pwd = (row.get("Password") or row.get("password") or "teacher123").strip()
                    if not fn or not login:
                        err += 1
                        continue
                    try:
                        yg = row.get("YearlyGoal") or row.get("yearly_goal") or ""
                        yg_i = int(yg) if str(yg).isdigit() else None
                        db.execute("""
                            INSERT INTO Teachers (FullName, Login, PasswordHash, Department, Position, Email, YearlyGoal)
                            VALUES (?,?,?,?,?,?,?)
                        """, (
                            fn, login, generate_password_hash(pwd),
                            (row.get("Department") or row.get("department") or "").strip() or None,
                            (row.get("Position") or row.get("position") or "").strip() or None,
                            (row.get("Email") or row.get("email") or "").strip() or None,
                            yg_i,
                        ))
                        ok += 1
                    except Exception:
                        err += 1
                flash(f"Импорт: {ok} қосылды, {err} қате/өткізілді", "success" if ok else "warning")
                log_audit("admin", session["user_id"], "teacher_import_csv", f"ok={ok},err={err}")
        return redirect(url_for("admin_teachers"))

    teachers = db.fetch_all("SELECT * FROM vw_TeacherRating ORDER BY FullName")
    inactive = db.fetch_all("""
        SELECT t.*,
               COALESCE(
                   (SELECT MAX(a.SubmittedAt) FROM Achievements a WHERE a.TeacherId = t.TeacherId),
                   t.CreatedAt
               ) AS LastActivity
        FROM Teachers t
        WHERE COALESCE(
            (SELECT MAX(a.SubmittedAt) FROM Achievements a WHERE a.TeacherId = t.TeacherId),
            t.CreatedAt
        ) < NOW() - INTERVAL '30 days'
        ORDER BY LastActivity ASC
    """)
    return render_template(
        "admin_teachers.html",
        teachers=teachers,
        inactive=inactive,
        academic_year=current_academic_year(),
        is_superadmin=admin_role_level() >= ADMIN_ROLE_LEVEL["superadmin"],
    )


@app.route("/admin/teachers/template.csv")
@login_required(role="admin", min_admin_role="admin")
def admin_teachers_csv_template():
    from flask import Response
    body = "FullName;Login;Password;Department;Position;Email;YearlyGoal\n"
    body += "Айгүл Қасымова;aigul2;teacher123;Информатика;Оқытушы;aigul2@college.kz;30\n"
    return Response(body, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=oqytushylar_shablon.csv"})


@app.route("/admin/audit")
@login_required(role="admin", min_admin_role="moderator")
def admin_audit():
    schema.ensure_schema()
    logs = db.fetch_all("""
        SELECT * FROM AuditLog ORDER BY CreatedAt DESC LIMIT 500
    """)
    return render_template("admin_audit.html", logs=logs)


@app.route("/admin/analytics")
@login_required(role="admin", min_admin_role="moderator")
def admin_analytics():
    schema.ensure_schema()
    logins_day = db.fetch_all("""
        SELECT DATE(CreatedAt) AS D, COUNT(*) AS Cnt
        FROM AuditLog
        WHERE UserType = 'teacher' AND Action = 'login'
          AND CreatedAt >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(CreatedAt) ORDER BY D
    """)
    ach_day = db.fetch_all("""
        SELECT DATE(SubmittedAt) AS D, COUNT(*) AS Cnt
        FROM Achievements
        WHERE SubmittedAt >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(SubmittedAt) ORDER BY D
    """)
    logins_week = db.fetch_one("""
        SELECT COUNT(*) AS Cnt FROM AuditLog
        WHERE UserType = 'teacher' AND Action = 'login'
          AND CreatedAt >= NOW() - INTERVAL '7 days'
    """)
    ach_week = db.fetch_one("""
        SELECT COUNT(*) AS Cnt FROM Achievements
        WHERE SubmittedAt >= NOW() - INTERVAL '7 days'
    """)
    dept_ranking = db.fetch_all("""
        SELECT Department,
               SUM(TotalScore) AS DeptScore,
               COUNT(*) AS TeacherCount
        FROM Teachers
        WHERE Department IS NOT NULL AND TRIM(Department) <> ''
          AND COALESCE(IsBlocked, FALSE) = FALSE
        GROUP BY Department
        ORDER BY DeptScore DESC
    """)
    return render_template(
        "admin_analytics.html",
        logins_day=logins_day,
        ach_day=ach_day,
        logins_week=logins_week or {},
        ach_week=ach_week or {},
        dept_ranking=dept_ranking,
    )


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required(role="admin", min_admin_role="admin")
def admin_settings():
    schema.ensure_schema()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "save_scores":
            types = db.fetch_all("SELECT TypeId FROM AchievementTypes")
            for t in types:
                tid = t["TypeId"]
                val = request.form.get(f"score_{tid}", "").strip()
                if val.isdigit():
                    db.execute(
                        "UPDATE AchievementTypes SET Score = ? WHERE TypeId = ?",
                        (int(val), tid),
                    )
            flash("Ұпайлар сақталды", "success")
            log_audit("admin", session["user_id"], "scores_update", "")
        elif action == "save_announcement":
            schema.set_setting("announcement_active", "1" if request.form.get("active") else "0")
            schema.set_setting("announcement_title", request.form.get("title", "").strip())
            schema.set_setting("announcement_body", request.form.get("body", "").strip())
            flash("Хабар жарияланды", "success")
        elif action == "test_email":
            to = request.form.get("test_to", "").strip()
            if mailer.send_email(to, "Ustaz Rating тест", "SMTP дұрыс жұмыс істейді ✅"):
                flash("Email жіберілді", "success")
            else:
                flash("Email жіберілмеді — SMTP баптауларын тексеріңіз", "error")
        elif action == "dept_goal":
            dept = request.form.get("department", "").strip()
            year = request.form.get("academic_year", "").strip() or current_academic_year()
            goal = request.form.get("dept_goal", "").strip()
            if dept and goal.isdigit():
                db.execute("""
                    INSERT INTO DepartmentGoals (Department, AcademicYear, YearlyGoal)
                    VALUES (?, ?, ?)
                    ON CONFLICT (Department, AcademicYear) DO UPDATE
                    SET YearlyGoal = EXCLUDED.YearlyGoal
                """, (dept, year, int(goal)))
                flash("Кафедра мақсаты қосылды", "success")
        return redirect(url_for("admin_settings"))

    types = db.fetch_all("SELECT * FROM AchievementTypes ORDER BY Category, Score DESC")
    dept_goals = db.fetch_all(
        "SELECT * FROM DepartmentGoals ORDER BY AcademicYear DESC, Department"
    )
    departments = [
        (r.get("Department") or r.get("department") or "")
        for r in db.fetch_all(
            "SELECT DISTINCT Department FROM Teachers "
            "WHERE Department IS NOT NULL AND TRIM(Department) <> '' ORDER BY Department"
        )
    ]
    return render_template(
        "admin_settings.html",
        types=types,
        announcement={
            "active": schema.get_setting("announcement_active") == "1",
            "title": schema.get_setting("announcement_title"),
            "body": schema.get_setting("announcement_body"),
        },
        mail_enabled=mailer.is_enabled(),
        dept_goals=dept_goals,
        departments=departments,
        academic_year=current_academic_year(),
    )


@app.route("/admin/roles", methods=["GET", "POST"])
@login_required(role="admin", min_admin_role="superadmin")
def admin_roles():
    schema.ensure_schema()
    if request.method == "POST":
        admin_id = int(request.form.get("admin_id"))
        role = request.form.get("role", "admin").lower()
        if role not in ADMIN_ROLE_LEVEL:
            role = "admin"
        db.execute('UPDATE Admins SET Role = ? WHERE AdminId = ?', (role, admin_id))
        flash("Рөл жаңартылды", "success")
        log_audit("admin", session["user_id"], "role_change", f"{admin_id}={role}")
        return redirect(url_for("admin_roles"))
    admins = db.fetch_all('SELECT AdminId, Username, FullName, Email, Role FROM Admins ORDER BY Username')
    return render_template("admin_roles.html", admins=admins, roles=ADMIN_ROLE_LEVEL.keys())


@app.route("/admin/teacher-of-year", methods=["GET", "POST"])
@login_required(role="admin", min_admin_role="moderator")
def admin_teacher_of_year():
    schema.ensure_schema()
    year = request.args.get("year", "").strip() or request.form.get("academic_year", "").strip() or current_academic_year()
    if request.method == "POST" and request.form.get("action") == "publish":
        tid = request.form.get("teacher_id", "").strip()
        if tid.isdigit():
            schema.set_setting(f"teacher_of_year_{year}", tid)
            t = db.fetch_one("SELECT FullName FROM Teachers WHERE TeacherId = ?", (int(tid),))
            flash(f"{year} жыл оқытушысы жарияланды: {t['FullName'] if t else tid}", "success")
            log_audit("admin", session["user_id"], "teacher_of_year", f"{year}={tid}")
        return redirect(url_for("admin_teacher_of_year", year=year))

    ranking = db.fetch_all("""
        SELECT t.TeacherId, t.FullName, t.Department, t.PhotoPath,
               COALESCE(SUM(a.Score), 0) AS YearScore,
               COUNT(a.AchievementId) AS YearAchCount
        FROM Teachers t
        LEFT JOIN Achievements a ON a.TeacherId = t.TeacherId
            AND a.IsApproved = TRUE AND a.AcademicYear = ?
        GROUP BY t.TeacherId, t.FullName, t.Department, t.PhotoPath
        ORDER BY YearScore DESC, t.FullName ASC
    """, (year,))

    published_id = schema.get_setting(f"teacher_of_year_{year}", "")
    published = None
    if published_id.isdigit():
        published = db.fetch_one("SELECT * FROM Teachers WHERE TeacherId = ?", (int(published_id),))

    years = db.fetch_all("""
        SELECT DISTINCT AcademicYear AS Y FROM Achievements
        WHERE AcademicYear IS NOT NULL AND TRIM(AcademicYear) <> ''
        ORDER BY Y DESC
    """)
    year_list = [r.get("Y") or r.get("y") for r in years if r.get("Y") or r.get("y")]
    if current_academic_year() not in year_list:
        year_list.insert(0, current_academic_year())

    return render_template(
        "admin_teacher_of_year.html",
        ranking=ranking,
        academic_year=year,
        years=year_list,
        published=published,
        published_id=published_id,
    )


# =========================================================================
# ҚОРЫТЫНДЫ — Барлық оқытушылардың жинаған ұпай қорытындысы
# =========================================================================
@app.route("/results")
def results_page():
    """Барлық оқытушылардың жалпы ұпайларын, категориялар бойынша
    талдауын және рейтингтегі орнын көрсететін жеке бет."""
    department = request.args.get("department", "").strip()

    base_query = "SELECT * FROM vw_TeacherRating"
    params = ()
    if department:
        base_query += " WHERE Department = ?"
        params = (department,)
    base_query += " ORDER BY TotalScore DESC, FullName ASC"
    teachers = db.fetch_all(base_query, params)

    # Категориялар бойынша әр оқытушының ұпай талдауы
    category_breakdown = db.fetch_all("""
        SELECT
            t.TeacherId,
            at.Category,
            SUM(a.Score) AS CategoryScore,
            COUNT(*)    AS CategoryCount
        FROM Achievements a
        INNER JOIN AchievementTypes at ON a.TypeId = at.TypeId
        INNER JOIN Teachers t          ON a.TeacherId = t.TeacherId
        WHERE a.IsApproved = TRUE
        GROUP BY t.TeacherId, at.Category
        ORDER BY t.TeacherId, CategoryScore DESC
    """)

    by_teacher = {}
    for row in category_breakdown:
        by_teacher.setdefault(row["TeacherId"], []).append(row)

    # Барлық бар категориялар (баған тақырыптары үшін)
    all_categories = [
        r["Category"] for r in db.fetch_all(
            "SELECT DISTINCT Category FROM AchievementTypes ORDER BY Category"
        )
    ]

    # Кафедралар тізімі (сүзгі үшін)
    departments = [
        r["Department"] for r in db.fetch_all(
            "SELECT DISTINCT Department FROM Teachers "
            "WHERE Department IS NOT NULL AND TRIM(Department) <> '' "
            "ORDER BY Department"
        )
    ]

    summary = db.fetch_one("""
        SELECT
            COUNT(*)                                AS TotalTeachers,
            COALESCE(SUM(TotalScore), 0)              AS SumScore,
            COALESCE(AVG(TotalScore::numeric), 0) AS AvgScore,
            COALESCE(MAX(TotalScore), 0)              AS MaxScore
        FROM Teachers
    """)

    top3 = db.fetch_all(
        "SELECT * FROM vw_TeacherRating ORDER BY TotalScore DESC, FullName ASC LIMIT 3"
    )

    return render_template(
        "results.html",
        teachers=teachers,
        by_teacher=by_teacher,
        all_categories=all_categories,
        departments=departments,
        department=department,
        summary=summary,
        top3=top3,
    )


@app.route("/results/export.csv")
def results_export_csv():
    """Қорытындыны CSV форматында жүктеу."""
    from io import StringIO
    import csv
    from flask import Response

    teachers = db.fetch_all(
        "SELECT * FROM vw_TeacherRating ORDER BY TotalScore DESC, FullName ASC"
    )

    buf = StringIO()
    buf.write("\ufeff")  # UTF-8 BOM Excel-де кирилл/қазақ әріптерін дұрыс ашуы үшін
    writer = csv.writer(buf, delimiter=";")
    writer.writerow([
        "Орны", "Аты-жөні", "Кафедра", "Қызметі",
        "Жалпы ұпай", "Расталған", "Күтілуде", "Орташа баға", "Пікірлер"
    ])
    for t in teachers:
        writer.writerow([
            t.get("RankPosition", ""),
            t.get("FullName", ""),
            t.get("Department", "") or "",
            t.get("Position", "") or "",
            t.get("TotalScore", 0),
            t.get("ApprovedCount", 0),
            t.get("PendingCount", 0),
            f"{float(t.get('AvgRating') or 0):.2f}",
            t.get("ReviewsCount", 0),
        ])

    return Response(
        buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=qorytyndy.csv"
        }
    )


# =========================================================================
# DASHBOARD
# =========================================================================
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/dashboard")
def api_dashboard():
    counters = db.fetch_one("""
        SELECT
            (SELECT COUNT(*) FROM Teachers) AS TeachersCount,
            (SELECT COUNT(*) FROM Achievements WHERE IsApproved = TRUE) AS ApprovedCount,
            (SELECT COUNT(*) FROM Achievements WHERE IsApproved = FALSE AND IsRejected = FALSE) AS PendingCount,
            (SELECT COALESCE(MAX(TotalScore), 0) FROM Teachers) AS MaxScore
    """)

    top10 = db.fetch_all("""
        SELECT FullName, TotalScore, PhotoPath
        FROM Teachers ORDER BY TotalScore DESC
        LIMIT 10
    """)

    by_category = db.fetch_all("""
        SELECT at.Category, COUNT(*) AS Cnt
        FROM Achievements a
        INNER JOIN AchievementTypes at ON a.TypeId = at.TypeId
        WHERE a.IsApproved = TRUE
        GROUP BY at.Category
        ORDER BY Cnt DESC
    """)

    months = db.fetch_all("""
        SELECT
            EXTRACT(MONTH FROM ApprovedAt)::int AS M,
            EXTRACT(YEAR FROM ApprovedAt)::int AS Y,
            COUNT(*) AS Cnt
        FROM Achievements
        WHERE IsApproved = TRUE AND ApprovedAt >= NOW() - INTERVAL '11 months'
        GROUP BY EXTRACT(YEAR FROM ApprovedAt), EXTRACT(MONTH FROM ApprovedAt)
        ORDER BY Y, M
    """)

    return jsonify({
        "counters": counters,
        "top10": top10,
        "by_category": by_category,
        "months": months
    })


# =========================================================================
# ДЕРЕКТЕР API — іздеу үшін (live search)
# =========================================================================
@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    results = db.fetch_all("""
        SELECT TeacherId, FullName, Department, TotalScore, PhotoPath
        FROM Teachers
        WHERE FullName LIKE ? OR Department LIKE ?
        ORDER BY TotalScore DESC
        LIMIT 8
    """, (f"%{q}%", f"%{q}%"))
    return jsonify(results)


# =========================================================================
# КОММЕНТАРИЙ / РЕЙТИНГ
# =========================================================================
@app.route("/review/<int:teacher_id>", methods=["POST"])
@login_required(role="teacher")
def add_review(teacher_id: int):
    reviewer_id = session["user_id"]
    if reviewer_id == teacher_id:
        flash("Өзіңізге баға бере алмайсыз", "error")
        return redirect(url_for("teacher_profile_public", teacher_id=teacher_id))
    stars = int(request.form.get("stars", 5))
    comment = request.form.get("comment", "").strip()
    db.execute("""
        INSERT INTO Reviews (TeacherId, ReviewerId, Stars, Comment)
        VALUES (?,?,?,?)
    """, (teacher_id, reviewer_id, max(1, min(5, stars)), comment))
    flash("Пікіріңіз қосылды", "success")
    return redirect(url_for("teacher_profile_public", teacher_id=teacher_id))


# =========================================================================
# Uploads бетке шығару (қауіпсіз)
# =========================================================================
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(config.UPLOAD_FOLDER, filename)


# =========================================================================
# Қателерді өңдеу
# =========================================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html", error=str(e)), 500


@app.errorhandler(Exception)
def handle_db_error(e):
    """Дерекқор қателерін көркем көрсету."""
    import psycopg2
    if isinstance(e, (psycopg2.InterfaceError, psycopg2.OperationalError, psycopg2.DatabaseError)):
        msg = str(e)
        hint = (
            "PostgreSQL (Railway): <code>DATABASE_URL</code> орнатылғанын тексеріңіз, "
            "содан Bash-та <code>python setup_db.py</code> орындаңыз."
        )
        if "does not exist" in msg.lower() or "relation" in msg.lower():
            hint = "Кестелер жоқ. Railway Bash: <code>python setup_db.py</code> орындаңыз."
        elif "connection" in msg.lower() or "could not connect" in msg.lower():
            hint = (
                "PostgreSQL-ге қосылу сәтсіз. Railway → PostgreSQL plugin, "
                "<code>DATABASE_URL</code> айнымалысы."
            )
        return render_template("db_error.html", error=msg, hint=hint), 500
    # Басқа қателер үшін әдепкі
    import traceback
    traceback.print_exc()
    return render_template("500.html", error=str(e)), 500


# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  Түркістан колледжі — Оқытушылар рейтингі")
    print("=" * 60)
    try:
        check_db_connection()
        print("✅ PostgreSQL байланысы сәтті")
        try:
            schema.ensure_schema()
            ensure_admin_email_column()
            ensure_seed_passwords()
            print("✅ Әдепкі парольдер орнатылды")
            print("   Админ:   admin@tapsyrma.kz / admin123")
            print("   Оқытушы: <email> / teacher123")
        except Exception as e:
            print(f"⚠️  Миграция/парольдер: {e}")
            print("   python setup_db.py орындаңыз.")
    except Exception as e:
        print(f"⚠️  PostgreSQL қосылмады: {e}")
        print("   Railway: PostgreSQL + DATABASE_URL, содан setup_db.py")
        print("   → DEPLOY_RAILWAY.md")
        print(f"   URL: {config.DATABASE_URL.split('@')[-1] if '@' in config.DATABASE_URL else '...'}")

    print("=" * 60)
    print("  🚀 Сервер: http://localhost:5000  (интерфейс ашылады)")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
