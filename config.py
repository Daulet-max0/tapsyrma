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
