from flask import Blueprint, redirect, render_template, request, session, url_for

from core.db import query
from core.security import verify_password

bp = Blueprint("auth", __name__, template_folder="templates")

ROLE_HOME = {
    "super_admin": lambda user: url_for("super_admin.dashboard"),
    "developer": lambda user: url_for("dev_portal.dashboard"),
    "qc": lambda user: url_for("qc_portal.dashboard"),
    "marketing": lambda user: url_for("marketing.dashboard"),
    "sales": lambda user: url_for("sales.dashboard"),
    "tenant_admin": lambda user: url_for("tenant_app.dashboard", tenant_subdomain=user["tenant_subdomain"]),
    "tenant_staff": lambda user: url_for("tenant_app.dashboard", tenant_subdomain=user["tenant_subdomain"]),
}


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = query(
            """
            SELECT u.id, u.password_hash, u.status, r.name AS role, t.subdomain AS tenant_subdomain
            FROM users u
            JOIN roles r ON r.id = u.role_id
            LEFT JOIN tenants t ON t.id = u.tenant_id
            WHERE u.email = %s
            """,
            (email,),
            fetchone=True,
        )

        if not user or user["status"] != "active" or not verify_password(user["password_hash"], password):
            error = "Invalid email or password."
        else:
            session.clear()
            session["user_id"] = user["id"]
            home = ROLE_HOME.get(user["role"])
            return redirect(home(user) if home else url_for("auth.login"))

    return render_template("auth/login.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
