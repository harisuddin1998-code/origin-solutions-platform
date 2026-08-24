from flask import Blueprint, abort, jsonify, request

from core.db import query
from projects.github import record_push, verify_signature

bp = Blueprint("webhook_api", __name__)


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
    return jsonify({"ok": True, "deployment_id": deployment_id}), 200
