import json

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from core.auth import guard_role
from core.db import execute, query
from projects.helpers import submit_qc_review

bp = Blueprint("qc_portal", __name__, template_folder="templates", url_prefix="/qc")
bp.before_request(guard_role("qc", "super_admin"))

TASK_STATUSES = ["todo", "in_progress", "done"]


@bp.route("/")
def index():
    return redirect(url_for("qc_portal.dashboard"))


@bp.route("/dashboard")
def dashboard():
    stats = {
        "pending_review": query(
            "SELECT COUNT(*) AS total FROM deployments WHERE status = 'review_ready'", fetchone=True
        )["total"],
        "reviewed_today": query(
            "SELECT COUNT(*) AS total FROM qc_reviews WHERE DATE(created_at) = CURDATE()", fetchone=True
        )["total"],
        "changes_requested": query(
            "SELECT COUNT(*) AS total FROM projects WHERE status = 'changes_requested'", fetchone=True
        )["total"],
    }
    return render_template("qc_portal/dashboard.html", stats=stats)


@bp.route("/projects")
def projects():
    if g.user["role"] == "super_admin":
        where, params = "1=1", ()
    else:
        where, params = "(p.qc_id = %s OR p.status = 'in_qc')", (g.user["id"],)

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
    return render_template("qc_portal/projects.html", projects=rows)


@bp.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        abort(404)

    deployments = query(
        "SELECT * FROM deployments WHERE project_id = %s ORDER BY created_at DESC", (project_id,)
    )
    latest_review_ready = next((d for d in deployments if d["status"] == "review_ready"), None)
    if latest_review_ready and latest_review_ready.get("files_changed"):
        latest_review_ready["files_changed"] = json.loads(latest_review_ready["files_changed"])

    return render_template(
        "qc_portal/project_detail.html",
        project=project,
        deployments=deployments,
        latest_review_ready=latest_review_ready,
    )


@bp.route("/projects/<int:project_id>/review", methods=["POST"])
def review_project(project_id):
    deployment_id = request.form.get("deployment_id", type=int)
    verdict = request.form.get("verdict")
    comments = request.form.get("comments", "")
    if verdict not in ("approved", "changes_requested") or not deployment_id:
        abort(400)

    submit_qc_review(deployment_id, g.user["id"], verdict, comments)
    return redirect(url_for("qc_portal.project_detail", project_id=project_id))


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
    return render_template("qc_portal/tasks.html", tasks=rows, columns=TASK_STATUSES)


@bp.route("/tasks/<int:task_id>/status", methods=["POST"])
def update_task_status(task_id):
    status = request.form.get("status")
    if status not in TASK_STATUSES:
        abort(400)
    execute("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
    return redirect(url_for("qc_portal.tasks"))
