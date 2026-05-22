"""
WSGI — Railway (gunicorn wsgi:app) және локальді тест.
"""
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from app import app  # noqa: E402

try:
    import schema
    schema.ensure_schema()
except Exception:
    pass
