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


def generate_unique_login_from_email(email: str) -> str:
    """Email-ден бірегей Login жасау: `aigul@mail.kz` → `aigul`, `aigul1`..."""
    import re as _re
    base = (email or "").split("@")[0].lower()
    base = _re.sub(r"[^a-z0-9_.]", "", base) or "user"
    if len(base) < 3:
        base = (base + "user")[:8]
    candidate = base
    i = 1
    while db.fetch_one("SELECT TeacherId FROM Teachers WHERE Login = ?", (candidate,)):
        candidate = f"{base}{i}"
        i += 1
    return candidate


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


def login_required(role: str = None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login_page"))
            if role and session.get("role") != role:
                flash("Бұл бетке кіру рұқсат етілмеген", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


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
    return {
        "current_user": {
            "id": session.get("user_id"),
            "name": session.get("user_name"),
            "role": session.get("role"),
        },
        "now_year": datetime.now().year,
    }


# =========================================================================
# БЕТТЕР — Негізгі беттер
# =========================================================================
@app.route("/")
def index():
    """Басты бет — барлық оқытушылар карточкалары + іздеу."""
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "score")

    query = "SELECT * FROM vw_TeacherRating"
    params = ()
    if search:
        query += " WHERE FullName LIKE ? OR Department LIKE ?"
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

    return render_template("index.html",
                           teachers=teachers, top3=top3, stats=stats,
                           search=search, sort=sort)


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
            log_audit("admin", user["AdminId"], "login", "success")
            return redirect(url_for("admin_panel"))
    else:
        user = db.fetch_one(
            "SELECT * FROM Teachers WHERE LOWER(Email) = ?",
            (email,)
        )
        if user and check_password_hash(user["PasswordHash"], password):
            session.permanent = True
            session["user_id"] = user["TeacherId"]
            session["user_name"] = user["FullName"]
            session["role"] = "teacher"
            log_audit("teacher", user["TeacherId"], "login", "success")
            return redirect(url_for("teacher_profile"))

    flash("Email немесе пароль қате", "error")
    log_audit(role, None, "login_failed", email)
    return redirect(url_for("login_page"))


@app.route("/register", methods=["GET"])
def register_page():
    """Оқытушы өзін-өзі тіркейтін бет."""
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_submit():
    """Жаңа оқытушы аккаунтын email арқылы жасау."""
    import re

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")
    department = request.form.get("department", "").strip()
    position = request.form.get("position", "").strip()

    if not full_name or len(full_name) < 3:
        flash("Аты-жөніңізді дұрыс жазыңыз (кем дегенде 3 таңба)", "error")
        return redirect(url_for("register_page"))

    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        flash("Жарамды email енгізіңіз", "error")
        return redirect(url_for("register_page"))

    if not password or len(password) < 6:
        flash("Құпия сөз кем дегенде 6 таңбадан тұруы керек", "error")
        return redirect(url_for("register_page"))

    if password != password_confirm:
        flash("Құпия сөздер сәйкес келмейді", "error")
        return redirect(url_for("register_page"))

    # Бірегейлікті тексеру (email)
    email_taken = db.fetch_one(
        "SELECT TeacherId FROM Teachers WHERE LOWER(Email) = ?", (email,)
    )
    if email_taken:
        flash("Бұл email бұрыннан тіркелген", "error")
        return redirect(url_for("register_page"))

    admin_email_taken = db.fetch_one(
        "SELECT AdminId FROM Admins WHERE LOWER(Email) = ?", (email,)
    )
    if admin_email_taken:
        flash("Бұл email бос емес", "error")
        return redirect(url_for("register_page"))

    # Email-ден бірегей Login автогенерацияланады
    login = generate_unique_login_from_email(email)

    try:
        db.execute("""
            INSERT INTO Teachers (FullName, Login, PasswordHash, Department, Position, Email, TotalScore)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (
            full_name,
            login,
            generate_password_hash(password),
            department or None,
            position or None,
            email,
        ))
    except Exception as exc:
        flash(f"Тіркелу кезінде қате: {exc}", "error")
        return redirect(url_for("register_page"))

    # Жаңа тіркелген оқытушыны бірден жүйеге кіргіземіз
    new_user = db.fetch_one(
        "SELECT * FROM Teachers WHERE LOWER(Email) = ?", (email,)
    )
    if new_user:
        session.permanent = True
        session["user_id"] = new_user["TeacherId"]
        session["user_name"] = new_user["FullName"]
        session["role"] = "teacher"
        log_audit("teacher", new_user["TeacherId"], "register", email)
        flash("Аккаунтыңыз сәтті жасалды! Қош келдіңіз 🎉", "success")
        return redirect(url_for("teacher_profile"))

    flash("Тіркелу сәтті, енді жүйеге кіріңіз", "success")
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
        INSERT INTO Achievements (TeacherId, TypeId, Title, Description, ImagePath, IsApproved)
        VALUES (?, ?, ?, ?, ?, FALSE)
    """, (teacher_id, type_id, title, description, image_path))

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
@login_required(role="admin")
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
@login_required(role="admin")
def admin_approve(achievement_id: int):
    db.call_proc("sp_ApproveAchievement", (achievement_id,))
    log_audit("admin", session["user_id"], "approve_achievement", str(achievement_id))
    return jsonify({"status": "ok"})


@app.route("/admin/reject/<int:achievement_id>", methods=["POST"])
@login_required(role="admin")
def admin_reject(achievement_id: int):
    if request.is_json:
        reason = (request.json or {}).get("reason", "")
    else:
        reason = request.form.get("reason", "")
    db.call_proc("sp_RejectAchievement", (achievement_id, reason or "Расталмады"))
    log_audit("admin", session["user_id"], "reject_achievement", str(achievement_id))
    return jsonify({"status": "ok"})


@app.route("/admin/approve-batch", methods=["POST"])
@login_required(role="admin")
def admin_approve_batch():
    ids = request.json.get("ids", []) if request.is_json else request.form.getlist("ids[]")
    count = 0
    for aid in ids:
        try:
            db.call_proc("sp_ApproveAchievement", (int(aid),))
            count += 1
        except Exception:
            pass
    log_audit("admin", session["user_id"], "batch_approve", f"count={count}")
    return jsonify({"status": "ok", "approved": count})


@app.route("/admin/teachers", methods=["GET", "POST"])
@login_required(role="admin")
def admin_teachers():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            full_name = request.form.get("full_name", "").strip()
            login = request.form.get("login", "").strip()
            password = request.form.get("password", "")
            department = request.form.get("department", "").strip()
            position = request.form.get("position", "").strip()
            email = request.form.get("email", "").strip()
            if not full_name or not login or not password:
                flash("Барлық негізгі өрістерді толтырыңыз", "error")
            else:
                try:
                    db.execute("""
                        INSERT INTO Teachers (FullName, Login, PasswordHash, Department, Position, Email)
                        VALUES (?,?,?,?,?,?)
                    """, (full_name, login, generate_password_hash(password), department, position, email))
                    flash("Оқытушы қосылды", "success")
                except Exception as exc:
                    flash(f"Қате: {exc}", "error")
        elif action == "delete":
            teacher_id = int(request.form.get("teacher_id"))
            try:
                db.execute("DELETE FROM Achievements WHERE TeacherId = ?", (teacher_id,))
                db.execute("DELETE FROM TeacherBadges WHERE TeacherId = ?", (teacher_id,))
                db.execute("DELETE FROM Reviews WHERE TeacherId = ? OR ReviewerId = ?", (teacher_id, teacher_id))
                db.execute("DELETE FROM Teachers WHERE TeacherId = ?", (teacher_id,))
                flash("Оқытушы өшірілді", "success")
            except Exception as exc:
                flash(f"Қате: {exc}", "error")
        return redirect(url_for("admin_teachers"))

    teachers = db.fetch_all("SELECT * FROM vw_TeacherRating ORDER BY FullName")
    return render_template("admin_teachers.html", teachers=teachers)


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
            "содан Bash-та <code>python setup_db.py</code>. "
            "<code>DEPLOY_RAILWAY.md</code> қараңыз."
        )
        if "does not exist" in msg.lower() or "relation" in msg.lower():
            hint = (
                "Кестелер жоқ. Railway Bash: <code>python setup_db.py</code> "
                "(<code>DEPLOY_RAILWAY.md</code>)"
            )
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
