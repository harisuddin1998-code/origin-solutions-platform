import threading

from flask import Blueprint, abort, current_app, jsonify, request

from core.db import query
from projects.github import record_push, verify_signature

bp = Blueprint("webhook_api", __name__)


def _deploy_in_background(app, project_id):
    """GitHub's own webhook delivery times out around 10s, and a
    docker-compose build + migrations easily takes minutes - so this runs
    off the request thread instead of making GitHub (and Cloudflare in
    front of us) wait for it. Needs its own app context since it's not
    running inside a request."""
    with app.app_context():
        from projects.vps_deploy import execute_deploy

        try:
            execute_deploy(project_id)
        except (ValueError, RuntimeError) as exc:
            app.logger.error(f"auto_deploy failed for project {project_id}: {exc}")


@bp.route("/webhooks/github/<int:project_id>", methods=["POST"])
def github_push(project_id):
    """Public endpoint - GitHub calls this directly, no session auth.
    Authenticity is verified via the per-project HMAC secret instead."""
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project or not project.get("github_webhook_secret"):
        abort(404)

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(project["github_webhook_secret"], request.get_data(), signature):
        abort(401)

    if request.headers.get("X-GitHub-Event", "") != "push":
        return jsonify({"ignored": request.headers.get("X-GitHub-Event", "")}), 200

    payload = request.get_json(silent=True) or {}
    deployment_id = record_push(project, payload)

    # Projects opted into auto_deploy skip the Dev -> QC review step: a push
    # to the default branch goes straight to production. Used for repos the
    # platform doesn't otherwise review (e.g. an external owner's own repo).
    ref = payload.get("ref", "")
    is_default_branch = ref in ("refs/heads/main", "refs/heads/master")
    deploying = bool(project.get("auto_deploy")) and is_default_branch and bool(project.get("github_repo"))
    if deploying:
        threading.Thread(
            target=_deploy_in_background, args=(current_app._get_current_object(), project_id), daemon=True
        ).start()

    return jsonify({"ok": True, "deployment_id": deployment_id, "auto_deploy_started": deploying}), 200
