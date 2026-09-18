"""The "Add a new web app" wizard: getting a brand-new project onto the box.

Two ways in, matching what Super Admin actually does:

  - **From GitHub** - paste owner/repo, the deploy pipeline clones it and
    keeps pulling on every later redeploy.
  - **Upload a .zip** - for code that isn't on GitHub. The zip is unpacked
    straight into the project's source directory once; there is nothing to
    pull from afterwards, so a redeploy rebuilds from whatever is there
    (re-upload to change it).

Both end at the same place: a project row, code in CLIENT_APPS_DIR/<id>, and
the ordinary deploy pipeline from there on.
"""

import os
import re
import shutil
import tempfile
import zipfile

from core.db import execute, query
from projects.github import generate_webhook_secret, unique_subdomain

# A .zip big enough to matter here is almost always a venv or node_modules
# that was never meant to ship, so refuse it with an explanation rather than
# spending minutes unpacking it.
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 600 * 1024 * 1024

# Junk that should never make it into a deploy, and that bloats the upload.
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "venv", ".venv", "env",
             ".pytest_cache", ".mypy_cache", ".idea", ".vscode", "__MACOSX"}


class WizardError(Exception):
    """Something the user can read and act on, not a bug."""


def normalize_subdomain(raw):
    """Same shape as unique_subdomain() produces, so a typed subdomain and a
    generated one can't end up in different formats."""
    return re.sub(r"[^a-z0-9]+", "-", (raw or "").lower()).strip("-")[:63]


def subdomain_taken(subdomain, exclude_project_id=None):
    if exclude_project_id:
        row = query(
            "SELECT id FROM projects WHERE subdomain = %s AND id <> %s",
            (subdomain, exclude_project_id), fetchone=True,
        )
    else:
        row = query("SELECT id FROM projects WHERE subdomain = %s", (subdomain,), fetchone=True)
    return bool(row)


def create_project(name, subdomain, github_repo=None, developer_id=None, branch=None):
    """The project row both wizard paths end up creating."""
    name = (name or "").strip()
    if not name:
        raise WizardError("Give the app a name.")

    subdomain = normalize_subdomain(subdomain) or unique_subdomain(name)
    if subdomain_taken(subdomain):
        raise WizardError(
            f"{subdomain} is already taken by another app. Pick a different one."
        )

    return execute(
        """
        INSERT INTO projects
            (name, subdomain, status, developer_id, github_repo, github_webhook_secret, branch)
        VALUES (%s, %s, 'in_dev', %s, %s, %s, %s)
        """,
        (name, subdomain, developer_id, github_repo or None,
         generate_webhook_secret() if github_repo else None, branch or None),
    )


def _safe_members(zf, dest_root):
    """Yields (member, target_path) for entries worth extracting.

    A zip can name entries like ../../etc/nginx/nginx.conf or point a symlink
    outside the tree; extracting one of those would write wherever the entry
    says. Every target is resolved and checked to sit under dest_root, and
    anything else is skipped rather than trusted.
    """
    dest_root = os.path.realpath(dest_root)
    total = 0
    for member in zf.infolist():
        name = member.filename
        if name.endswith("/"):
            continue
        parts = name.replace("\\", "/").split("/")
        if any(p in SKIP_DIRS for p in parts) or any(p.startswith("._") for p in parts):
            continue

        target = os.path.realpath(os.path.join(dest_root, name))
        if target != dest_root and not target.startswith(dest_root + os.sep):
            continue  # escapes the destination - drop it

        total += member.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise WizardError(
                "That zip expands to more than 600 MB. Remove venv/, node_modules/ "
                "and other build output, then upload again."
            )
        yield member, target


def _strip_single_root(paths):
    """Zips made by 'compress this folder' nest everything under one folder,
    so app.py arrives as myproject/app.py and the Dockerfile lands a level
    above the code. Detect that one shared folder and drop it."""
    tops = {p.replace("\\", "/").split("/")[0] for p in paths}
    if len(tops) != 1:
        return None
    top = tops.pop()
    if any(p.replace("\\", "/") == top for p in paths):
        return None  # it's a file at the root, not a wrapping folder
    return top


def extract_zip(file_storage, repo_dir):
    """Unpacks an uploaded .zip into repo_dir, replacing whatever is there."""
    filename = (file_storage.filename or "").strip()
    if not filename.lower().endswith(".zip"):
        raise WizardError("Upload a .zip file (zip the project folder first).")

    # Werkzeug hands small uploads over as a SpooledTemporaryFile, which on
    # Python 3.10 has no .seekable until it rolls over to disk - and zipfile
    # needs one. Spill it to a real temp file first, which also keeps a large
    # upload off the heap.
    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        file_storage.save(tmp.name)
        size = os.path.getsize(tmp.name)
        if size == 0:
            raise WizardError("That file is empty.")
        if size > MAX_UPLOAD_BYTES:
            raise WizardError(
                f"That zip is {size // (1024 * 1024)} MB; the limit is "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB. "
                "Remove venv/ and node_modules/ first."
            )

        try:
            zf = zipfile.ZipFile(tmp.name)
        except zipfile.BadZipFile:
            raise WizardError("That file isn't a readable .zip.")

        with zf:
            members = list(_safe_members(zf, repo_dir))
            if not members:
                raise WizardError("That zip has no usable files in it.")

            strip = _strip_single_root([m.filename for m, _ in members])

            if os.path.isdir(repo_dir):
                shutil.rmtree(repo_dir)
            os.makedirs(repo_dir, exist_ok=True)

            written = 0
            for member, _ in members:
                rel = member.filename.replace("\\", "/")
                if strip:
                    rel = rel[len(strip) + 1:]
                    if not rel:
                        continue
                target = os.path.join(repo_dir, rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with zf.open(member) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                written += 1

    return written
