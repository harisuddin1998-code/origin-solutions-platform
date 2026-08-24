"""Shared business logic for the internal software delivery pipeline
(Dev -> QC -> Super Admin deploy), reused by the portal routes. Pushes come
from real GitHub webhooks (see projects/github.py) - QC reviews real commits,
not AI-generated text. "Deploy" flips a status flag rather than provisioning
real per-project infrastructure (see README for why).
"""

from flask import url_for

from core.db import execute, query
from crm.helpers import create_notification


def resolve_project(identifier):
    project = query(
        "SELECT * FROM projects WHERE subdomain = %s OR name = %s", (identifier, identifier), fetchone=True
    )
    if not project:
        raise ValueError(f"No project found matching '{identifier}'.")
    return project


def submit_qc_review(deployment_id, reviewer_id, verdict, comments):
    deployment = query("SELECT * FROM deployments WHERE id = %s", (deployment_id,), fetchone=True)
    if not deployment:
        raise ValueError("Deployment not found.")

    execute(
        "INSERT INTO qc_reviews (deployment_id, reviewer_id, verdict, comments) VALUES (%s, %s, %s, %s)",
        (deployment_id, reviewer_id, verdict, comments),
    )

    new_status = "approved" if verdict == "approved" else "changes_requested"
    execute("UPDATE deployments SET status = %s WHERE id = %s", (new_status, deployment_id))
    execute("UPDATE projects SET status = %s WHERE id = %s", (new_status, deployment["project_id"]))

    project = query("SELECT * FROM projects WHERE id = %s", (deployment["project_id"],), fetchone=True)
    dev_link = url_for("dev_portal.project_detail", project_id=project["id"])
    verdict_label = "approved" if verdict == "approved" else "requested changes on"

    if project["developer_id"]:
        create_notification(
            project["developer_id"],
            f"QC {verdict_label} your push on {project['name']}",
            comments or "(no additional notes)",
            dev_link,
        )

    if verdict == "approved":
        admins = query("SELECT u.id FROM users u JOIN roles r ON r.id = u.role_id WHERE r.name = 'super_admin'")
        admin_link = url_for("super_admin.projects")
        for admin in admins:
            create_notification(
                admin["id"],
                f"{project['name']} approved by QC, ready to deploy",
                comments or "(no additional notes)",
                admin_link,
            )

    return {"deployment_id": deployment_id, "verdict": verdict}


def set_live_url(project_id, live_url):
    execute("UPDATE projects SET live_url = %s WHERE id = %s", (live_url or None, project_id))


def deploy_project(identifier):
    project = resolve_project(identifier)
    if project["status"] != "approved":
        raise ValueError(f"Project '{project['name']}' is not approved yet (status: {project['status']}).")

    execute("UPDATE projects SET status = 'live' WHERE id = %s", (project["id"],))
    execute(
        "UPDATE deployments SET status = 'deployed' WHERE project_id = %s AND status = 'approved'",
        (project["id"],),
    )
    return {"project": project["name"], "status": "live"}


def pause_project(identifier):
    project = resolve_project(identifier)
    execute("UPDATE projects SET status = 'paused' WHERE id = %s", (project["id"],))
    return {"project": project["name"], "status": "paused"}


def resume_project(identifier):
    project = resolve_project(identifier)
    execute("UPDATE projects SET status = 'live' WHERE id = %s", (project["id"],))
    return {"project": project["name"], "status": "live"}


