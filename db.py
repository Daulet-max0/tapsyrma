"""
PostgreSQL байланыс қабаты (psycopg2 + DATABASE_URL).
"""
import re
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import config

# PostgreSQL-де кавычкасыз атаулар кіші әріпке түседі — шаблондар PascalCase күтеді
_IDENTIFIERS = sorted(
    [
        "vw_TeacherRating",
        "AchievementTypes", "Achievements", "TeacherBadges", "AuditLog",
        "Admins", "Teachers", "Badges", "Reviews", "Events",
        "AchievementId", "TeacherBadgeId", "ReviewId", "EventId", "LogId",
        "AdminId", "TeacherId", "TypeId", "BadgeId", "ReviewerId", "UserId",
        "PasswordHash", "FullName", "TypeName", "BadgeName", "RejectReason",
        "SubmittedAt", "ApprovedAt", "CreatedAt", "EventDate", "AwardedAt",
        "PhotoPath", "ImagePath", "IpAddress", "TotalScore", "MinScore",
        "IsApproved", "IsRejected", "Department", "Position", "Username",
        "Login", "Email", "Title", "Description", "Category", "Comment",
        "Stars", "Score", "Action", "Details", "UserType", "Icon", "Color",
        "ApprovedCount", "PendingCount", "RejectedCount", "AvgRating",
        "ReviewsCount", "RankPosition", "ReviewerName", "ReviewerPhoto",
        "TypeScore", "TeachersCount", "ApprovedCount", "PendingCount",
        "MaxScore", "SumScore", "AvgScore", "TotalTeachers", "TotalAch",
    ],
    key=len,
    reverse=True,
)


def _prepare_query(query: str) -> str:
    q = re.sub(r"\?", "%s", query)
    for name in _IDENTIFIERS:
        q = re.sub(rf"\b{re.escape(name)}\b", f'"{name}"', q)
    return q


def get_connection():
    return psycopg2.connect(config.DATABASE_URL)


@contextmanager
def cursor_ctx(commit: bool = False):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(cursor, row) -> dict:
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {col[0]: value for col, value in zip(cursor.description, row)}


def rows_to_dicts(cursor, rows) -> list:
    return [row_to_dict(cursor, r) for r in rows]


def fetch_all(query: str, params: tuple = ()) -> list:
    with cursor_ctx() as cur:
        cur.execute(_prepare_query(query), params)
        return rows_to_dicts(cur, cur.fetchall())


def fetch_one(query: str, params: tuple = ()) -> dict:
    with cursor_ctx() as cur:
        cur.execute(_prepare_query(query), params)
        return row_to_dict(cur, cur.fetchone())


def execute(query: str, params: tuple = ()) -> int:
    with cursor_ctx(commit=True) as cur:
        cur.execute(_prepare_query(query), params)
        return cur.rowcount


def execute_scalar(query: str, params: tuple = ()):
    with cursor_ctx(commit=True) as cur:
        cur.execute(_prepare_query(query), params)
        row = cur.fetchone()
        return row[0] if row else None


def insert_returning_id(query: str, params: tuple = (), id_column: str = "id") -> int:
    sql = _prepare_query(query)
    if "RETURNING" not in sql.upper():
        sql += f' RETURNING "{id_column}"'
    with cursor_ctx(commit=True) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[id_column] if row else None


def _approve_achievement(achievement_id: int) -> None:
    row = fetch_one(
        'SELECT "TypeId", "TeacherId" FROM "Achievements" WHERE "AchievementId" = %s',
        (achievement_id,),
    )
    if not row:
        return
    type_row = fetch_one(
        'SELECT "Score" FROM "AchievementTypes" WHERE "TypeId" = %s',
        (row["TypeId"],),
    )
    score = type_row["Score"] if type_row else 0
    execute(
        """
        UPDATE "Achievements"
        SET "IsApproved" = TRUE, "IsRejected" = FALSE, "Score" = %s,
            "ApprovedAt" = NOW(), "RejectReason" = NULL
        WHERE "AchievementId" = %s
        """,
        (score, achievement_id),
    )
    tid = row["TeacherId"]
    execute(
        """
        INSERT INTO "TeacherBadges" ("TeacherId", "BadgeId")
        SELECT %s, b."BadgeId" FROM "Badges" b
        WHERE b."MinScore" <= (SELECT "TotalScore" FROM "Teachers" WHERE "TeacherId" = %s)
        AND NOT EXISTS (
            SELECT 1 FROM "TeacherBadges" tb
            WHERE tb."TeacherId" = %s AND tb."BadgeId" = b."BadgeId"
        )
        """,
        (tid, tid, tid),
    )


def _reject_achievement(achievement_id: int, reason: str) -> None:
    execute(
        """
        UPDATE "Achievements"
        SET "IsRejected" = TRUE, "IsApproved" = FALSE, "Score" = 0,
            "RejectReason" = COALESCE(%s, 'Расталмады'), "ApprovedAt" = NOW()
        WHERE "AchievementId" = %s
        """,
        (reason, achievement_id),
    )


def call_proc(proc_name: str, params: tuple = ()) -> list:
    if proc_name == "sp_ApproveAchievement" and params:
        _approve_achievement(int(params[0]))
    elif proc_name == "sp_RejectAchievement" and params:
        reason = params[1] if len(params) > 1 else "Расталмады"
        _reject_achievement(int(params[0]), reason)
    return []
