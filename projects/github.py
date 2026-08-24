"""Real GitHub push integration for the Dev -> QC pipeline. A project is
linked to a GitHub repo; every real `git push` fires GitHub's webhook here,
and we record the actual commit as the thing QC reviews - no AI involved."""

import hashlib
import hmac
import json
import secrets

from core.db import execute, query
from crm.helpers import create_notification


def generate_webhook_secret():
    return secrets.token_hex(20)


def verify_signature(secret, payload_body, signature_header):
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def record_push(project, payload):
    """Parses a GitHub push webhook payload and records the real head commit
    as a new deployment awaiting QC review."""
    head_commit = payload.get("head_commit") or {}
    if not head_commit:
        return None  # e.g. a branch delete / tag push carries no head_commit

    commit_sha = head_commit.get("id", "")
    commit_message = head_commit.get("message", "")
    commit_author = (head_commit.get("author") or {}).get("name", "")
    commit_url = head_commit.get("url", "")
    files_changed = {
        "added": head_commit.get("added", []),
        "removed": head_commit.get("removed", []),
        "modified": head_commit.get("modified", []),
    }

    next_version = (
        query(
            "SELECT COUNT(*) AS total FROM deployments WHERE project_id = %s", (project["id"],), fetchone=True
        )["total"]
        + 1
    )

    deployment_id = execute(
        """
        INSERT INTO deployments
            (project_id, version_label, commit_sha, commit_message, commit_author, commit_url, files_changed, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'review_ready')
        """,
        (
            project["id"],
            f"v{next_version}",
            commit_sha,
            commit_message,
            commit_author,
            commit_url,
            json.dumps(files_changed),
        ),
    )

    execute("UPDATE projects SET status = 'in_qc' WHERE id = %s", (project["id"],))

    if project.get("qc_id"):
        first_line = commit_message.splitlines()[0] if commit_message else "(no commit message)"
        create_notification(
            project["qc_id"],
            f"New push for QC: {project['name']}",
            f"{commit_author or 'A developer'} pushed: {first_line}",
        )

    return deployment_id
