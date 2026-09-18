from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from core.db import query


def load_current_user():
    """Runs on every request (registered in init_app) so g.user is always
    available to templates, regardless of whether the route requires login."""
    g.user = None
    user_id = session.get("user_id")
    if user_id:
        row = query(
            """
            SELECT u.id, u.tenant_id, u.name, u.email, u.status,
                   r.name AS role, t.subdomain AS tenant_subdomain
            FROM users u
            JOIN roles r ON r.id = u.role_id
            LEFT JOIN tenants t ON t.id = u.tenant_id
            WHERE u.id = %s
            """,
            (user_id,),
            fetchone=True,
        )
        if row and row["status"] == "active":
            g.user = row


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("auth.login", next=request.path))
            if g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def guard_role(*roles):
    """Blueprint-wide gate: bp.before_request(guard_role('super_admin'))."""

    def _guard():
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        if g.user["role"] not in roles:
            abort(403)

    return _guard


def init_app(app):
    app.before_request(load_current_user)
