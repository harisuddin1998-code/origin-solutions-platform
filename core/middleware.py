from flask import abort, g, render_template, request

from core.db import query


def load_tenant_from_path():
    """Registered as a before_request hook on the tenant_app blueprint, whose
    routes are declared with url_prefix="/t/<tenant_subdomain>". Flask injects
    the matched path segment into view_args; we pop it, resolve the tenant,
    and enforce the kill switch before any tenant_app view runs."""
    subdomain = request.view_args.pop("tenant_subdomain", None) if request.view_args else None
    if not subdomain:
        abort(404)

    tenant = query("SELECT * FROM tenants WHERE subdomain = %s", (subdomain,), fetchone=True)
    if tenant is None:
        abort(404)

    g.tenant = tenant

    if tenant["status"] in ("suspended", "killed"):
        return render_template("tenant_app/suspended.html", tenant=tenant), 403
