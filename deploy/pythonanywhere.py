"""Push the current code to a free-tier PythonAnywhere account and reload the
web app - no SSH needed, everything goes through PythonAnywhere's REST API.

One-time setup (through the PythonAnywhere dashboard, not this script - see
README.md's "Deploying to PythonAnywhere" section):
  1. Create the web app via their "Add a new web app" wizard (manual Flask config).
  2. Set the virtualenv path and point the WSGI file at this project's `app:app`.
  3. Create a MySQL database via their control panel; put its host/credentials
     in the SERVER's own .env (not this local one - never copy secrets between them).

After that, every future push is just:
    python deploy/pythonanywhere.py

Requires `requests` (requirements-dev.txt) and PA_USERNAME/PA_API_TOKEN/PA_REMOTE_DIR
in .env (never hardcode these).
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

PA_USERNAME = os.environ.get("PA_USERNAME", "")
PA_API_TOKEN = os.environ.get("PA_API_TOKEN", "")
PA_REMOTE_DIR = os.environ.get("PA_REMOTE_DIR", "mysite")
PA_DOMAIN = os.environ.get("PA_DOMAIN") or f"{PA_USERNAME}.pythonanywhere.com"

API_BASE = f"https://www.pythonanywhere.com/api/v0/user/{PA_USERNAME}"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXCLUDED_DIRS = {"venv", ".git", "__pycache__", "agencycrm", ".pytest_cache", "node_modules"}
EXCLUDED_FILES = {".env"}  # the server has its own .env - never overwrite it from here


def iter_project_files():
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for filename in files:
            if filename in EXCLUDED_FILES or filename.endswith(".pyc"):
                continue
            local_path = os.path.join(root, filename)
            relative_path = os.path.relpath(local_path, PROJECT_ROOT).replace("\\", "/")
            yield local_path, relative_path


def upload_file(local_path, relative_path):
    remote_path = f"/home/{PA_USERNAME}/{PA_REMOTE_DIR}/{relative_path}"
    url = f"{API_BASE}/files/path{remote_path}"
    with open(local_path, "rb") as f:
        response = requests.post(
            url,
            headers={"Authorization": f"Token {PA_API_TOKEN}"},
            files={"content": (os.path.basename(local_path), f)},
        )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed ({response.status_code}): {relative_path} -> {response.text[:200]}")


def reload_webapp():
    url = f"{API_BASE}/webapps/{PA_DOMAIN}/reload/"
    response = requests.post(url, headers={"Authorization": f"Token {PA_API_TOKEN}"})
    if response.status_code != 200:
        raise RuntimeError(f"Reload failed ({response.status_code}): {response.text[:300]}")


def main():
    if not PA_USERNAME or not PA_API_TOKEN:
        print("Set PA_USERNAME and PA_API_TOKEN in .env first (get a token from your PythonAnywhere Account page).")
        sys.exit(1)

    files = list(iter_project_files())
    print(f"Uploading {len(files)} files to /home/{PA_USERNAME}/{PA_REMOTE_DIR}/ ...")

    failures = []
    for i, (local_path, relative_path) in enumerate(files, start=1):
        try:
            upload_file(local_path, relative_path)
            print(f"  [{i}/{len(files)}] {relative_path}")
        except Exception as exc:
            failures.append((relative_path, str(exc)))
            print(f"  [{i}/{len(files)}] FAILED: {relative_path} - {exc}")

    if failures:
        print(f"\n{len(failures)} file(s) failed to upload - not reloading. Fix and re-run.")
        sys.exit(1)

    print(f"Reloading {PA_DOMAIN} ...")
    reload_webapp()
    print(f"Done. Live at https://{PA_DOMAIN}")


if __name__ == "__main__":
    main()
