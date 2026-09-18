import requests
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from core.auth import guard_role
from core.db import execute, query
from projects.dockerize import DockerizeError
from projects.github import create_project_from_repo, generate_webhook_secret, unique_subdomain
from projects.vps_deploy import execute_deploy

bp = Blueprint("dev_portal", __name__, template_folder="templates", url_prefix="/dev")
bp.before_request(guard_role("developer", "super_admin"))

TASK_STATUSES = ["todo", "in_progress", "qc_review", "done"]


@bp.route("/")
def index():
    return redirect(url_for("dev_portal.dashboard"))


@bp.route("/dashboard")
def dashboard():
    dev_filter = "" if g.user["role"] == "super_admin" else "AND developer_id = %s"
    params = () if g.user["role"] == "super_admin" else (g.user["id"],)
    stats = {
        "open_tasks": query("SELECT COUNT(*) AS total FROM tasks WHERE status != 'done'", fetchone=True)["total"],
        "in_qc": query("SELECT COUNT(*) AS total FROM tasks WHERE status = 'qc_review'", fetchone=True)["total"],
        "connected_repos": query(
            f"SELECT COUNT(*) AS total FROM projects WHERE github_repo IS NOT NULL {dev_filter}",
            params,
            fetchone=True,
        )["total"],
    }
    return render_template("dev_portal/dashboard.html", stats=stats)


@bp.route("/tasks")
def tasks():
    rows = query(
        """
        SELECT t.*, ua.name AS assignee_name, ub.name AS assigner_name
        FROM tasks t
        LEFT JOIN users ua ON ua.id = t.assigned_to
        LEFT JOIN users ub ON ub.id = t.assigned_by
        ORDER BY t.created_at DESC
        """
    )
    return render_template("dev_portal/tasks.html", tasks=rows, columns=TASK_STATUSES)


@bp.route("/tasks/<int:task_id>/status", methods=["POST"])
def update_task_status(task_id):
    status = request.form.get("status")
    if status not in TASK_STATUSES:
        abort(400)
    execute("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
    return redirect(url_for("dev_portal.tasks"))


@bp.route("/projects")
def projects():
    if g.user["role"] == "super_admin":
        where, params = "1=1", ()
    else:
        where, params = "developer_id = %s", (g.user["id"],)

    rows = query(
        f"""
        SELECT p.*, ud.name AS developer_name, uq.name AS qc_name,
               (SELECT status FROM deployments d WHERE d.project_id = p.id
                ORDER BY d.created_at DESC LIMIT 1) AS latest_deployment_status
        FROM projects p
        LEFT JOIN users ud ON ud.id = p.developer_id
        LEFT JOIN users uq ON uq.id = p.qc_id
        WHERE {where}
        ORDER BY p.updated_at DESC
        """,
        params,
    )
    return render_template("dev_portal/projects.html", projects=rows)


@bp.route("/preview")
def project_preview():
    if g.user["role"] != "developer":
        abort(404)

    rows = query("SELECT * FROM projects WHERE developer_id = %s ORDER BY updated_at DESC", (g.user["id"],))
    return render_template("dev_portal/preview.html", projects=rows)


@bp.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)
    if g.user["role"] == "developer" and g.user["id"] != project["developer_id"]:
        abort(403)

    deployments = query(
        "SELECT * FROM deployments WHERE project_id = %s ORDER BY created_at DESC", (project_id,)
    )
    qc_reviews = query(
        """
        SELECT r.*, d.version_label, u.name AS reviewer_name
        FROM qc_reviews r
        JOIN deployments d ON d.id = r.deployment_id
        LEFT JOIN users u ON u.id = r.reviewer_id
        WHERE d.project_id = %s
        ORDER BY r.created_at DESC
        """,
        (project_id,),
    )
    webhook_url = url_for("webhook_api.github_push", project_id=project_id, _external=True)

    return render_template(
        "dev_portal/project_detail.html",
        project=project,
        deployments=deployments,
        qc_reviews=qc_reviews,
        webhook_url=webhook_url,
        is_developer=g.user["id"] == project["developer_id"],
    )


@bp.route("/projects/add", methods=["POST"])
def add_project():
    """One box, one click: paste a 'owner/repo', get a project that's already
    live on its own subdomain - no separate connect-then-deploy steps."""
    github_repo = request.form.get("github_repo", "").strip()
    if not github_repo:
        flash("Enter a GitHub repo as 'owner/repo'.", "error")
        return redirect(url_for("dev_portal.projects"))

    try:
        project_id = create_project_from_repo(github_repo, developer_id=g.user["id"])
        result = execute_deploy(project_id)
        flash(f"{github_repo} is live at {result['live_url']}", "success")
    except (ValueError, DockerizeError, RuntimeError) as exc:
        flash(str(exc), "error")

    return redirect(url_for("dev_portal.projects"))


@bp.route("/github/sync", methods=["POST"])
def sync_github_repos():
    username = request.form.get("github_username", "").strip()
    username = username.split("github.com/")[-1].strip("/")
    if not username:
        abort(400)

    resp = requests.get(
        f"https://api.github.com/users/{username}/repos",
        params={"per_page": 100, "sort": "updated"},
        headers={"Accept": "application/vnd.github+json"},
        timeout=15,
    )
    if resp.status_code != 200:
        flash(f"Could not fetch repos for '{username}' from GitHub (status {resp.status_code}).", "error")
        return redirect(url_for("dev_portal.projects"))

    existing_repos = {
        row["github_repo"]
        for row in query("SELECT github_repo FROM projects WHERE github_repo IS NOT NULL")
    }

    imported = 0
    for repo in resp.json():
        full_name = repo["full_name"]
        if full_name in existing_repos:
            continue
        execute(
            """
            INSERT INTO projects (name, subdomain, status, developer_id, github_repo, github_webhook_secret)
            VALUES (%s, %s, 'in_dev', %s, %s, %s)
            """,
            (repo["name"], unique_subdomain(repo["name"]), g.user["id"], full_name, generate_webhook_secret()),
        )
        imported += 1

    flash(f"Imported {imported} new project(s) from '{username}' on GitHub.", "success")
    return redirect(url_for("dev_portal.projects"))


@bp.route("/projects/<int:project_id>/github", methods=["POST"])
def set_github_repo(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)
    if g.user["role"] != "super_admin" and g.user["id"] != project["developer_id"]:
        abort(403)

    github_repo = request.form.get("github_repo", "").strip().strip("/")
    if not github_repo:
        abort(400)

    execute(
        "UPDATE projects SET github_repo = %s, github_webhook_secret = %s WHERE id = %s",
        (github_repo, generate_webhook_secret(), project_id),
    )
    return redirect(url_for("dev_portal.project_detail", project_id=project_id))
