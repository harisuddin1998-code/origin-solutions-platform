"""Agency CRM: companies/contacts/deals pipeline, proposals/quotations/invoicing,
and a global notification center - shared logic reused by the Sales and Super
Admin portal routes, same pattern as projects/helpers.py.

The centerpiece is `provision_from_deal`: marking a deal 'won' auto-creates a
real `tenants` row and a real `projects` row, wiring this CRM straight into the
existing tenant-onboarding + Dev/QC/Deploy pipeline built earlier.
"""

import json
import re
import secrets

from core.db import execute, query
from core.security import hash_password


def slugify(name, table="tenants"):
    """table is one of a small fixed set we control ('tenants'/'projects'),
    never user input, so interpolating it into SQL below is safe. Tenant/project
    slugs live under their own /t/<slug> path prefix, so they can't collide
    with portal routes like /admin or /dev regardless of the name chosen."""
    assert table in ("tenants", "projects")

    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "client"

    slug = base
    suffix = 1
    while query(f"SELECT id FROM {table} WHERE subdomain = %s", (slug,), fetchone=True):
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


def get_or_create_company(name, **fields):
    company = query("SELECT * FROM companies WHERE name = %s", (name,), fetchone=True)
    if company:
        return company

    company_id = execute(
        """
        INSERT INTO companies (name, domain, industry, phone, website, city, country, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            name,
            fields.get("domain"),
            fields.get("industry"),
            fields.get("phone"),
            fields.get("website"),
            fields.get("city"),
            fields.get("country"),
            fields.get("notes"),
        ),
    )
    return query("SELECT * FROM companies WHERE id = %s", (company_id,), fetchone=True)


def create_contact(company_id, name, email="", phone="", job_title="", owner_id=None, lead_id=None):
    return execute(
        """
        INSERT INTO contacts (company_id, lead_id, name, email, phone, job_title, owner_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'qualified')
        """,
        (company_id, lead_id, name, email, phone, job_title, owner_id),
    )


def create_deal(company_id, name, amount=0, contact_id=None, owner_id=None, stage="qualified", probability=50):
    return execute(
        """
        INSERT INTO deals (company_id, contact_id, name, amount, stage, probability, owner_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (company_id, contact_id, name, amount, stage, probability, owner_id),
    )


def update_deal_stage(deal_id, new_stage, lost_reason=None):
    deal = query("SELECT * FROM deals WHERE id = %s", (deal_id,), fetchone=True)
    if not deal:
        raise ValueError("Deal not found.")

    execute("UPDATE deals SET stage = %s, lost_reason = %s WHERE id = %s", (new_stage, lost_reason, deal_id))

    if new_stage == "won":
        return provision_from_deal(deal)
    return {"deal_id": deal_id, "stage": new_stage}


def resolve_deal(identifier):
    deal = query(
        "SELECT d.* FROM deals d WHERE d.id = %s OR d.name = %s",
        (identifier if str(identifier).isdigit() else 0, identifier),
        fetchone=True,
    )
    if not deal:
        raise ValueError(f"No deal found matching '{identifier}'.")
    return deal


def provision_from_deal(deal):
    """The hybrid's centerpiece: a won deal becomes a real tenant + a real
    project, ready to flow through the existing Dev -> QC -> Deploy pipeline."""
    company = query("SELECT * FROM companies WHERE id = %s", (deal["company_id"],), fetchone=True)

    created_login = None
    if company["tenant_id"]:
        tenant_id = company["tenant_id"]
    else:
        slug = slugify(company["name"], table="tenants")
        tenant_id = execute(
            "INSERT INTO tenants (name, subdomain, status, plan) VALUES (%s, %s, 'active', 'trial')",
            (company["name"], slug),
        )
        execute("UPDATE companies SET tenant_id = %s WHERE id = %s", (tenant_id, company["id"]))

        role_row = query("SELECT id FROM roles WHERE name = 'tenant_admin'", fetchone=True)
        contact = (
            query("SELECT * FROM contacts WHERE id = %s", (deal["contact_id"],), fetchone=True)
            if deal["contact_id"]
            else None
        )
        login_email = contact["email"] if contact and contact["email"] else f"admin@{slug}.local"
        login_name = contact["name"] if contact else f"{company['name']} Admin"
        generated_password = secrets.token_urlsafe(9)

        execute(
            """
            INSERT INTO users (tenant_id, role_id, name, email, password_hash, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
            ON DUPLICATE KEY UPDATE tenant_id = VALUES(tenant_id)
            """,
            (tenant_id, role_row["id"], login_name, login_email, hash_password(generated_password)),
        )
        created_login = {"email": login_email, "password": generated_password, "subdomain": slug}

    project_slug = slugify(deal["name"], table="projects")
    execute(
        """
        INSERT INTO projects (name, description, subdomain, tenant_id, status)
        VALUES (%s, %s, %s, %s, 'planning')
        """,
        (deal["name"], f"Auto-provisioned from won deal '{deal['name']}'.", project_slug, tenant_id),
    )

    note = "New client project auto-created from a won deal - assign a developer and QC to get started."
    if created_login:
        note += (
            f" New tenant login: {created_login['email']} / {created_login['password']} "
            "(share manually - real email delivery isn't wired up yet)."
        )

    if deal.get("owner_id"):
        create_notification(deal["owner_id"], f"Deal won: {deal['name']}", note)
    for admin in query("SELECT u.id FROM users u JOIN roles r ON r.id = u.role_id WHERE r.name = 'super_admin'"):
        create_notification(admin["id"], f"Deal won: {deal['name']}", note)

    tenant_subdomain = query("SELECT subdomain FROM tenants WHERE id = %s", (tenant_id,), fetchone=True)["subdomain"]
    return {
        "deal": deal["name"],
        "tenant_subdomain": tenant_subdomain,
        "project_subdomain": project_slug,
        "new_login": created_login,
    }


def create_proposal(deal_id, title, content=""):
    return execute(
        "INSERT INTO proposals (deal_id, title, content, status) VALUES (%s, %s, %s, 'sent')",
        (deal_id, title, content),
    )


def create_quotation(deal_id, items, total):
    return execute(
        "INSERT INTO quotations (deal_id, items, total, status) VALUES (%s, %s, %s, 'sent')",
        (deal_id, json.dumps(items), total),
    )


def _next_invoice_number():
    total = query("SELECT COUNT(*) AS total FROM client_invoices", fetchone=True)["total"]
    return f"INV-{total + 1:04d}"


def create_invoice(company_id, total, deal_id=None, due_date=None, tax=0, discount=0, items=None):
    number = _next_invoice_number()
    return execute(
        """
        INSERT INTO client_invoices (deal_id, company_id, number, items, subtotal, tax, discount, total, status, due_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'sent', %s)
        """,
        (deal_id, company_id, number, json.dumps(items or []), total, tax, discount, total, due_date),
    )


def record_payment(invoice_id, amount, method="bank_transfer", transaction_ref=""):
    execute(
        "INSERT INTO client_payments (invoice_id, amount, method, transaction_ref) VALUES (%s, %s, %s, %s)",
        (invoice_id, amount, method, transaction_ref),
    )
    execute("UPDATE client_invoices SET status = 'paid' WHERE id = %s", (invoice_id,))


def create_notification(user_id, title, message="", link=None):
    execute(
        "INSERT INTO notifications (user_id, title, message, link) VALUES (%s, %s, %s, %s)",
        (user_id, title, message, link),
    )


def list_notifications(user_id, limit=8):
    return query(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
        (user_id, limit),
    )


def unread_count(user_id):
    return query(
        "SELECT COUNT(*) AS total FROM notifications WHERE user_id = %s AND is_read = FALSE",
        (user_id,),
        fetchone=True,
    )["total"]


def mark_all_read(user_id):
    execute("UPDATE notifications SET is_read = TRUE WHERE user_id = %s", (user_id,))


def get_pipeline_summary():
    rows = query("SELECT stage, COUNT(*) AS total, COALESCE(SUM(amount), 0) AS value FROM deals GROUP BY stage")
    return {"stages": {r["stage"]: {"count": r["total"], "value": float(r["value"])} for r in rows}}


def get_financial_report(period="month"):
    active_row = query("SELECT COUNT(*) AS total FROM tenants WHERE status = 'active'", fetchone=True)
    revenue_row = query("SELECT COALESCE(SUM(total), 0) AS total FROM pos_sales", fetchone=True)
    return {
        "period": period,
        "active_tenants": active_row["total"],
        "gross_pos_revenue": float(revenue_row["total"]),
    }


def get_agency_revenue_summary():
    invoiced = query("SELECT COALESCE(SUM(total), 0) AS total FROM client_invoices", fetchone=True)["total"]
    paid = query(
        "SELECT COALESCE(SUM(total), 0) AS total FROM client_invoices WHERE status = 'paid'", fetchone=True
    )["total"]
    return {
        "total_invoiced": float(invoiced),
        "total_paid": float(paid),
        "outstanding": float(invoiced) - float(paid),
    }
