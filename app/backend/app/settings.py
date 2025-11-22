# settings.py の頭の方に追加
import os
from pathlib import Path

# 既存
BASE_DIR = Path(__file__).resolve().parent.parent

# --- DEBUG / ALLOWED_HOSTS / TIME_ZONE を環境変数化 ---
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h] or []

LANGUAGE_CODE = "ja"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Tokyo")

# --- DATABASES を環境変数から設定（DATABASE_URL 優先、無ければ MySQL 個別値、最後に SQLite） ---
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # dj-database-url を使わない軽量版パーサ
    # 形式: mysql://user:pass@host:3306/dbname?charset=utf8mb4
    from urllib.parse import urlparse, parse_qs
    u = urlparse(DATABASE_URL)
    DB_NAME = u.path.lstrip("/")
    DB_USER = u.username or ""
    DB_PASS = u.password or ""
    DB_HOST = u.hostname or ""
    DB_PORT = u.port or 3306

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASS,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "OPTIONS": {"charset": parse_qs(u.query).get("charset", ["utf8mb4"])[0]},
        }
    }
else:
    # 個別の環境変数から（composeのMYSQL_*と揃える）
    MYSQL_DB = os.getenv("MYSQL_DATABASE")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))

    if MYSQL_DB and MYSQL_USER and MYSQL_PASSWORD:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.mysql",
                "NAME": MYSQL_DB,
                "USER": MYSQL_USER,
                "PASSWORD": MYSQL_PASSWORD,
                "HOST": MYSQL_HOST,
                "PORT": MYSQL_PORT,
                "OPTIONS": {"charset": "utf8mb4"},
            }
        }
    else:
        # フォールバック（開発用）
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }

# STATIC/MEDIA は現状のままでもOK（collectstaticで /code/deploy に吐き出し推奨）
STATIC_URL = "static/"
