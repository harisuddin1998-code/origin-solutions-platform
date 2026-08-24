"""Automated per-client deploy: one Docker container per client project,
reverse-proxied by Nginx on its own subdomain, with a Let's Encrypt cert.

Turns Super Admin's existing Deploy button (see
blueprints/super_admin/routes.py::deploy_project_route) from a pure DB status
flip into something that actually puts a client's approved software live on
its own subdomain - no manual server work per client.

Every step is computed as a plain (description, argv) pair by
build_deploy_plan() *before* anything runs, so the whole thing is inspectable
and testable via dry_run=True without touching the OS - useful both for
Admin ("preview before you commit") and for verifying this logic without a
real VPS.

Requires, on the VPS (see the plan file / README for the one-time setup):
  - Docker, Nginx, Certbot (python3-certbot-nginx), Git installed
  - the app's OS user in the `docker` group, plus a narrow passwordless-sudo
    rule for `systemctl reload nginx` and the certbot command below
  - a wildcard DNS A record (*.DEPLOY_DOMAIN -> this server's IP)

Convention required from Dev: every client project's repo must have a
Dockerfile at its root that listens on port 8000 internally.
"""

import os
import subprocess

from flask import current_app

from core.db import execute, query

CONTAINER_PORT = 8000
NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled"


def allocate_port(project):
    if project.get("port"):
        return project["port"]

    start = current_app.config["DEPLOY_PORT_RANGE_START"]
    end = current_app.config["DEPLOY_PORT_RANGE_END"]
    used = {
        row["port"]
        for row in query("SELECT port FROM projects WHERE port IS NOT NULL")
    }
    port = next((p for p in range(start, end + 1) if p not in used), None)
    if port is None:
        raise RuntimeError(f"No free port left in range {start}-{end}.")

    execute("UPDATE projects SET port = %s WHERE id = %s", (port, project["id"]))
    return port


def container_name_for(project):
    if project.get("container_name"):
        return project["container_name"]
    name = f"client-{project['id']}-{project['subdomain']}"
    execute("UPDATE projects SET container_name = %s WHERE id = %s", (name, project["id"]))
    return name


def render_nginx_config(subdomain, domain, port):
    server_name = f"{subdomain}.{domain}"
    return f"""server {{
    listen 80;
    server_name {server_name};

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""


def build_deploy_plan(project):
    """Returns (steps, context) where steps is an ordered list of
    (description, argv_or_None) - argv is None for steps that write a file
    rather than run a command. Nothing is executed here."""
    if not project.get("github_repo"):
        raise ValueError("Project has no github_repo set - nothing to deploy.")

    domain = current_app.config["DEPLOY_DOMAIN"]
    apps_dir = current_app.config["CLIENT_APPS_DIR"]
    admin_email = current_app.config["DEPLOY_ADMIN_EMAIL"]

    port = allocate_port(project)
    container = container_name_for(project)
    repo_dir = os.path.join(apps_dir, str(project["id"]))
    repo_url = f"https://github.com/{project['github_repo']}.git"
    subdomain = project["subdomain"]
    server_name = f"{subdomain}.{domain}"
    site_conf_path = os.path.join(NGINX_SITES_AVAILABLE, f"{server_name}.conf")
    site_enabled_path = os.path.join(NGINX_SITES_ENABLED, f"{server_name}.conf")

    clone_or_pull = (
        ["git", "-C", repo_dir, "pull"]
        if os.path.isdir(os.path.join(repo_dir, ".git"))
        else ["git", "clone", repo_url, repo_dir]
    )

    steps = [
        (f"Fetch latest code for {project['name']}", clone_or_pull),
        (
            "Verify Dockerfile exists at repo root",
            None,
            lambda: _require_dockerfile(repo_dir),
        ),
        (f"Build Docker image {container}", ["docker", "build", "-t", container, repo_dir]),
        (f"Stop old container {container} (if running)", ["docker", "rm", "-f", container]),
        (
            f"Start container {container} on port {port}",
            [
                "docker", "run", "-d",
                "--name", container,
                "--restart", "unless-stopped",
                "-p", f"127.0.0.1:{port}:{CONTAINER_PORT}",
                container,
            ],
        ),
        (
            f"Write Nginx config for {server_name}",
            None,
            lambda: _write_nginx_config(site_conf_path, site_enabled_path, subdomain, domain, port),
        ),
        ("Validate Nginx config", ["nginx", "-t"]),
        ("Reload Nginx", ["sudo", "systemctl", "reload", "nginx"]),
        (
            f"Issue SSL certificate for {server_name} (skipped if one already exists)",
            [
                "sudo", "certbot", "--nginx", "-d", server_name,
                "--non-interactive", "--agree-tos", "-m", admin_email,
            ],
        ),
    ]
    context = {"port": port, "container": container, "server_name": server_name, "domain": domain}
    return steps, context


def _require_dockerfile(repo_dir):
    dockerfile = os.path.join(repo_dir, "Dockerfile")
    if not os.path.isfile(dockerfile):
        raise RuntimeError(
            f"No Dockerfile found at the root of this project's repo ({repo_dir}). "
            "Every client project needs a Dockerfile that listens on port 8000."
        )


def _write_nginx_config(site_conf_path, site_enabled_path, subdomain, domain, port):
    config_text = render_nginx_config(subdomain, domain, port)
    os.makedirs(os.path.dirname(site_conf_path), exist_ok=True)
    with open(site_conf_path, "w", encoding="utf-8") as f:
        f.write(config_text)
    if not os.path.islink(site_enabled_path) and not os.path.exists(site_enabled_path):
        os.symlink(site_conf_path, site_enabled_path)


def execute_deploy(project_id, dry_run=False):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        raise ValueError(f"Project {project_id} not found.")

    steps, context = build_deploy_plan(project)

    if dry_run:
        return {
            "dry_run": True,
            "context": context,
            "steps": [
                {"description": s[0], "argv": s[1]} for s in steps
            ],
        }

    for step in steps:
        description, argv = step[0], step[1]
        custom_action = step[2] if len(step) > 2 else None
        try:
            if custom_action is not None:
                custom_action()
            elif argv is not None:
                subprocess.run(argv, check=True, capture_output=True, text=True)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            detail = exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)
            raise RuntimeError(f"Deploy failed at step '{description}': {detail}") from exc

    live_url = f"https://{context['server_name']}"
    execute("UPDATE projects SET status = 'live', live_url = %s WHERE id = %s", (live_url, project_id))
    execute(
        "UPDATE deployments SET status = 'deployed' WHERE project_id = %s AND status = 'approved'",
        (project_id,),
    )
    return {"dry_run": False, "live_url": live_url, "context": context}
