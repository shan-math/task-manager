import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# For Railway deployment, templates/static are inside Backend/
FRONTEND_DIR = BACKEND_DIR

# Load .env from Backend/ or project root
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.getenv("SESSION_LIFETIME_MINUTES", "60"))
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"

    MYSQL_HOST = os.getenv("MYSQL_HOST") or os.getenv("MYSQLHOST")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT") or os.getenv("MYSQLPORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER") or os.getenv("MYSQLUSER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQLPASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE") or os.getenv("MYSQLDATABASE")

    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@tms.local")
    MAIL_SUPPRESS_SEND = os.getenv("MAIL_SUPPRESS_SEND", "false").lower() == "true"

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", "16")) * 1024 * 1024
    ITEMS_PER_PAGE = int(os.getenv("ITEMS_PER_PAGE", "10"))
    API_TOKEN = os.getenv("API_TOKEN", "")

    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin123!")

    WTF_CSRF_ENABLED = True
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]
