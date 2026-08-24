from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from core.auth import guard_role
from core.db import execute, query
from mock_integrations.helpers import create_fake_lead, first_tenant_id

bp = Blueprint("marketing", __name__, template_folder="templates", url_prefix="/marketing")
bp.before_request(guard_role("marketing", "super_admin"))

TASK_STATUSES = ["todo", "in_progress", "done"]


@bp.route("/")
def index():
    return redirect(url_for("marketing.dashboard"))


@bp.route("/dashboard")
def dashboard():
    stats = {
        "ad_accounts": query(
            "SELECT COUNT(*) AS total FROM ad_accounts WHERE status = 'active'", fetchone=True
        )["total"],
        "whatsapp_numbers": query(
            "SELECT COUNT(*) AS total FROM whatsapp_instances WHERE status = 'active'", fetchone=True
        )["total"],
        "leads_7d": query(
            "SELECT COUNT(*) AS total FROM leads WHERE created_at >= NOW() - INTERVAL 7 DAY", fetchone=True
        )["total"],
    }
    return render_template("marketing/dashboard.html", stats=stats)


@bp.route("/connectors")
def connectors():
    ad_accounts = query(
        """
        SELECT a.*, t.name AS tenant_name FROM ad_accounts a
        JOIN tenants t ON t.id = a.tenant_id
        ORDER BY a.connected_at DESC
        """
    )
    whatsapp_numbers = query(
        """
        SELECT w.*, t.name AS tenant_name FROM whatsapp_instances w
        JOIN tenants t ON t.id = w.tenant_id
        ORDER BY w.created_at DESC
        """
    )
    return render_template(
        "marketing/connectors.html", ad_accounts=ad_accounts, whatsapp_numbers=whatsapp_numbers
    )


@bp.route("/connectors/mock-connect", methods=["POST"])
def mock_connect():
    platform = request.form.get("platform", "meta")
    tenant_id = first_tenant_id()
    execute(
        """
        INSERT INTO ad_accounts (tenant_id, platform, account_name, external_account_id, status)
        VALUES (%s, %s, %s, %s, 'active')
        """,
        (tenant_id, platform, f"Demo {platform.title()} Account", f"acc_{platform}_{tenant_id}"),
    )
    return redirect(url_for("marketing.connectors"))


@bp.route("/whatsapp-inbox")
def whatsapp_inbox():
    messages = query(
        """
        SELECT m.*, l.name AS lead_name FROM whatsapp_messages m
        LEFT JOIN leads l ON l.id = m.lead_id
        ORDER BY m.sent_at DESC LIMIT 50
        """
    )
    numbers = query(
        """
        SELECT w.*, t.name AS tenant_name FROM whatsapp_instances w
        JOIN tenants t ON t.id = w.tenant_id
        """
    )
    return render_template("marketing/whatsapp_inbox.html", messages=messages, numbers=numbers)


@bp.route("/simulate-lead", methods=["POST"])
def simulate_lead():
    source = request.form.get("source", "meta")
    create_fake_lead(first_tenant_id(), source)
    return redirect(request.referrer or url_for("marketing.dashboard"))


@bp.route("/tasks")
def tasks():
    rows = query(
        """
        SELECT t.*, ub.name AS assigner_name
        FROM tasks t
        LEFT JOIN users ub ON ub.id = t.assigned_by
        WHERE t.assigned_to = %s
        ORDER BY t.created_at DESC
        """,
        (g.user["id"],),
    )
    return render_template("marketing/tasks.html", tasks=rows, columns=TASK_STATUSES)


@bp.route("/tasks/<int:task_id>/status", methods=["POST"])
def update_task_status(task_id):
    status = request.form.get("status")
    if status not in TASK_STATUSES:
        abort(400)
    execute("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
    return redirect(url_for("marketing.tasks"))
