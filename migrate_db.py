"""
Қауіпсіз миграция — деректерді ӨШІРМЕЙДІ, жаңа кесте/бағандарды қосады.
Railway deploy және локальді: DATABASE_URL орнатылған болуы керек.

    python migrate_db.py
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import config
import psycopg2
import schema


def main():
    url = config.DATABASE_URL
    host = url.split("@")[-1] if "@" in url else url
    print("=" * 60)
    print("  tapsyrma — DB миграция (деректер сақталады)")
    print("=" * 60)
    print(f"  Қосылу: {host}")

    if "localhost" in url and not (
        __import__("os").environ.get("DATABASE_URL")
        or __import__("os").environ.get("DATABASE_PUBLIC_URL")
    ):
        print("\n❌ Локальді PostgreSQL жоқ немесе .env жоқ.")
        print("   1) Railway → PostgreSQL → DATABASE_PUBLIC_URL көшіріңіз")
        print("   2) tapsyrma/.env файлына DATABASE_URL=... жазыңыз")
        print("   3) қайта: python migrate_db.py")
        print("\n   Немесе Railway Shell: python migrate_db.py")
        sys.exit(1)

    try:
        psycopg2.connect(url).close()
        print("  ✅ PostgreSQL қосылды")
    except psycopg2.Error as exc:
        print(f"\n❌ {exc}")
        sys.exit(1)

    schema._MIGRATIONS_DONE = False  # noqa: SLF001
    schema.ensure_schema(force=True)
    print("  ✅ Кестелер/бағандар жаңартылды (SiteSettings, DepartmentGoals, …)")
    print("=" * 60)


if __name__ == "__main__":
    main()
