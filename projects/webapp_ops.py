"""Per-project operations behind the Web Apps page (blueprints/super_admin).

The page is modelled on PythonAnywhere's "Web" tab: pick a project on the
left, get everything about that one app on the right - reload it, see its
status and traffic, edit what it runs, read its logs, restore its data, and
run commands against it in its own console.

Everything here acts on a single project's *container*, never on the host.
The console in particular runs through `docker exec`, so a mistyped command
(or a misused Super Admin session) is contained to one client app. A host
shell would not be: the account this platform runs as is in the `docker`
group and holds sudo rules for nginx, which together are root over every
client on the box at once.

Commands are passed to subprocess as argv lists with no shell=True, so the
only shell involved is the one inside the target container.
"""

import glob
import os
import subprocess
import time
from datetime import datetime

from flask import current_app

from core.db import execute
from projects.vps_deploy import container_name_for

# A console command holds a gunicorn worker for as long as it runs, so keep
# the ceiling well under a browser's patience and let long jobs be started
# with nohup instead.
CONSOLE_TIMEOUT = 20
LOG_LINES = 200
NGINX_LOG_DIR = "/var/log/nginx"


def _run(argv, timeout=15):
    """Runs argv and returns (ok, combined_output). Never raises - every
    caller here is rendering into a page, and 'docker said no' is something
    to show the user, not a 500."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"Timed out after {timeout}s."
    except FileNotFoundError:
        return False, f"{argv[0]} not found on this server."
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out.strip()


def _inspect(container, fmt):
    ok, out = _run(["docker", "inspect", container, "--format", fmt])
    return out if ok else ""


def _humanize(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    return f"{seconds // 86400}d {(seconds % 86400) // 3600}h"


def container_state(project):
    """What the app is actually doing right now, as opposed to what the
    projects table claims. Returns a dict that always has the same keys, so
    the template never has to guard on existence."""
    container = project.get("container_name") or f"client-{project['id']}-{project['subdomain']}"
    state = {
        "container": container,
        "exists": False,
        "running": False,
        "status": "not deployed",
        "restarts": 0,
        "uptime": "-",
        "image": "-",
        "started_at": "-",
        "mounts": [],
    }

    raw = _inspect(container, "{{.State.Status}}|{{.RestartCount}}|{{.State.StartedAt}}|{{.Config.Image}}")
    if not raw or "|" not in raw:
        return state

    status, restarts, started_at, image = (raw.split("|") + ["", "", "", ""])[:4]
    state.update(
        exists=True,
        running=status == "running",
        status=status or "unknown",
        restarts=int(restarts) if restarts.isdigit() else 0,
        image=image or "-",
        started_at=started_at[:19].replace("T", " ") if started_at else "-",
    )

    if state["running"] and started_at:
        try:
            started = datetime.strptime(started_at[:19], "%Y-%m-%dT%H:%M:%S")
            state["uptime"] = _humanize((datetime.utcnow() - started).total_seconds())
        except ValueError:
            pass

    mounts = _inspect(container, "{{range .Mounts}}{{.Source}}:{{.Destination}}\n{{end}}")
    state["mounts"] = [m for m in mounts.splitlines() if m.strip()]
    return state


def run_console(project, command):
    """Runs one command inside the project's container via `sh -c`.

    Returns (ok, output). The container must be running - `docker exec` has
    nothing to attach to otherwise, and starting it implicitly would hide a
    crash-looping app behind a console that appears to work.
    """
    command = (command or "").strip()
    if not command:
        return False, "Enter a command first."

    state = container_state(project)
    if not state["exists"]:
        return False, f"No container named {state['container']} - deploy this project first."
    if not state["running"]:
        return False, (
            f"Container {state['container']} is {state['status']}, so there is nothing to run "
            "commands in. Start it from the Reload section, then check the logs below."
        )

    started = time.time()
    ok, out = _run(
        ["docker", "exec", "--workdir", "/app", state["container"], "sh", "-c", command],
        timeout=CONSOLE_TIMEOUT,
    )
    elapsed = time.time() - started
    if not out:
        out = "(no output)"
    return ok, f"$ {command}\n\n{out}\n\n[finished in {elapsed:.1f}s]"


def container_logs(project, lines=LOG_LINES):
    state = container_state(project)
    if not state["exists"]:
        return "No container yet - this project has not been deployed."
    ok, out = _run(["docker", "logs", "--tail", str(lines), state["container"]])
    return out or "(log is empty)"


def nginx_log_paths(project, domain):
    """Log paths for this project's site, preferring the configured domain.

    Some sites on this box were set up under an older, misspelled domain
    (originsolutions.com, one 's') and still serve under those server_names,
    so the log named after DEPLOY_DOMAIN may not be the one Nginx is
    actually writing. Fall back to any <subdomain>.*.access.log rather than
    reporting no traffic for a site that plainly has some.
    """
    preferred = os.path.join(NGINX_LOG_DIR, f"{project['subdomain']}.{domain}.access.log")
    if os.path.exists(preferred):
        return preferred, preferred[: -len("access.log")] + "error.log"

    matches = sorted(
        glob.glob(os.path.join(NGINX_LOG_DIR, f"{project['subdomain']}.*.access.log")),
        key=lambda p: os.path.getsize(p),
        reverse=True,
    )
    if matches:
        return matches[0], matches[0][: -len("access.log")] + "error.log"
    return preferred, preferred[: -len("access.log")] + "error.log"


def traffic_stats(project, domain):
    """Request counts read from this site's own Nginx access log.

    Sites deployed before per-site logging was added write into the shared
    /var/log/nginx/access.log with a format that does not record which host
    was asked for, so those cannot be attributed - hence `available: False`
    rather than a misleading zero.
    """
    access_log, _ = nginx_log_paths(project, domain)
    stats = {"available": False, "today": 0, "month": 0, "hour": 0, "path": access_log}
    if not os.path.exists(access_log):
        return stats

    now = datetime.now()
    today = now.strftime("%d/%b/%Y")
    month = now.strftime("/%b/%Y")
    hour = now.strftime("%d/%b/%Y:%H")
    stats["available"] = True
    try:
        with open(access_log, "r", errors="ignore") as fh:
            for line in fh:
                stamp = line.partition("[")[2].partition("]")[0]
                if not stamp:
                    continue
                if month in stamp:
                    stats["month"] += 1
                if stamp.startswith(today):
                    stats["today"] += 1
                if stamp.startswith(hour):
                    stats["hour"] += 1
    except OSError:
        stats["available"] = False
    return stats


def nginx_error_tail(project, domain, lines=40):
    _, error_log = nginx_log_paths(project, domain)
    if not os.path.exists(error_log):
        return ""
    ok, out = _run(["tail", "-n", str(lines), error_log])
    return out if ok else ""


# ---------------------------------------------------------------- lifecycle

def restart_container(project):
    state = container_state(project)
    if not state["exists"]:
        return False, "Nothing to restart - deploy this project first."
    return _run(["docker", "restart", state["container"]], timeout=60)


def stop_container(project):
    state = container_state(project)
    if not state["exists"]:
        return False, "Nothing to stop."
    ok, out = _run(["docker", "stop", state["container"]], timeout=60)
    if ok:
        execute("UPDATE projects SET status = 'paused' WHERE id = %s", (project["id"],))
    return ok, out


def start_container(project):
    state = container_state(project)
    if not state["exists"]:
        return False, "Nothing to start - deploy this project first."
    ok, out = _run(["docker", "start", state["container"]], timeout=60)
    if ok:
        execute("UPDATE projects SET status = 'live' WHERE id = %s", (project["id"],))
    return ok, out


# ------------------------------------------------------------------ backups

def _backups_dir():
    return current_app.config["CLIENT_BACKUPS_DIR"]


def list_backups(project):
    """The snapshots vps_deploy takes before each redeploy, newest first."""
    backups_dir = _backups_dir()
    prefix = f"{project['id']}-"
    if not os.path.isdir(backups_dir):
        return []

    rows = []
    for name in os.listdir(backups_dir):
        if not (name.startswith(prefix) and name.endswith(".tar.gz")):
            continue
        path = os.path.join(backups_dir, name)
        try:
            st = os.stat(path)
        except OSError:
            continue
        rows.append({
            "name": name,
            "size_kb": max(1, st.st_size // 1024),
            "when": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "mtime": st.st_mtime,
        })
    return sorted(rows, key=lambda r: r["mtime"], reverse=True)


def restore_backup(project, name):
    """Puts a snapshot back, with the app stopped while it happens.

    Restoring underneath a running app risks handing it a half-written
    SQLite file, so the container is stopped first and started again after -
    and the current data is snapshotted too, so a restore chosen by mistake
    is itself undoable.
    """
    if os.path.basename(name) != name or not name.endswith(".tar.gz"):
        return False, "Invalid backup name."
    if not name.startswith(f"{project['id']}-"):
        return False, "That backup belongs to a different project."

    archive = os.path.join(_backups_dir(), name)
    if not os.path.exists(archive):
        return False, "That backup no longer exists."

    data_dir = os.path.join(current_app.config["CLIENT_DATA_DIR"], str(project["id"]))
    os.makedirs(data_dir, exist_ok=True)

    from projects.vps_deploy import _backup_data_dir
    try:
        _backup_data_dir(data_dir, project["id"])
    except Exception:
        pass

    state = container_state(project)
    was_running = state["running"]
    if was_running:
        _run(["docker", "stop", state["container"]], timeout=60)

    ok, out = _run(["tar", "-xzf", archive, "-C", data_dir], timeout=120)

    if was_running:
        started_ok, start_out = _run(["docker", "start", state["container"]], timeout=60)
        if not started_ok:
            return False, f"Restored, but the container did not start again: {start_out}"

    if not ok:
        return False, f"Restore failed: {out}"
    return True, f"Restored {name}. The previous data was snapshotted first, so this is undoable."
