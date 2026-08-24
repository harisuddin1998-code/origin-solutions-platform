"""Production-ready setup: creates saas_master_db and applies schema.sql, but
seeds ONLY roles plus one real Super Admin login you provide interactively -
no demo tenants, leads, deals, or projects ship to production.

Run once, instead of db/init_db.py, when you're ready to go live:
    python db/reset_demo_data.py

Safe to re-run: schema is idempotent (CREATE TABLE IF NOT EXISTS) and roles
use ON DUPLICATE KEY UPDATE. It will NOT delete any existing data - if you
need a truly empty database, drop it yourself first.
"""

import getpass
import os
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.security import hash_password  # noqa: E402
from db.init_db import run_sql_file  # noqa: E402

load_dotenv()

HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
PORT = int(os.environ.get("MYSQL_PORT", "3306"))
USER = os.environ.get("MYSQL_USER", "root")
PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
DB_NAME = os.environ.get("MYSQL_DB", "saas_master_db")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ROLES_SQL = """
INSERT INTO roles (name) VALUES
  ('super_admin'), ('developer'), ('qc'), ('marketing'), ('sales'),
  ('tenant_admin'), ('tenant_staff')
ON DUPLICATE KEY UPDATE name = VALUES(name)
"""


def prompt_admin():
    print("Create your real Super Admin login:")
    name = input("  Name: ").strip()
    email = input("  Email: ").strip().lower()
    while True:
        password = getpass.getpass("  Password (hidden): ")
        confirm = getpass.getpass("  Confirm password: ")
        if password and password == confirm:
            return name, email, password
        print("  Passwords didn't match (or were empty) - try again.")


def main():
    name, email, password = prompt_admin()

    conn = pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, autocommit=True)
    try:
        with conn.cursor() as cur:
            print("Running schema.sql ...")
            run_sql_file(cur, os.path.join(BASE_DIR, "schema.sql"))

        with conn.cursor() as cur:
            print("Seeding roles ...")
            cur.execute(ROLES_SQL)

            cur.execute("SELECT id FROM roles WHERE name = 'super_admin'")
            role_id = cur.fetchone()[0]

            print(f"Creating Super Admin login for {email} ...")
            cur.execute(
                """
                INSERT INTO users (tenant_id, role_id, name, email, password_hash, status)
                VALUES (NULL, %s, %s, %s, %s, 'active')
                ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash), name = VALUES(name)
                """,
                (role_id, name, email, hash_password(password)),
            )

        print("Done. Database is production-ready: no demo tenants, leads, deals, or projects.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
