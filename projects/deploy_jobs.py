"""Redeploys run off the request thread.

A rebuild (npm install, pip install, docker build) easily runs past the
100 seconds Cloudflare waits for an answer, and the admin then got a 524
error page while the build carried on. Worse, each retry click started
another build of the same app alongside it. So the button only starts the
deploy here and returns at once; the outcome is kept in a small status
file (CLIENT_DATA_DIR/<id>.deploy.json, beside the app's .env and outside
its data mount) that the Web Apps page shows. A file rather than memory,
because gunicorn runs several workers and any of them may serve the page.
"""

import json
import os
import threading
import time

from flask import current_app

# A deploy still marked "running" after this long died with its worker
# (e.g. a gunicorn reload) - don't let it block the button forever.
STALE_AFTER = 45 * 60


def _path(project_id):
    return os.path.join(current_app.config["CLIENT_DATA_DIR"], f"{project_id}.deploy.json")


def _write(path, status):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f)
    os.replace(tmp, path)


def status(project_id):
    """The last deploy of this project: {state: running|ok|error, message,
    started, finished}, or None if it never ran through here."""
    try:
        with open(_path(project_id), encoding="utf-8") as f:
            job = json.load(f)
    except (OSError, ValueError):
        return None
    if job.get("state") == "running" and time.time() - job.get("started", 0) > STALE_AFTER:
        job.update(state="error", message="The deploy stopped without reporting back (the server restarted mid-build?). Start it again.")
    job["minutes"] = max(0, int((time.time() - job.get("started", time.time())) // 60))
    return job


def start(project_id, run):
    """Starts run() (which returns the success message or raises) in the
    background. Returns False if this project already has a deploy running."""
    current = status(project_id)
    if current and current["state"] == "running":
        return False

    app = current_app._get_current_object()
    path = _path(project_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    started = time.time()
    _write(path, {"state": "running", "message": "", "started": started})

    def worker():
        with app.app_context():
            try:
                result = {"state": "ok", "message": run()}
            except Exception as exc:  # noqa: BLE001 - shown to the admin on the page
                result = {"state": "error", "message": str(exc)}
            result.update(started=started, finished=time.time())
            _write(path, result)

    threading.Thread(target=worker, name=f"deploy-{project_id}", daemon=True).start()
    return True
