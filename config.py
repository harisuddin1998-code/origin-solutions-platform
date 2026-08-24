import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ["FLASK_SECRET_KEY"]

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "saas_master_db")

    WHATSAPP_WEBHOOK_TOKEN = os.environ.get("WHATSAPP_WEBHOOK_TOKEN", "")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Automated per-client VPS deploy (see projects/vps_deploy.py)
    DEPLOY_DOMAIN = os.environ.get("DEPLOY_DOMAIN", "originsolutions.com")
    DEPLOY_ADMIN_EMAIL = os.environ.get("DEPLOY_ADMIN_EMAIL", "")
    CLIENT_APPS_DIR = os.environ.get("CLIENT_APPS_DIR", "/srv/client-apps")
    DEPLOY_PORT_RANGE_START = int(os.environ.get("DEPLOY_PORT_RANGE_START", "6000"))
    DEPLOY_PORT_RANGE_END = int(os.environ.get("DEPLOY_PORT_RANGE_END", "6999"))
