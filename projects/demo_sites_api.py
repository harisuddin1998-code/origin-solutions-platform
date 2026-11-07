"""Read-only feed of the demo sites for other Origin apps.

The agency CRM (Origins OS) runs on its own box and shows the same list,
live check and traffic as the Super Admin Demo Sites page, so callers can
pick a demo to send a lead. Everything here is already public (the sites
themselves) or harmless counts, so it takes no login; it changes nothing -
restart and domain sync stay on the admin page.
"""

from flask import Blueprint, abort, current_app, jsonify

from projects import demo_sites

bp = Blueprint("demo_sites_api", __name__, url_prefix="/api/demo-sites")


@bp.after_request
def _allow_any_origin(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _public(site, domain):
    return dict(sub=site["sub"], url=f"https://{site['sub']}.{domain}", brand=site["brand"],
                niche=site["niche"], theme=site["tpl"], city=site.get("city", ""),
                accent=site.get("accent", "#7c3aed"), icon=site.get("icon", "globe"))


@bp.route("")
def list_sites():
    project = demo_sites.demos_project()
    domain = current_app.config["DEPLOY_DOMAIN"]
    sites = demo_sites.load_sites(project) if project else []
    return jsonify(showcase=f"https://{demo_sites.DEMOS_SUBDOMAIN}.{domain}",
                   sites=[_public(s, domain) for s in sites])


@bp.route("/<sub>")
def site_detail(sub):
    project = demo_sites.demos_project()
    if not project:
        abort(404)
    site = next((s for s in demo_sites.load_sites(project) if s["sub"] == sub), None)
    if not site:
        abort(404)
    domain = current_app.config["DEPLOY_DOMAIN"]
    return jsonify(site=_public(site, domain),
                   check=demo_sites.check_site(project, sub, domain),
                   traffic=demo_sites.traffic(sub, domain))
