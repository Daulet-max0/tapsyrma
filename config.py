"""
Конфигурация — PostgreSQL (Railway DATABASE_URL)
"""
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def get_database_url() -> str:
    """Railway/postgres:// → postgresql:// (psycopg2)."""
    url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("DATABASE_URL_PRIVATE")
        or os.environ.get("DATABASE_PUBLIC_URL")
        or ""
    ).strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if not url:
        url = "postgresql://postgres:postgres@localhost:5432/tapsyrma"
    return url


DATABASE_URL = get_database_url()

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "turkestan-college-rating-2026-super-secret-key-change-me",
)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
MAX_CONTENT_LENGTH = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}

# Email (Railway / .env)
MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "").lower() in ("1", "true", "yes")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@tapsyrma.kz")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
