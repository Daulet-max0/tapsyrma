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


def run_setup():
    print("=" * 66)
    print("  🎓 tapsyrma — PostgreSQL орнату (Railway)")
    print("=" * 66)
    url = config.DATABASE_URL
    print(f"  DB: {url.split('@')[-1] if '@' in url else url}")

    print("\n[1/3] PostgreSQL қосылу...")
    try:
        conn = psycopg2.connect(url)
        conn.autocommit = True
    except psycopg2.Error as exc:
        print(f"\n❌ {exc}")
        print("   Railway: PostgreSQL plugin → DATABASE_URL автоматты")
        print("   Локальді: .env ішінде DATABASE_URL=postgresql://...")
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

    print("\n🎉 Дайын! Railway → Deploy → python setup_db.py (Bash)")
    print("🔐 admin / admin123  |  aigul / teacher123")
    print("=" * 66)


if __name__ == "__main__":
    run_setup()
