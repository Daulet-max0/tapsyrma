"""
PostgreSQL дерекқорын орнату (Railway DATABASE_URL).

    python setup_db.py
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import psycopg2
import config
from werkzeug.security import generate_password_hash


def split_batches(sql: str) -> list:
    parts = re.split(r"^\s*--\s*BATCH\s*$", sql, flags=re.MULTILINE | re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def _using_local_default(url: str) -> bool:
    return "localhost" in url and not (
        os.environ.get("DATABASE_URL")
        or os.environ.get("DATABASE_URL_PRIVATE")
        or os.environ.get("DATABASE_PUBLIC_URL")
    )


def run_setup():
    print("=" * 66)
    print("  🎓 tapsyrma — PostgreSQL ТОЛЫҚ орнату (БАРЛЫҚ ДЕРЕКТІ ӨШІРЕДІ!)")
    print("=" * 66)
    url = config.DATABASE_URL
    print(f"  DB: {url.split('@')[-1] if '@' in url else url}")

    if _using_local_default(url):
        print("\n❌ Локальді PostgreSQL жоқ (.env орнатылмаған).")
        print("   Шешім A — Railway Shell:  python setup_db.py")
        print("   Шешім B — .env.example → .env, DATABASE_URL=Railway сілтемесі")
        print("   Шешім C — деректерді сақтау:  python migrate_db.py")
        sys.exit(1)

    if os.environ.get("CONFIRM_RESET") != "yes":
        print("\n⚠️  Бұл скрипт БАРЛЫҚ кестелерді өшіріп қайта жасайды!")
        print("   Жалғастыру:  set CONFIRM_RESET=yes   (cmd)")
        print("   немесе:      $env:CONFIRM_RESET='yes'  (PowerShell)")
        print("   Деректерді сақтау үшін:  python migrate_db.py")
        sys.exit(1)

    print("\n[1/3] PostgreSQL қосылу...")
    try:
        conn = psycopg2.connect(url)
        conn.autocommit = True
    except psycopg2.Error as exc:
        print(f"\n❌ {exc}")
        print("   Railway → PostgreSQL → DATABASE_PUBLIC_URL → .env файлына қойыңыз")
        print("   Немесе Railway Shell ішінде іске қосыңыз")
        sys.exit(1)
    print("    ✅ Қосылды")

    script_path = os.path.join(os.path.dirname(__file__), "database.sql")
    sql = open(script_path, "r", encoding="utf-8").read()
    batches = split_batches(sql)

    print("\n[2/3] Кестелер, триггер, view...")
    executed = errors = 0
    with conn.cursor() as cur:
        for i, batch in enumerate(batches, 1):
            try:
                cur.execute(batch)
                executed += 1
            except psycopg2.Error as exc:
                errors += 1
                print(f"    ⚠️  Батч #{i}: {str(exc)[:200]}")
    print(f"    ✅ {executed} батч ({errors} ескерту)")

    print("\n[3/3] Парольдер...")
    admin_hash = generate_password_hash("admin123")
    teacher_hash = generate_password_hash("teacher123")
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE "Admins" SET "PasswordHash" = %s WHERE "PasswordHash" LIKE %s',
            (admin_hash, "PLACEHOLDER%"),
        )
        ac = cur.rowcount
        cur.execute(
            'UPDATE "Teachers" SET "PasswordHash" = %s WHERE "PasswordHash" = %s',
            (teacher_hash, "PLACEHOLDER"),
        )
        tc = cur.rowcount
    conn.close()
    print(f"    ✅ {ac} админ + {tc} оқытушы")

    import schema as schema_mod
    schema_mod._MIGRATIONS_DONE = False  # noqa: SLF001
    schema_mod.ensure_schema(force=True)

    print("\n🎉 Дайын!")
    print("🔐 admin@tapsyrma.kz / admin123  |  aigul@college.kz / teacher123")
    print("   Күнделікті deploy: migrate_db.py (деректер сақталады)")
    print("=" * 66)


if __name__ == "__main__":
    run_setup()
