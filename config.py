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
    DEPLOY_DOMAIN = os.environ.get("DEPLOY_DOMAIN", "originssolutions.com")
    DEPLOY_ADMIN_EMAIL = os.environ.get("DEPLOY_ADMIN_EMAIL", "")
    CLIENT_APPS_DIR = os.environ.get("CLIENT_APPS_DIR", "/srv/client-apps")
    # Persistent per-project data directory, bind-mounted into every
    # single-container deploy at /data (see vps_deploy.py). A redeploy
    # rebuilds the container from scratch, so anything an app needs to
    # survive that (a SQLite db.sqlite3, uploaded files) must live here, not
    # in the container's own writable layer.
    CLIENT_DATA_DIR = os.environ.get("CLIENT_DATA_DIR", "/srv/client-data")
    # Timestamped snapshots of CLIENT_DATA_DIR, taken automatically before
    # every redeploy (see vps_deploy.py::_backup_data_dir). A redeploy runs
    # the client app's own startup code fresh against its mounted database,
    # and some client apps clear and reseed on boot, so the bind mount alone
    # is not the whole safety net.
    CLIENT_BACKUPS_DIR = os.environ.get("CLIENT_BACKUPS_DIR", "/srv/client-backups")
    DEPLOY_PORT_RANGE_START = int(os.environ.get("DEPLOY_PORT_RANGE_START", "6000"))
    DEPLOY_PORT_RANGE_END = int(os.environ.get("DEPLOY_PORT_RANGE_END", "6999"))

    # Cloudflare Tunnel + DNS: every deployed project's subdomain is wired up
    # here instead of Let's Encrypt/certbot, since the VPS has no public IP of
    # its own -- all traffic arrives through this one tunnel.
    CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    CLOUDFLARE_ZONE_ID = os.environ.get("CLOUDFLARE_ZONE_ID", "")
    CLOUDFLARE_TUNNEL_ID = os.environ.get("CLOUDFLARE_TUNNEL_ID", "")
    CLOUDFLARE_TUNNEL_TARGET = os.environ.get("CLOUDFLARE_TUNNEL_TARGET", "")
