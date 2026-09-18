"""Multi-service deploy for client repos that ship a docker-compose.yml -
apps backed by Postgres/Redis/Celery, not just a single Dockerfile on port
8000. vps_deploy.execute_deploy() checks for this file (via
repo_has_compose_file, before cloning) and delegates here instead of the
single-container path when it's present.

Convention this expects from the repo: the externally-facing HTTP service in
docker-compose.yml must be named "web". Every service's host port mapping is
stripped - Postgres/Redis/etc. stay reachable only from other containers on
the compose network, and "web" gets a host port from the same pool
single-container projects use. This platform's own Nginx + Cloudflare Tunnel
front the app from there, exactly like every other project - so a
docker-compose.yml's own "nginx" service (if any) is skipped entirely.
"""

import os
import subprocess
import time

import requests
import yaml
from flask import current_app

from core.db import execute
from projects.cloudflare import wire_up_subdomain

NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled"


def repo_has_compose_file(github_repo):
    """Cheap pre-clone check so execute_deploy can route to this path without
    cloning first: does this repo have a docker-compose.yml at its root?"""
    try:
        meta = requests.get(f"https://api.github.com/repos/{github_repo}", timeout=10)
        branch = meta.json().get("default_branch", "main") if meta.ok else "main"
        resp = requests.head(
            f"https://raw.githubusercontent.com/{github_repo}/{branch}/docker-compose.yml",
            timeout=10,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _web_internal_port(compose):
    web = compose.get("services", {}).get("web")
    if not web:
        raise RuntimeError(
            "docker-compose.yml has no 'web' service - that's the convention this platform "
            "expects for the externally-facing app. Rename the HTTP-serving service to 'web' "
            "and redeploy."
        )
    for mapping in web.get("ports", []):
        target = str(mapping).split(":")[-1]
        if target.isdigit():
            return int(target)
    raise RuntimeError("Could not determine the 'web' service's internal port from docker-compose.yml.")


def deploy_compose_stack(project, repo_dir):
    from projects.vps_deploy import allocate_port  # deferred: avoids a circular import with vps_deploy

    domain = current_app.config["DEPLOY_DOMAIN"]
    subdomain = project["subdomain"]
    server_name = f"{subdomain}.{domain}"
    compose_path = os.path.join(repo_dir, "docker-compose.yml")

    with open(compose_path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    internal_port = _web_internal_port(compose)
    host_port = allocate_port(project)
    compose_project = f"client{project['id']}"

    # A .env dropped directly in the repo dir (never committed - untouched by
    # git pull) is this project's real secrets: mail, third-party API keys,
    # an internal DB to sync with, etc. If one exists, every app-code service
    # (not the datastores) gets it wired in automatically, so it survives
    # every future redeploy without editing this function again per project.
    has_secrets_env = os.path.isfile(os.path.join(repo_dir, ".env"))
    datastore_services = {"postgres", "redis", "mysql", "mariadb", "mongo"}

    override = {"services": {}}
    for name, svc in compose.get("services", {}).items():
        if name == "nginx":
            continue
        entry = {}
        if name == "web":
            entry["ports"] = [f"127.0.0.1:{host_port}:{internal_port}"]
        elif "ports" in svc:
            entry["ports"] = []
        if has_secrets_env and name not in datastore_services:
            entry["env_file"] = [".env"]
        if entry:
            override["services"][name] = entry

    override_path = os.path.join(repo_dir, "docker-compose.override.yml")
    with open(override_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(override, f)

    up_services = [name for name in compose.get("services", {}) if name != "nginx"]
    _run(
        [
            "docker", "compose", "-p", compose_project,
            "-f", "docker-compose.yml", "-f", "docker-compose.override.yml",
            "up", "-d", "--build", *up_services,
        ],
        step="Build and start the docker-compose stack",
        cwd=repo_dir,
    )

    _run_migrations(compose_project, repo_dir)

    site_conf_path = os.path.join(NGINX_SITES_AVAILABLE, f"{server_name}.conf")
    site_enabled_path = os.path.join(NGINX_SITES_ENABLED, f"{server_name}.conf")
    _write_nginx_config(site_conf_path, site_enabled_path, server_name, host_port)
    _run(["sudo", "nginx", "-t"], step="Validate Nginx config")
    _run(["sudo", "systemctl", "reload", "nginx"], step="Reload Nginx")

    wire_up_subdomain(subdomain, domain)

    container_name = f"{compose_project}-web"
    execute("UPDATE projects SET container_name = %s WHERE id = %s", (container_name, project["id"]))

    return {"port": host_port, "container": container_name, "server_name": server_name, "domain": domain}


def _run_migrations(compose_project, repo_dir):
    """Tries, in order: Flask-Migrate, plain Alembic, then a `flask init-db`
    CLI command - the convention this platform's other client repos already
    use to bootstrap their schema when Alembic isn't (fully) wired up."""
    time.sleep(3)
    attempts = [
        ["flask", "db", "upgrade"],
        ["alembic", "upgrade", "head"],
        ["flask", "init-db"],
    ]
    outputs = []
    for argv in attempts:
        result = subprocess.run(
            ["docker", "compose", "-p", compose_project, "exec", "-T", "web", *argv],
            cwd=repo_dir, capture_output=True, text=True,
        )
        if result.returncode == 0:
            return
        combined = (result.stdout + result.stderr).strip()[-500:]
        outputs.append(f"{' '.join(argv)} -> {combined or '(no output, exit ' + str(result.returncode) + ')'}")

    raise RuntimeError(
        "Deploy failed at step 'Run database migrations': " + " | ".join(outputs)
    )


def _write_nginx_config(site_conf_path, site_enabled_path, server_name, port):
    config_text = f"""server {{
    listen 80;
    server_name {server_name};

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    os.makedirs(os.path.dirname(site_conf_path), exist_ok=True)
    with open(site_conf_path, "w", encoding="utf-8") as f:
        f.write(config_text)
    if not os.path.islink(site_enabled_path) and not os.path.exists(site_enabled_path):
        os.symlink(site_conf_path, site_enabled_path)


def _run(argv, step, cwd=None):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Deploy failed at step '{step}': {result.stderr.strip()[-800:]}")
