from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from core.auth import guard_role
from core.db import execute, query
from crm.helpers import get_agency_revenue_summary, get_financial_report, record_payment
from projects.helpers import deploy_project, pause_project, resume_project, set_live_url
from projects.vps_deploy import execute_deploy

bp = Blueprint("super_admin", __name__, template_folder="templates", url_prefix="/admin")
bp.before_request(guard_role("super_admin"))


@bp.route("/")
def index():
    return redirect(url_for("super_admin.dashboard"))


@bp.route("/dashboard")
def dashboard():
    stats = {
        "tenants": query("SELECT COUNT(*) AS total FROM tenants", fetchone=True)["total"],
        "active_tenants": query(
            "SELECT COUNT(*) AS total FROM tenants WHERE status = 'active'", fetchone=True
        )["total"],
        "users": query("SELECT COUNT(*) AS total FROM users", fetchone=True)["total"],
        "open_complaints": query(
            "SELECT COUNT(*) AS total FROM complaints WHERE status = 'open'", fetchone=True
        )["total"],
        "live_projects": query(
            "SELECT COUNT(*) AS total FROM projects WHERE status = 'live'", fetchone=True
        )["total"],
    }
    recent_audit = query("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10")
    return render_template("super_admin/dashboard.html", stats=stats, recent_audit=recent_audit)


@bp.route("/tenants")
def tenants():
    rows = query("SELECT * FROM tenants ORDER BY created_at DESC")
    return render_template("super_admin/tenants.html", tenants=rows)


@bp.route("/tenants/<int:tenant_id>/status", methods=["POST"])
def update_tenant_status(tenant_id):
    status = request.form.get("status")
    if status not in ("active", "suspended", "killed"):
        abort(400)
    execute("UPDATE tenants SET status = %s WHERE id = %s", (status, tenant_id))
    return redirect(url_for("super_admin.tenants"))


@bp.route("/financials")
def financials():
    report = get_financial_report()
    revenue_by_tenant = query(
        """
        SELECT t.name, COALESCE(SUM(p.total), 0) AS revenue
        FROM tenants t
        LEFT JOIN pos_sales p ON p.tenant_id = t.id
        GROUP BY t.id, t.name
        ORDER BY revenue DESC
        """
    )
    agency_revenue = get_agency_revenue_summary()
    client_invoices = query(
        """
        SELECT ci.*, c.name AS company_name
        FROM client_invoices ci
        JOIN companies c ON c.id = ci.company_id
        ORDER BY ci.created_at DESC
        """
    )
    return render_template(
        "super_admin/financials.html",
        report=report,
        revenue_by_tenant=revenue_by_tenant,
        agency_revenue=agency_revenue,
        client_invoices=client_invoices,
    )


@bp.route("/invoices/<int:invoice_id>/pay", methods=["POST"])
def pay_invoice(invoice_id):
    invoice = query("SELECT * FROM client_invoices WHERE id = %s", (invoice_id,), fetchone=True)
    if not invoice:
        abort(404)
    record_payment(invoice_id, invoice["total"])
    return redirect(url_for("super_admin.financials"))


@bp.route("/projects")
def projects():
    rows = query(
        """
        SELECT p.*, ud.name AS developer_name, uq.name AS qc_name, t.name AS tenant_name
        FROM projects p
        LEFT JOIN users ud ON ud.id = p.developer_id
        LEFT JOIN users uq ON uq.id = p.qc_id
        LEFT JOIN tenants t ON t.id = p.tenant_id
        ORDER BY p.updated_at DESC
        """
    )
    developers = query(
        "SELECT u.id, u.name FROM users u JOIN roles r ON r.id = u.role_id WHERE r.name = 'developer' ORDER BY u.name"
    )
    qcs = query(
        "SELECT u.id, u.name FROM users u JOIN roles r ON r.id = u.role_id WHERE r.name = 'qc' ORDER BY u.name"
    )
    return render_template("super_admin/projects.html", projects=rows, developers=developers, qcs=qcs)


@bp.route("/preview")
def preview():
    rows = query("SELECT * FROM projects ORDER BY updated_at DESC")
    return render_template("super_admin/preview.html", projects=rows)


@bp.route("/projects/<int:project_id>/assign", methods=["POST"])
def assign_project_route(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)
    developer_id = request.form.get("developer_id", type=int)
    qc_id = request.form.get("qc_id", type=int)
    execute(
        "UPDATE projects SET developer_id = %s, qc_id = %s WHERE id = %s",
        (developer_id or None, qc_id or None, project_id),
    )
    return redirect(url_for("super_admin.projects"))


@bp.route("/projects/<int:project_id>/live-url", methods=["POST"])
def set_live_url_route(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)
    set_live_url(project_id, request.form.get("live_url", "").strip())
    return redirect(url_for("super_admin.projects"))


@bp.route("/projects/<int:project_id>/deploy", methods=["POST"])
def deploy_project_route(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)

    if project["github_repo"]:
        try:
            result = execute_deploy(project_id)
            flash(f"Deployed — live at {result['live_url']}", "success")
        except (ValueError, RuntimeError) as exc:
            flash(str(exc), "error")
    else:
        try:
            deploy_project(project["subdomain"])
        except ValueError as exc:
            flash(str(exc), "error")

    return redirect(url_for("super_admin.projects"))


@bp.route("/projects/<int:project_id>/pause", methods=["POST"])
def pause_project_route(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)
    pause_project(project["subdomain"])
    return redirect(url_for("super_admin.projects"))


@bp.route("/projects/<int:project_id>/resume", methods=["POST"])
def resume_project_route(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)
    resume_project(project["subdomain"])
    return redirect(url_for("super_admin.projects"))


@bp.route("/tasks")
def tasks():
    rows = query(
        """
        SELECT t.*, ua.name AS assignee_name, ub.name AS assigner_name, p.name AS project_name
        FROM tasks t
        LEFT JOIN users ua ON ua.id = t.assigned_to
        LEFT JOIN users ub ON ub.id = t.assigned_by
        LEFT JOIN projects p ON p.id = t.project_id
        ORDER BY t.created_at DESC
        """
    )
    return render_template("super_admin/tasks.html", tasks=rows)


@bp.route("/tasks/new", methods=["GET", "POST"])
def new_task():
    if request.method == "POST":
        assigned_to = request.form.get("assigned_to", type=int)
        title = request.form.get("title", "").strip()
        if not assigned_to or not title:
            abort(400)
        execute(
            """
            INSERT INTO tasks (project_id, title, description, assigned_to, assigned_by, priority, due_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'todo')
            """,
            (
                request.form.get("project_id", type=int) or None,
                title,
                request.form.get("description", ""),
                assigned_to,
                g.user["id"],
                request.form.get("priority", "medium"),
                request.form.get("due_date") or None,
            ),
        )
        return redirect(url_for("super_admin.tasks"))

    assignees = query(
        """
        SELECT u.id, u.name, u.email, r.name AS role FROM users u
        JOIN roles r ON r.id = u.role_id
        WHERE r.name IN ('developer', 'qc', 'marketing', 'sales')
        ORDER BY u.name
        """
    )
    projects_list = query("SELECT id, name FROM projects ORDER BY name")
    return render_template("super_admin/task_new.html", assignees=assignees, projects=projects_list)


@bp.route("/users")
def users():
    rows = query(
        """
        SELECT u.*, r.name AS role_name, t.name AS tenant_name
        FROM users u
        JOIN roles r ON r.id = u.role_id
        LEFT JOIN tenants t ON t.id = u.tenant_id
        ORDER BY u.created_at DESC
        """
    )
    return render_template("super_admin/users.html", users=rows)


@bp.route("/complaints")
def complaints():
    rows = query(
        """
        SELECT c.*, t.name AS tenant_name, u.name AS raised_by_name
        FROM complaints c
        LEFT JOIN tenants t ON t.id = c.tenant_id
        LEFT JOIN users u ON u.id = c.raised_by
        ORDER BY c.created_at DESC
        """
    )
    return render_template("super_admin/complaints.html", complaints=rows)


@bp.route("/complaints/<int:complaint_id>/status", methods=["POST"])
def update_complaint_status(complaint_id):
    status = request.form.get("status")
    if status not in ("open", "in_progress", "resolved"):
        abort(400)
    execute("UPDATE complaints SET status = %s WHERE id = %s", (status, complaint_id))
    return redirect(url_for("super_admin.complaints"))
