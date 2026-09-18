"""Fully and permanently removes a project's live deployment: stops its
container(s), deletes its Nginx vhost, unwires its Cloudflare DNS record +
tunnel route, and deletes its cloned repo directory from disk. Used by
Super Admin's "Remove" button (see blueprints/super_admin/routes.py::
delete_project_route) right before the project's DB row itself is deleted.

Unlike Pause (projects/helpers.py::pause_project), which stops a container
but keeps everything else so Resume can bring it straight back, this is
irreversible - redeploying afterwards starts completely from scratch
(fresh clone, fresh containers, fresh DNS).

Best-effort throughout: a project that was only partially deployed (or
already manually cleaned up) shouldn't block removal just because one step
finds nothing to do. Every step's failure is collected and returned instead
of raised, so the caller can still delete the DB row and report what, if
anything, needs manual cleanup.
"""

import os
import shutil
import subprocess

from flask import current_app

from projects.cloudflare import remove_subdomain

NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled"


def teardown_project(project):
    """Returns a list of non-fatal error strings (empty if everything went
    cleanly) - the caller deletes the DB row regardless."""
    errors = []
    apps_dir = current_app.config["CLIENT_APPS_DIR"]
    repo_dir = os.path.join(apps_dir, str(project["id"]))

    if project.get("container_name"):
        is_compose = os.path.isfile(os.path.join(repo_dir, "docker-compose.yml"))
        if is_compose:
            # A compose stack's container_name column only tracks the "web"
            # service; tearing it down properly (Postgres/Redis/Celery too,
            # plus its network and volumes) needs `docker compose down -v`
            # against the same project name compose_deploy.py used.
            compose_project = f"client{project['id']}"
            result = subprocess.run(
                ["docker", "compose", "-p", compose_project, "down", "-v"],
                cwd=repo_dir, capture_output=True, text=True,
            )
            if result.returncode != 0:
                errors.append(f"docker compose down: {result.stderr.strip()[-300:]}")
        else:
            result = subprocess.run(
                ["docker", "rm", "-f", project["container_name"]], capture_output=True, text=True
            )
            if result.returncode != 0 and "No such container" not in result.stderr:
                errors.append(f"docker rm: {result.stderr.strip()[-300:]}")

    if project.get("subdomain"):
        domain = current_app.config["DEPLOY_DOMAIN"]
        server_name = f"{project['subdomain']}.{domain}"
        site_conf_path = os.path.join(NGINX_SITES_AVAILABLE, f"{server_name}.conf")
        site_enabled_path = os.path.join(NGINX_SITES_ENABLED, f"{server_name}.conf")

        removed_nginx_config = False
        for path in (site_enabled_path, site_conf_path):
            try:
                if os.path.islink(path) or os.path.exists(path):
                    os.remove(path)
                    removed_nginx_config = True
            except OSError as exc:
                errors.append(f"remove {path}: {exc}")

        if removed_nginx_config:
            subprocess.run(["sudo", "nginx", "-t"], capture_output=True, text=True)
            subprocess.run(["sudo", "systemctl", "reload", "nginx"], capture_output=True, text=True)

        try:
            remove_subdomain(project["subdomain"], domain)
        except RuntimeError as exc:
            errors.append(str(exc))

    if os.path.isdir(repo_dir):
        try:
            shutil.rmtree(repo_dir)
        except OSError as exc:
            errors.append(f"remove {repo_dir}: {exc}")

    return errors
