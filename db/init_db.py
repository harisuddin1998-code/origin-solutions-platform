"""One-shot local setup: creates saas_master_db, applies schema.sql + seed.sql,
then inserts demo login users with properly hashed passwords.

Run once: `python db/init_db.py`. Re-running is safe for schema/roles/tenants
(idempotent) but will insert duplicate demo leads/tasks/etc rows.
"""

import json
import os
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.security import hash_password  # noqa: E402
from projects.github import generate_webhook_secret  # noqa: E402

load_dotenv()

HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
PORT = int(os.environ.get("MYSQL_PORT", "3306"))
USER = os.environ.get("MYSQL_USER", "root")
PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
DB_NAME = os.environ.get("MYSQL_DB", "saas_master_db")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_PASSWORD = "Passw0rd!"

# (name, email, role_name, tenant_subdomain_or_None)
SEED_USERS = [
    ("Super Admin", "superadmin@demo.local", "super_admin", None),
    ("Dana Developer", "dev@demo.local", "developer", None),
    ("Quinn QC", "qc@demo.local", "qc", None),
    ("Mona Marketing", "marketing@demo.local", "marketing", None),
    ("Sam Sales", "sales@demo.local", "sales", None),
    ("Tariq Tenant Admin", "admin@tenant1.local", "tenant_admin", "tenant1"),
]

# Demo software delivery pipeline: needs dev/qc user ids, so seeded here (in
# Python) rather than in seed.sql, which runs before users exist.
SEED_PROJECTS = [
    {
        "name": "Invoice Manager",
        "description": "Internal tool for generating and tracking client invoices.",
        "subdomain": "invoice-app",
        "tenant_subdomain": None,
        "status": "in_qc",
        "developer_email": "dev@demo.local",
        "qc_email": "qc@demo.local",
        "github_repo": "originsolutions-demo/invoice-manager",
        "deployment": {
            "version_label": "v1",
            "commit_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            "commit_message": "Add CSV export button to the invoice list page",
            "commit_author": "Dana Developer",
            "commit_url": "https://github.com/originsolutions-demo/invoice-manager/commit/a1b2c3d",
            "files_changed": {"added": ["static/js/export.js"], "modified": ["templates/invoices.html"], "removed": []},
            "status": "review_ready",
        },
    },
    {
        "name": "Fleet Tracker",
        "description": "Client-facing fleet tracking dashboard delivered to Demo Retail Co.",
        "subdomain": "fleet-tracker",
        "tenant_subdomain": "tenant1",
        "status": "live",
        "developer_email": "dev@demo.local",
        "qc_email": "qc@demo.local",
        "github_repo": "originsolutions-demo/fleet-tracker",
        "deployment": {
            "version_label": "v1",
            "commit_sha": "f0e9d8c7b6a5948372615049382716059483726",
            "commit_message": "Initial release: vehicle list, live status, driver assignment",
            "commit_author": "Dana Developer",
            "commit_url": "https://github.com/originsolutions-demo/fleet-tracker/commit/f0e9d8c",
            "files_changed": {"added": ["app.py", "templates/dashboard.html"], "modified": [], "removed": []},
            "status": "deployed",
        },
    },
]


# Demo Agency CRM data: companies/contacts/deals, one of which sits right at
# 'negotiation' so the deal-won auto-provisioning can be demoed immediately.
SEED_CRM_COMPANIES = [
    {
        "name": "Acme Retail Co",
        "domain": "acme-retail.com",
        "industry": "Retail",
        "contact": {
            "name": "Ali Raza",
            "email": "ali@acme-retail.com",
            "phone": "+923001112223",
            "job_title": "Operations Manager",
        },
        "deal": {
            "name": "Acme Retail - E-commerce Platform",
            "amount": 5000,
            "stage": "negotiation",
            "probability": 70,
        },
    },
    {
        "name": "Bright Bakery",
        "domain": "brightbakery.com",
        "industry": "Food & Beverage",
        "contact": {
            "name": "Sara Bright",
            "email": "sara@brightbakery.com",
            "phone": "+923004445556",
            "job_title": "Owner",
        },
        "deal": {
            "name": "Bright Bakery - POS System",
            "amount": 2000,
            "stage": "qualified",
            "probability": 40,
        },
    },
]


def run_sql_file(cursor, path):
    with open(path, "r", encoding="utf-8") as f:
        script = f.read()
    for statement in script.split(";"):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)


def seed_users(cursor):
    for name, email, role_name, tenant_subdomain in SEED_USERS:
        cursor.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
        role = cursor.fetchone()
        if not role:
            raise RuntimeError(f"Role '{role_name}' not found - did seed.sql run?")

        tenant_id = None
        if tenant_subdomain:
            cursor.execute("SELECT id FROM tenants WHERE subdomain = %s", (tenant_subdomain,))
            tenant_row = cursor.fetchone()
            if not tenant_row:
                raise RuntimeError(f"Tenant '{tenant_subdomain}' not found - did seed.sql run?")
            tenant_id = tenant_row[0]

        cursor.execute(
            """
            INSERT INTO users (tenant_id, role_id, name, email, password_hash, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
            ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash)
            """,
            (tenant_id, role[0], name, email, hash_password(DEMO_PASSWORD)),
        )


def seed_projects(cursor):
    for entry in SEED_PROJECTS:
        cursor.execute("SELECT id FROM users WHERE email = %s", (entry["developer_email"],))
        developer_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM users WHERE email = %s", (entry["qc_email"],))
        qc_id = cursor.fetchone()[0]

        tenant_id = None
        if entry["tenant_subdomain"]:
            cursor.execute("SELECT id FROM tenants WHERE subdomain = %s", (entry["tenant_subdomain"],))
            tenant_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO projects (name, description, subdomain, tenant_id, status, developer_id, qc_id, github_repo, github_webhook_secret)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status)
            """,
            (
                entry["name"],
                entry["description"],
                entry["subdomain"],
                tenant_id,
                entry["status"],
                developer_id,
                qc_id,
                entry["github_repo"],
                generate_webhook_secret(),
            ),
        )
        cursor.execute("SELECT id FROM projects WHERE subdomain = %s", (entry["subdomain"],))
        project_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM deployments WHERE project_id = %s", (project_id,))
        if cursor.fetchone():
            continue  # demo deployment already seeded for this project

        dep = entry["deployment"]
        cursor.execute(
            """
            INSERT INTO deployments
                (project_id, version_label, commit_sha, commit_message, commit_author, commit_url, files_changed, status, triggered_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                project_id,
                dep["version_label"],
                dep["commit_sha"],
                dep["commit_message"],
                dep["commit_author"],
                dep["commit_url"],
                json.dumps(dep["files_changed"]),
                dep["status"],
                developer_id,
            ),
        )
        deployment_id = cursor.lastrowid

        if dep["status"] == "deployed":
            cursor.execute(
                "INSERT INTO qc_reviews (deployment_id, reviewer_id, verdict, comments) VALUES (%s, %s, 'approved', %s)",
                (deployment_id, qc_id, "Looks good, approved for release."),
            )


def seed_crm(cursor):
    cursor.execute("SELECT id FROM users WHERE email = %s", ("sales@demo.local",))
    sales_id = cursor.fetchone()[0]

    for entry in SEED_CRM_COMPANIES:
        cursor.execute("SELECT id FROM companies WHERE domain = %s", (entry["domain"],))
        if cursor.fetchone():
            continue  # demo company already seeded

        cursor.execute(
            "INSERT INTO companies (name, domain, industry) VALUES (%s, %s, %s)",
            (entry["name"], entry["domain"], entry["industry"]),
        )
        company_id = cursor.lastrowid

        c = entry["contact"]
        cursor.execute(
            """
            INSERT INTO contacts (company_id, name, email, phone, job_title, owner_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'qualified')
            """,
            (company_id, c["name"], c["email"], c["phone"], c["job_title"], sales_id),
        )
        contact_id = cursor.lastrowid

        d = entry["deal"]
        cursor.execute(
            """
            INSERT INTO deals (company_id, contact_id, name, amount, stage, probability, owner_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (company_id, contact_id, d["name"], d["amount"], d["stage"], d["probability"], sales_id),
        )
        deal_id = cursor.lastrowid

        if d["stage"] in ("proposal_sent", "negotiation", "won"):
            cursor.execute(
                "INSERT INTO proposals (deal_id, title, status) VALUES (%s, %s, 'sent')",
                (deal_id, f"Proposal - {d['name']}"),
            )
            cursor.execute(
                "INSERT INTO quotations (deal_id, total, status) VALUES (%s, %s, 'sent')",
                (deal_id, d["amount"]),
            )

    cursor.execute("SELECT id FROM users WHERE email = %s", ("superadmin@demo.local",))
    admin_id = cursor.fetchone()[0]
    welcome_title = "Welcome to the Command Center"
    cursor.execute("SELECT id FROM notifications WHERE user_id = %s AND title = %s", (admin_id, welcome_title))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
            (admin_id, welcome_title, "Your CRM pipeline and GitHub-driven delivery pipeline are all ready."),
        )


def main():
    conn = pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, autocommit=True)
    try:
        with conn.cursor() as cur:
            print("Running schema.sql ...")
            run_sql_file(cur, os.path.join(BASE_DIR, "schema.sql"))

        with conn.cursor() as cur:
            print("Running seed.sql ...")
            run_sql_file(cur, os.path.join(BASE_DIR, "seed.sql"))

            print("Seeding demo users ...")
            seed_users(cur)

            print("Seeding demo projects/deployments ...")
            seed_projects(cur)

            print("Seeding demo CRM (companies/contacts/deals) ...")
            seed_crm(cur)

        print(f"Done. Demo password for every seeded user: {DEMO_PASSWORD}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
