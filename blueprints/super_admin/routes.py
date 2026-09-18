import os

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
)

from core.auth import guard_role
from core.db import execute, query
from crm.helpers import get_agency_revenue_summary, get_financial_report, record_payment
from projects import webapp_ops
from projects.dockerize import DockerizeError
from projects.github import create_project_from_repo
from projects.helpers import deploy_project, pause_project, resume_project, set_live_url
from projects.teardown import teardown_project
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


@bp.route("/projects/add", methods=["POST"])
def add_project_route():
    """One box, one click: paste a 'owner/repo', get a project that's already
    live on its own subdomain - no separate connect-then-deploy steps.
    Branch / main file path / start command are optional overrides - leave
    them blank and the deploy pipeline auto-detects the stack."""
    github_repo = request.form.get("github_repo", "").strip()
    if not github_repo:
        flash("Enter a GitHub repo as 'owner/repo'.", "error")
        return redirect(url_for("super_admin.projects"))

    branch = request.form.get("branch", "").strip() or None
    main_file_path = request.form.get("main_file_path", "").strip() or None
    start_command = request.form.get("start_command", "").strip() or None

    try:
        project_id = create_project_from_repo(
            github_repo, branch=branch, main_file_path=main_file_path, start_command=start_command
        )
        result = execute_deploy(project_id)
        flash(f"{github_repo} is live at {result['live_url']}", "success")
    except (ValueError, DockerizeError, RuntimeError) as exc:
        flash(str(exc), "error")

    return redirect(url_for("super_admin.projects"))


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


@bp.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project_route(project_id):
    """Permanently removes a project: tears down its live deployment (see
    projects/teardown.py) then deletes the DB row. Irreversible - redeploying
    afterwards starts completely from scratch."""
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)

    errors = teardown_project(project)
    execute("DELETE FROM projects WHERE id = %s", (project_id,))

    if errors:
        flash(f"{project['name']} removed, but some cleanup needs a manual check: " + "; ".join(errors), "error")
    else:
        flash(f"{project['name']} fully removed.", "success")

    return redirect(request.referrer or url_for("super_admin.projects"))


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


# --------------------------------------------------------------- web apps
# A per-project control panel in the shape of PythonAnywhere's "Web" tab:
# every project down the left, and the selected one's whole life - reload,
# status, traffic, what it runs, its own console, logs, backups - on the
# right. The heavy lifting lives in projects/webapp_ops.py.

def _webapp_context(project_id, **extra):
    projects_list = query(
        "SELECT id, name, subdomain, status, port FROM projects ORDER BY name"
    )
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)

    domain = current_app.config["DEPLOY_DOMAIN"]
    ctx = {
        "projects": projects_list,
        "project": project,
        "domain": domain,
        "server_name": f"{project['subdomain']}.{domain}",
        "state": webapp_ops.container_state(project),
        "traffic": webapp_ops.traffic_stats(project, domain),
        "backups": webapp_ops.list_backups(project),
        "source_dir": os.path.join(current_app.config["CLIENT_APPS_DIR"], str(project["id"])),
        "data_dir": os.path.join(current_app.config["CLIENT_DATA_DIR"], str(project["id"])),
        "console_output": None,
    }
    ctx.update(extra)
    return ctx


@bp.route("/webapps")
def webapps():
    first = query("SELECT id FROM projects ORDER BY name LIMIT 1", fetchone=True)
    if not first:
        return render_template("super_admin/webapps.html", projects=[], project=None)
    return redirect(url_for("super_admin.webapp_detail", project_id=first["id"]))


@bp.route("/webapps/<int:project_id>")
def webapp_detail(project_id):
    return render_template("super_admin/webapps.html", **_webapp_context(project_id))


@bp.route("/webapps/<int:project_id>/console", methods=["POST"])
def webapp_console(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)

    ok, output = webapp_ops.run_console(project, request.form.get("command", ""))
    if request.headers.get("X-Requested-With") == "fetch":
        return {"ok": ok, "output": output}
    return render_template(
        "super_admin/webapps.html", **_webapp_context(project_id, console_output=output)
    )


@bp.route("/webapps/<int:project_id>/power", methods=["POST"])
def webapp_power(project_id):
    """Restart / stop / start the container, without touching its code."""
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)

    action = request.form.get("action")
    handler = {
        "restart": webapp_ops.restart_container,
        "stop": webapp_ops.stop_container,
        "start": webapp_ops.start_container,
    }.get(action)
    if not handler:
        abort(400)

    ok, out = handler(project)
    if ok:
        flash(f"{project['name']}: {action} done.", "success")
    else:
        flash(f"{project['name']}: {action} failed. {out}", "error")
    return redirect(url_for("super_admin.webapp_detail", project_id=project_id))


@bp.route("/webapps/<int:project_id>/config", methods=["POST"])
def webapp_config(project_id):
    """Saves what the project runs. These take effect on the next deploy,
    not immediately - the running container was built from the old values,
    which is why the page says so next to the button."""
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)

    def clean(field):
        return (request.form.get(field) or "").strip() or None

    execute(
        """UPDATE projects
              SET branch = %s, main_file_path = %s, start_command = %s, data_mount_path = %s
            WHERE id = %s""",
        (clean("branch"), clean("main_file_path"), clean("start_command"),
         clean("data_mount_path"), project_id),
    )
    flash("Saved. Click \"Fetch latest push & rebuild\" to apply it.", "success")
    return redirect(url_for("super_admin.webapp_detail", project_id=project_id))


@bp.route("/webapps/<int:project_id>/restore", methods=["POST"])
def webapp_restore(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)

    ok, message = webapp_ops.restore_backup(project, request.form.get("backup", ""))
    flash(message, "success" if ok else "error")
    return redirect(url_for("super_admin.webapp_detail", project_id=project_id))


@bp.route("/webapps/<int:project_id>/logs")
def webapp_logs(project_id):
    """Fetched by the page so opening the tab doesn't wait on docker logs."""
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)
    return {
        "app": webapp_ops.container_logs(project),
        "nginx": webapp_ops.nginx_error_tail(project, current_app.config["DEPLOY_DOMAIN"]),
    }


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
