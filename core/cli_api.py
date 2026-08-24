"""Token-authenticated API for cli/pms.py - the small command-line tool run
from VS Code's (or any) terminal. Not for browsers; see core/api_auth.py."""

from flask import Blueprint, g, jsonify, request

from core.api_auth import require_api_token
from core.db import query
from projects.helpers import deploy_project
from projects.vps_deploy import execute_deploy

bp = Blueprint("cli_api", __name__, url_prefix="/api/cli")


@bp.route("/whoami")
@require_api_token
def whoami():
    return jsonify({"name": g.user["name"], "email": g.user["email"], "role": g.user["role"]})


@bp.route("/projects")
@require_api_token
def projects():
    role = g.user["role"]
    if role == "super_admin":
        where, params = "1=1", ()
    elif role == "qc":
        where, params = "(qc_id = %s OR status = 'in_qc')", (g.user["id"],)
    elif role == "developer":
        where, params = "developer_id = %s", (g.user["id"],)
    else:
        where, params = "1=0", ()

    rows = query(
        f"SELECT id, name, subdomain, status FROM projects WHERE {where} ORDER BY updated_at DESC", params
    )
    return jsonify({"projects": rows})


@bp.route("/status")
@require_api_token
def status():
    tasks = query(
        """
        SELECT id, title, status, priority FROM tasks
        WHERE assigned_to = %s AND status != 'done'
        ORDER BY created_at DESC
        """,
        (g.user["id"],),
    )
    pending_review = []
    if g.user["role"] in ("qc", "super_admin"):
        pending_review = query(
            """
            SELECT d.id, p.name AS project_name, d.version_label
            FROM deployments d
            JOIN projects p ON p.id = d.project_id
            WHERE d.status = 'review_ready'
            """
        )
    return jsonify({"open_tasks": tasks, "pending_review": pending_review})


@bp.route("/deploy/<int:project_id>", methods=["POST"])
@require_api_token
def deploy(project_id):
    if g.user["role"] != "super_admin":
        return jsonify({"error": "Only a super_admin token can deploy."}), 403

    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        return jsonify({"error": "Project not found."}), 404

    if project["github_repo"]:
        dry_run = request.args.get("dry_run", "").lower() in ("1", "true", "yes")
        try:
            result = execute_deploy(project_id, dry_run=dry_run)
        except (ValueError, RuntimeError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    try:
        result = deploy_project(project["subdomain"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)
