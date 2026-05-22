"""
DB миграциялары — бар қолданбада жаңа бағандар/кестелерді қосу.
"""
import db

_MIGRATIONS_DONE = False


def _column_exists(table: str, column: str) -> bool:
    row = db.fetch_one(
        """
        SELECT 1 AS ok FROM information_schema.columns
        WHERE table_schema = 'public' AND LOWER(table_name) = LOWER(%s)
          AND LOWER(column_name) = LOWER(%s)
        """,
        (table, column),
    )
    return bool(row)


def _table_exists(table: str) -> bool:
    row = db.fetch_one(
        """
        SELECT 1 AS ok FROM information_schema.tables
        WHERE table_schema = 'public' AND LOWER(table_name) = LOWER(%s)
        """,
        (table,),
    )
    return bool(row)


def ensure_schema(force: bool = False) -> None:
    global _MIGRATIONS_DONE
    if _MIGRATIONS_DONE and not force:
        if _table_exists("SiteSettings") and _table_exists("DepartmentGoals"):
            return
        _MIGRATIONS_DONE = False

    # Жаңа кестелер алдымен (кейінгі сұраулар сәтсіз болмауы үшін)
    if not _table_exists("SiteSettings"):
        db.execute("""
            CREATE TABLE "SiteSettings" (
                "SettingKey"   VARCHAR(100) PRIMARY KEY,
                "SettingValue" TEXT,
                "UpdatedAt"    TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)

    if not _table_exists("DepartmentGoals"):
        db.execute("""
            CREATE TABLE "DepartmentGoals" (
                "GoalId"       SERIAL PRIMARY KEY,
                "Department"   VARCHAR(200) NOT NULL,
                "AcademicYear" VARCHAR(20) NOT NULL,
                "YearlyGoal"   INT NOT NULL DEFAULT 0,
                UNIQUE ("Department", "AcademicYear")
            )
        """)

    if not _column_exists("Teachers", "IsBlocked"):
        db.execute('ALTER TABLE "Teachers" ADD COLUMN "IsBlocked" BOOLEAN NOT NULL DEFAULT FALSE')
    if not _column_exists("Teachers", "YearlyGoal"):
        db.execute('ALTER TABLE "Teachers" ADD COLUMN "YearlyGoal" INT')
    if not _column_exists("Teachers", "LastLoginAt"):
        db.execute('ALTER TABLE "Teachers" ADD COLUMN "LastLoginAt" TIMESTAMP')
    if not _column_exists("Teachers", "Bio"):
        db.execute('ALTER TABLE "Teachers" ADD COLUMN "Bio" VARCHAR(2000)')
    if not _column_exists("Teachers", "Phone"):
        db.execute('ALTER TABLE "Teachers" ADD COLUMN "Phone" VARCHAR(50)')

    if not _column_exists("Admins", "Role"):
        db.execute(
            """ALTER TABLE "Admins" ADD COLUMN "Role" VARCHAR(30) NOT NULL DEFAULT 'superadmin'"""
        )
    db.execute(
        """UPDATE "Admins" SET "Role" = 'superadmin'
           WHERE "Role" IS NULL OR TRIM("Role") = ''"""
    )

    if not _column_exists("Achievements", "AcademicYear"):
        db.execute('ALTER TABLE "Achievements" ADD COLUMN "AcademicYear" VARCHAR(20)')

    if _column_exists("Teachers", "IsBlocked"):
        db.execute('DROP VIEW IF EXISTS "vw_TeacherRating"')
        db.execute("""
            CREATE VIEW "vw_TeacherRating" AS
            SELECT
                t."TeacherId", t."FullName", t."Login", t."Department", t."Position",
                t."Email", t."PhotoPath", t."TotalScore", t."IsBlocked", t."YearlyGoal",
                t."LastLoginAt", t."Bio", t."Phone",
                (SELECT COUNT(*) FROM "Achievements" a
                 WHERE a."TeacherId" = t."TeacherId" AND a."IsApproved" = TRUE) AS "ApprovedCount",
                (SELECT COUNT(*) FROM "Achievements" a
                 WHERE a."TeacherId" = t."TeacherId"
                   AND a."IsApproved" = FALSE AND a."IsRejected" = FALSE) AS "PendingCount",
                (SELECT COUNT(*) FROM "Achievements" a
                 WHERE a."TeacherId" = t."TeacherId" AND a."IsRejected" = TRUE) AS "RejectedCount",
                COALESCE((SELECT AVG("Stars"::numeric) FROM "Reviews" r
                    WHERE r."TeacherId" = t."TeacherId"), 0) AS "AvgRating",
                (SELECT COUNT(*) FROM "Reviews" r WHERE r."TeacherId" = t."TeacherId") AS "ReviewsCount",
                DENSE_RANK() OVER (ORDER BY t."TotalScore" DESC) AS "RankPosition"
            FROM "Teachers" t
        """)

    _MIGRATIONS_DONE = True


def get_setting(key: str, default: str = "") -> str:
    ensure_schema()
    row = db.fetch_one(
        'SELECT "SettingValue" FROM "SiteSettings" WHERE "SettingKey" = %s',
        (key,),
    )
    if not row or row.get("SettingValue") is None:
        return default
    return str(row["SettingValue"])


def set_setting(key: str, value: str) -> None:
    ensure_schema()
    db.execute(
        """
        INSERT INTO "SiteSettings" ("SettingKey", "SettingValue", "UpdatedAt")
        VALUES (%s, %s, NOW())
        ON CONFLICT ("SettingKey") DO UPDATE
        SET "SettingValue" = EXCLUDED."SettingValue", "UpdatedAt" = NOW()
        """,
        (key, value),
    )
