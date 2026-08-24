"""Personal access tokens for the CLI tool (cli/pms.py) - separate from the
session-cookie auth every browser-facing route uses. Only a SHA-256 hash of
each token is ever stored; the raw token is shown once at generation time."""

import hashlib
import secrets
from functools import wraps

from flask import flash, g, jsonify, redirect, request

from core.auth import login_required
from core.db import execute, query


def generate_token():
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_token(user_id, name=""):
    raw = generate_token()
    execute(
        "INSERT INTO api_tokens (user_id, token_hash, name) VALUES (%s, %s, %s)",
        (user_id, hash_token(raw), name),
    )
    return raw


def require_api_token(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing 'Authorization: Bearer <token>' header."}), 401

        token = auth_header[len("Bearer ") :].strip()
        row = query(
            """
            SELECT u.id, u.tenant_id, u.name, u.email, u.status, r.name AS role,
                   t.subdomain AS tenant_subdomain, at.id AS token_id
            FROM api_tokens at
            JOIN users u ON u.id = at.user_id
            JOIN roles r ON r.id = u.role_id
            LEFT JOIN tenants t ON t.id = u.tenant_id
            WHERE at.token_hash = %s
            """,
            (hash_token(token),),
            fetchone=True,
        )
        if not row or row["status"] != "active":
            return jsonify({"error": "Invalid or revoked token."}), 401

        execute("UPDATE api_tokens SET last_used_at = CURRENT_TIMESTAMP WHERE id = %s", (row["token_id"],))
        g.user = row
        return view(*args, **kwargs)

    return wrapped


@login_required
def generate_token_view():
    name = request.form.get("name", "CLI token").strip() or "CLI token"
    raw = create_token(g.user["id"], name)
    flash(f"New API token (copy it now — shown only once): {raw}", "success")
    return redirect(request.referrer or "/")


def register(app):
    app.add_url_rule(
        "/account/api-token", endpoint="generate_api_token", view_func=generate_token_view, methods=["POST"]
    )
