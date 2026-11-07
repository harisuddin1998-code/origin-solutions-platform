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
  - Docker, Nginx, Git installed
  - the app's OS user in the `docker` group, plus a narrow passwordless-sudo
    rule for `nginx -t` / `systemctl reload nginx`
  - a Cloudflare Tunnel already running on this box, with its account/zone/
    tunnel IDs and API token set in .env (see config.py) - this platform has
    no public IP of its own, so every subdomain is wired up as a tunnel
    route + DNS record instead of a direct A record + Let's Encrypt cert.

Convention: every client project's repo should have a Dockerfile at its root
that listens on port 8000 internally. If it doesn't, dockerize.py makes a
best-effort guess at one (Flask, Django, FastAPI, Streamlit, Node, PHP,
Ruby, Go, or static HTML) before giving up and asking the dev to add one -
see dockerize.py for the full detection logic and the main_file_path /
start_command overrides a project can set to steer or bypass it.

A project can also pin a git branch (project.branch) - useful when the
default branch isn't what should go live.
"""

import os
import re
import shutil
import subprocess
from datetime import datetime

from flask import current_app

from core.db import execute, query
from core.secrets import decrypt_secret
from projects.cloudflare import purge_cache, wire_up_subdomain
from projects.dockerize import ensure_dockerfile

CONTAINER_PORT = 8000
# How many pre-redeploy data snapshots to keep per project.
BACKUPS_TO_KEEP = 10
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

    # Per-site logs, so the Web Apps page can attribute traffic and errors to
    # one project - the shared default log records no Host, so requests there
    # cannot be told apart.
    access_log /var/log/nginx/{server_name}.access.log;
    error_log  /var/log/nginx/{server_name}.error.log;

    # Client apps routinely accept photo and document uploads; Nginx's 1 MB
    # default rejected those before the app ever saw them. 100 MB matches the
    # ceiling Cloudflare's free plan enforces anyway, so this is as high as
    # raising it can usefully go.
    client_max_body_size 100m;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSockets: without these an upgrade request is proxied as a plain
        # HTTP one and the connection dies. Streamlit is built on them, and so
        # is anything with live chat or a realtime dashboard.
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        # Report and export endpoints regularly run past Nginx's 60s default
        # and came back as a 504 with the work still running behind it.
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }}
}}
"""


def _authed_repo_url(project):
    """Clone/fetch URL for a project's GitHub repo, carrying a stored access
    token for a PRIVATE repo. The token (if any) lives encrypted in
    github_token_enc; a public repo has none and clones over plain https."""
    repo = project["github_repo"]
    token = decrypt_secret(project.get("github_token_enc"))
    if token:
        return f"https://x-access-token:{token}@github.com/{repo}.git"
    return f"https://github.com/{repo}.git"


def _redact(text):
    """Strip an embedded access token out of any text before it reaches a log
    or the UI - git echoes the remote URL (token and all) in its errors."""
    if not text:
        return text
    return re.sub(r"(x-access-token:)[^@/\s]+(@)", r"\1***\2", text)


def _env_file_host(project_id):
    """Host path holding a project's injected .env, kept BESIDE its data dir
    (CLIENT_DATA_DIR/<id>.env) so it never lands under the app's own data
    mount (CLIENT_DATA_DIR/<id>)."""
    return os.path.join(current_app.config["CLIENT_DATA_DIR"], f"{project_id}.env")


def _write_env_file(host_path, content):
    """Writes the per-app environment file that gets mounted at /app/.env, or
    removes it when the app has none. 0600 - it holds DB passwords and keys."""
    if content:
        with open(host_path, "w", encoding="utf-8") as f:
            f.write(content if content.endswith("\n") else content + "\n")
        os.chmod(host_path, 0o600)
    elif os.path.exists(host_path):
        os.remove(host_path)


def _git(repo_dir, *args):
    return subprocess.run(["git", "-C", repo_dir, *args], check=True, capture_output=True, text=True)


def _fetch_repo(repo_dir, repo_url, branch=None):
    """Clones repo_url into repo_dir, or brings an existing clone up to date.
    GitHub is the source of truth: an existing clone is always fetched and
    hard-reset to origin/<branch> (or the checked-out branch's upstream when
    no branch is set), so a file someone edited by hand on the server can
    never block a redeploy with a merge error. Those edits aren't thrown
    away silently - they're stashed first and can be recovered with
    `git stash list` / `git stash pop` inside repo_dir."""
    if os.path.isdir(os.path.join(repo_dir, ".git")):
        if _git(repo_dir, "status", "--porcelain", "--untracked-files=no").stdout.strip():
            _git(
                repo_dir, "-c", "user.name=deploy", "-c", "user.email=deploy@localhost",
                "stash", "push", "-m", f"auto-stash before deploy {datetime.now():%Y-%m-%d %H:%M:%S}",
            )
        if branch:
            _git(repo_dir, "fetch", "origin", branch)
            _git(repo_dir, "checkout", "-f", branch)
            _git(repo_dir, "reset", "--hard", f"origin/{branch}")
        else:
            _git(repo_dir, "fetch", "origin")
            _git(repo_dir, "reset", "--hard", "@{upstream}")
    else:
        # A fresh clone. If repo_dir already holds non-git code (e.g. a
        # zip-uploaded app being converted to a GitHub repo), clear it first -
        # git clone refuses a non-empty target. Only the code lives here; the
        # app's persistent data is under CLIENT_DATA_DIR and is left untouched.
        if os.path.isdir(repo_dir) and os.listdir(repo_dir):
            shutil.rmtree(repo_dir)
        clone_cmd = ["git", "clone"]
        if branch:
            clone_cmd += ["-b", branch]
        clone_cmd += [repo_url, repo_dir]
        subprocess.run(clone_cmd, check=True, capture_output=True, text=True)


def _backup_data_dir(data_dir, project_id):
    """Snapshot a project's persistent data before a redeploy replaces its
    container.

    A redeploy is the riskiest moment for client data: the freshly built
    image runs the client app's own startup code against the mounted
    database, and some client apps clear and reseed on boot - Elite's
    elite.py calls os.remove(DB) inside init_db() on every single start.
    The bind mount in _run_container blocks that (you cannot unlink a
    bind-mount point from inside the container - it fails with EBUSY, which
    Elite's bare `except: pass` swallows), but that is the app being stopped
    by the kernel rather than by anything we control, and the next client
    app may well clear its tables with DELETE or drop_all instead, which no
    mount can stop. So take a snapshot first and keep the last
    BACKUPS_TO_KEEP of them, per project.

    No-op when a project has no persistent data yet, so a first deploy costs
    nothing.
    """
    if not os.path.isdir(data_dir) or not os.listdir(data_dir):
        return

    backups_dir = current_app.config["CLIENT_BACKUPS_DIR"]
    os.makedirs(backups_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    subprocess.run(
        ["tar", "-czf", os.path.join(backups_dir, f"{project_id}-{stamp}.tar.gz"),
         "-C", data_dir, "."],
        check=True, capture_output=True, text=True,
    )

    prefix = f"{project_id}-"
    stale = sorted(
        f for f in os.listdir(backups_dir)
        if f.startswith(prefix) and f.endswith(".tar.gz")
    )[:-BACKUPS_TO_KEEP]
    for name in stale:
        os.remove(os.path.join(backups_dir, name))


def build_deploy_plan(project):
    """Returns (steps, context) where steps is an ordered list of
    (description, argv_or_None) or (description, None, custom_action) -
    argv/custom_action is None for steps that write a file or shell out via a
    plain lambda rather than a single argv command. Nothing is executed
    here."""
    domain = current_app.config["DEPLOY_DOMAIN"]
    apps_dir = current_app.config["CLIENT_APPS_DIR"]
    data_dir = os.path.join(current_app.config["CLIENT_DATA_DIR"], str(project["id"]))
    env_file_host = _env_file_host(project["id"])

    port = allocate_port(project)
    container = container_name_for(project)
    repo_dir = os.path.join(apps_dir, str(project["id"]))
    repo_url = _authed_repo_url(project) if project.get("github_repo") else None
    branch = project.get("branch")
    subdomain = project["subdomain"]
    server_name = f"{subdomain}.{domain}"
    site_conf_path = os.path.join(NGINX_SITES_AVAILABLE, f"{server_name}.conf")
    site_enabled_path = os.path.join(NGINX_SITES_ENABLED, f"{server_name}.conf")

    fetch_description = f"Fetch latest code for {project['name']}"
    if branch:
        fetch_description += f" (branch: {branch})"

    # A project uploaded as a zip has no repo to pull from - its code was
    # written straight into repo_dir when it was created, and a redeploy
    # rebuilds from whatever is sitting there now. Everything after this
    # step is identical either way.
    if project.get("github_repo"):
        fetch_step = (fetch_description, None, lambda: _fetch_repo(repo_dir, repo_url, branch))
    elif os.path.isdir(repo_dir):
        fetch_step = (f"Use uploaded code already at {repo_dir}", None, lambda: None)
    else:
        raise ValueError(
            f"{project['name']} has no GitHub repo and no uploaded code at {repo_dir} "
            "- nothing to deploy."
        )

    steps = [
        (
            f"Back up existing data for {project['name']} before redeploying",
            None,
            lambda: _backup_data_dir(data_dir, project["id"]),
        ),
        fetch_step,
        (
            "Ensure a Dockerfile exists at repo root (auto-generated if missing)",
            None,
            lambda: ensure_dockerfile(repo_dir, project.get("main_file_path"), project.get("start_command")),
        ),
        (f"Build Docker image {container}", ["docker", "build", "-t", container, repo_dir]),
        (
            f"Stop old container {container} (if running)",
            None,
            lambda: subprocess.run(["docker", "rm", "-f", container], capture_output=True, text=True),
        ),
        (
            f"Write the environment file for {project['name']}",
            None,
            lambda: _write_env_file(env_file_host, decrypt_secret(project.get("env_file_enc"))),
        ),
        (
            f"Start container {container} on port {port}",
            None,
            lambda: _run_container(container, port, data_dir, project.get("data_mount_path"), _dockerfile_port(repo_dir), env_file_host),
        ),
        (
            f"Write Nginx config for {server_name}",
            None,
            lambda: _write_nginx_config(site_conf_path, site_enabled_path, subdomain, domain, port),
        ),
        ("Validate Nginx config", ["sudo", "nginx", "-t"]),
        ("Reload Nginx", ["sudo", "systemctl", "reload", "nginx"]),
        (
            f"Wire up {server_name} on the Cloudflare Tunnel (DNS + route)",
            None,
            lambda: wire_up_subdomain(subdomain, domain),
        ),
        (
            f"Purge cached copies of {server_name} so the new code is what visitors get",
            None,
            lambda: purge_cache(server_name),
        ),
    ]
    context = {"port": port, "container": container, "server_name": server_name, "domain": domain}
    return steps, context


def _dockerfile_port(repo_dir):
    """The port the container actually listens on, taken from the first
    EXPOSE line of its Dockerfile. Auto-generated Dockerfiles all EXPOSE
    CONTAINER_PORT, but a repo's own custom Dockerfile may listen on any
    port (e.g. digportal/#37 on 6013) - publishing the host port to a
    hard-coded 8000 then yields a 502 because nothing is listening there.
    Falls back to CONTAINER_PORT when no EXPOSE is found."""
    try:
        with open(os.path.join(repo_dir, "Dockerfile"), encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r"\s*EXPOSE\s+(\d+)", line, re.IGNORECASE)
                if m:
                    return int(m.group(1))
    except OSError:
        pass
    return CONTAINER_PORT


def _run_container(container, port, data_dir, mount_path=None, container_port=None, env_file_host=None):
    """Every single-container deploy gets a persistent per-project data
    mount, whether or not the app actually uses it - harmless if unused.
    Defaults to /data, which is what dockerize.py's Django template points
    a SQLite db.sqlite3 at (see _write_django). A project with its own
    pre-existing Dockerfile that expects its persistent data somewhere else
    can set project.data_mount_path to override the container-side
    path(s) - comma-separated for more than one. Each entry is either a
    directory (e.g. gracelogistics'/PSG's "/app/instance") mounted from
    data_dir itself, or a specific file (e.g. "/app/fleet.db" for an app
    whose whole SQLite db sits at its WORKDIR root, detected by a "." in
    the last path segment) mounted from that same filename under data_dir,
    so it doesn't mask anything else living alongside it in the image -
    Elite needs two such file mounts (it keeps two separate .db files at
    its root). Several projects (MIB, PSG, Elite, Dost Muhammad) had no
    persistent mount at all until this - see the 2026-09-17
    gracelogistics/al_murad incidents this generalizes the fix from."""
    os.makedirs(data_dir, exist_ok=True)
    entries = [e.strip() for e in (mount_path or "/data").split(",") if e.strip()]
    # Several directories that must each survive a rebuild (e.g. /app/data AND
    # /app/history) cannot all be aliased onto data_dir - they would then share
    # one host folder and clobber each other. When there is more than one
    # directory entry, give each its own host subdir (data_dir/app_data,
    # data_dir/app_history, ...). A lone directory still maps straight to
    # data_dir, so every existing single-mount app is unaffected.
    dir_count = sum(1 for e in entries if "." not in os.path.basename(e))
    volume_args = []
    for entry in entries:
        base = os.path.basename(entry)
        if "." in base:
            host_source = os.path.join(data_dir, base)
            if not os.path.exists(host_source):
                open(host_source, "a").close()
        elif dir_count > 1:
            host_source = os.path.join(data_dir, entry.strip("/").replace("/", "_"))
            os.makedirs(host_source, exist_ok=True)
        else:
            host_source = data_dir
        volume_args += ["-v", f"{host_source}:{entry}"]
    # A private-repo build ships no .env (it is gitignored); the platform
    # mounts the per-app environment file in at runtime instead, so the app
    # gets its DB password etc. without the secret ever entering the image.
    if env_file_host and os.path.exists(env_file_host):
        volume_args += ["-v", f"{env_file_host}:/app/.env:ro"]
    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", container,
            "--restart", "unless-stopped",
            "-p", f"127.0.0.1:{port}:{container_port or CONTAINER_PORT}",
            *volume_args,
            container,
        ],
        check=True, capture_output=True, text=True,
    )


def _write_nginx_config(site_conf_path, site_enabled_path, subdomain, domain, port):
    config_text = render_nginx_config(subdomain, domain, port)
    os.makedirs(os.path.dirname(site_conf_path), exist_ok=True)
    with open(site_conf_path, "w", encoding="utf-8") as f:
        f.write(config_text)
    if not os.path.islink(site_enabled_path) and not os.path.exists(site_enabled_path):
        os.symlink(site_conf_path, site_enabled_path)



def _head_commit(repo_dir):
    """The commit that just went live, so "did my push actually deploy?" is
    answerable from the button's own result instead of by guessing. None for
    an uploaded project, which has no commits to report."""
    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", repo_dir, "log", "-1", "--format=%h%s%cr"],
            capture_output=True, text=True, timeout=10, check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    parts = proc.stdout.strip().split("")
    if len(parts) != 3 or not parts[0]:
        return None
    return {"sha": parts[0], "message": parts[1], "when": parts[2]}

def execute_deploy(project_id, dry_run=False):
    project = query("SELECT * FROM projects WHERE id = %s", (project_id,), fetchone=True)
    if not project:
        raise ValueError(f"Project {project_id} not found.")

    # Repos that ship a docker-compose.yml (Postgres/Redis/Celery-backed apps,
    # not just a single Dockerfile) need a different deploy path - see
    # compose_deploy.py. Checked before cloning, over the network, so it can
    # also flag this in a dry-run preview without side effects.
    from projects.compose_deploy import deploy_compose_stack, repo_has_compose_file

    is_compose = bool(project.get("github_repo")) and repo_has_compose_file(project["github_repo"])

    if is_compose and not dry_run:
        apps_dir = current_app.config["CLIENT_APPS_DIR"]
        repo_dir = os.path.join(apps_dir, str(project["id"]))
        repo_url = _authed_repo_url(project)
        try:
            _fetch_repo(repo_dir, repo_url, project.get("branch"))
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"Deploy failed at step 'Fetch latest code for {project['name']}': {_redact(exc.stderr)}"
            ) from exc

        context = deploy_compose_stack(project, repo_dir)
        live_url = f"https://{context['server_name']}"
        execute("UPDATE projects SET status = 'live', live_url = %s WHERE id = %s", (live_url, project_id))
        execute(
            "UPDATE deployments SET status = 'deployed' WHERE project_id = %s AND status = 'approved'",
            (project_id,),
        )
        return {
        "dry_run": False,
        "live_url": live_url,
        "context": context,
        "commit": _head_commit(
            os.path.join(current_app.config["CLIENT_APPS_DIR"], str(project_id))
        ),
    }

    steps, context = build_deploy_plan(project)

    if dry_run:
        return {
            "dry_run": True,
            "compose_stack": is_compose,
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
            raise RuntimeError(f"Deploy failed at step '{description}': {_redact(detail)}") from exc

    live_url = f"https://{context['server_name']}"
    execute("UPDATE projects SET status = 'live', live_url = %s WHERE id = %s", (live_url, project_id))
    execute(
        "UPDATE deployments SET status = 'deployed' WHERE project_id = %s AND status = 'approved'",
        (project_id,),
    )
    return {
        "dry_run": False,
        "live_url": live_url,
        "context": context,
        "commit": _head_commit(
            os.path.join(current_app.config["CLIENT_APPS_DIR"], str(project_id))
        ),
    }
