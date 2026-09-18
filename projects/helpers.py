from core.db import execute, query

def submit_qc_review(deployment_id, reviewer_id, verdict, comments):
    deployment = query("SELECT * FROM deployments WHERE id = %s", (deployment_id,), fetchone=True)
    if not deployment: raise ValueError("Deployment not found.")
    execute("INSERT INTO qc_reviews (deployment_id, reviewer_id, verdict, comments) VALUES (%s, %s, %s, %s)", (deployment_id, reviewer_id, verdict, comments))
    status = "approved" if verdict == "approved" else "changes_requested"
    execute("UPDATE deployments SET status = %s WHERE id = %s", (status, deployment_id))
    return {"deployment_id": deployment_id, "verdict": verdict}

def _project(identifier):
    project = query("SELECT * FROM projects WHERE subdomain = %s OR name = %s", (identifier, identifier), fetchone=True)
    if not project: raise ValueError(f"No project found matching {identifier}.")
    return project

def deploy_project(identifier):
    project = _project(identifier)
    execute("UPDATE projects SET status = 'live' WHERE id = %s", (project["id"],))
    return {"project": project["name"], "status": "live"}

def pause_project(identifier):
    project = _project(identifier); execute("UPDATE projects SET status = 'paused' WHERE id = %s", (project["id"],)); return {"project": project["name"], "status": "paused"}

def resume_project(identifier):
    project = _project(identifier); execute("UPDATE projects SET status = 'live' WHERE id = %s", (project["id"],)); return {"project": project["name"], "status": "live"}

def set_live_url(project_id, live_url):
    execute("UPDATE projects SET live_url = %s WHERE id = %s", (live_url or None, project_id))
