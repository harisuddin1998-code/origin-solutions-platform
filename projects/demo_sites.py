"""Behind the Demo Sites page (blueprints/super_admin).

All the industry demo sites run inside ONE web app - the project whose
subdomain is "demos". Its nginx container picks a folder from the Host header,
so every demo is just a folder under sites/ plus a hostname. This module
lists those sites (from the manifest the generator writes), checks one is
actually answering, counts its traffic, and wires hostnames onto the box:
a local nginx alias that sends each demo hostname to the demos container,
one Cloudflare DNS record per site, and the matching tunnel ingress routes.
"""

import html
import json
import os
import re
import subprocess
import time
from datetime import datetime

import requests
from flask import current_app

from core.db import query
from projects.cloudflare import API_BASE, _headers, ensure_dns_record

DEMOS_SUBDOMAIN = "demos"
ALIAS_AVAILABLE = "/etc/nginx/sites-available/demo-sites.aliases.conf"
ALIAS_ENABLED = "/etc/nginx/sites-enabled/demo-sites.aliases.conf"
ACCESS_LOG = "/var/log/nginx/demo-sites.access.log"


def demos_project():
    return query("SELECT * FROM projects WHERE subdomain = %s", (DEMOS_SUBDOMAIN,), fetchone=True)


def sites_dir(project):
    return os.path.join(current_app.config["CLIENT_APPS_DIR"], str(project["id"]), "sites")


def load_sites(project):
    """Every demo site, in generator order. Folders added by hand that the
    manifest doesn't know about still appear, as plain 'Custom site' rows."""
    root = sites_dir(project)
    try:
        with open(os.path.join(root, DEMOS_SUBDOMAIN, "sites.json"), encoding="utf-8") as f:
            sites = json.load(f)
    except (OSError, ValueError):
        sites = []

    known = {s["sub"] for s in sites}
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            if name == DEMOS_SUBDOMAIN or name in known:
                continue
            if os.path.isfile(os.path.join(root, name, "index.html")):
                sites.append(dict(sub=name, brand=name, niche="Custom site", tpl="custom", city="",
                                  accent="#7c3aed", accent2="#22d3ee", icon="globe"))
    return sites


def site_files(project, sub):
    folder = os.path.join(sites_dir(project), sub)
    rows = []
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                st = os.stat(path)
                rows.append(dict(name=name, size_kb=max(1, st.st_size // 1024),
                                 modified=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")))
    return folder, rows


def check_site(project, sub, domain):
    """Asks the demos container for this one site, the way the tunnel will -
    so a wrong folder or a broken page shows up here, not to a customer."""
    port = project.get("port")
    if not port:
        return dict(ok=False, code=None, ms=None, error="The demos app has no port yet - deploy it first.")
    started = time.time()
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/", headers={"Host": f"{sub}.{domain}"}, timeout=5)
    except requests.RequestException as exc:
        return dict(ok=False, code=None, ms=None, error=str(exc)[:160])
    match = re.search(r"<title>(.*?)</title>", resp.text, re.S)
    return dict(ok=resp.status_code == 200, code=resp.status_code, ms=int((time.time() - started) * 1000),
                size_kb=max(1, len(resp.content) // 1024),
                title=html.unescape(match.group(1)).strip() if match else "")


def traffic(sub, domain):
    """Requests for one demo hostname, read from the shared alias log - its
    lines start with the Host (see render_alias_conf), so they can be split
    per site."""
    stats = {"available": False, "today": 0, "month": 0, "hour": 0}
    if not os.path.exists(ACCESS_LOG):
        return stats
    prefix = f"{sub}.{domain} "
    now = datetime.now()
    today, month, hour = now.strftime("%d/%b/%Y"), now.strftime("/%b/%Y"), now.strftime("%d/%b/%Y:%H")
    stats["available"] = True
    try:
        with open(ACCESS_LOG, "r", errors="ignore") as fh:
            for line in fh:
                if not line.startswith(prefix):
                    continue
                stamp = line.partition("[")[2].partition("]")[0]
                if month in stamp:
                    stats["month"] += 1
                if stamp.startswith(today):
                    stats["today"] += 1
                if stamp.startswith(hour):
                    stats["hour"] += 1
    except OSError:
        stats["available"] = False
    return stats


def is_wired(sub, domain):
    try:
        with open(ALIAS_AVAILABLE, encoding="utf-8") as f:
            return f" {sub}.{domain}" in f.read().replace("\n", " ")
    except OSError:
        return False


def render_alias_conf(project, subs, domain):
    names = "\n        ".join(f"{s}.{domain}" for s in subs)
    return (
        f"# Managed by the Demo Sites page for project #{project['id']} - regenerated on\n"
        "# every 'Sync domains'. Each demo hostname goes to the one demos container,\n"
        "# which picks the folder from the Host header.\n"
        "log_format demo_sites_host '$host [$time_local] \"$request\" $status $body_bytes_sent \"$http_referer\"';\n\n"
        "server {\n"
        "    listen 80;\n"
        f"    server_name\n        {names};\n"
        f"    access_log {ACCESS_LOG} demo_sites_host;\n"
        "    error_log  /var/log/nginx/demo-sites.error.log;\n\n"
        "    location / {\n"
        f"        proxy_pass http://127.0.0.1:{project['port']};\n"
        "        proxy_set_header Host $host;\n"
        "        proxy_set_header X-Real-IP $remote_addr;\n"
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        "        proxy_set_header X-Forwarded-Proto $scheme;\n"
        "    }\n"
        "}\n"
    )


def wire_all(project):
    """Makes every site folder reachable at <folder>.<domain>. Idempotent -
    run it after adding a new site folder. Returns (ok, message)."""
    domain = current_app.config["DEPLOY_DOMAIN"]
    subs = sorted(s["sub"] for s in load_sites(project))
    if not subs:
        return False, "No site folders found - deploy the demos app first."

    # 1) local nginx alias, validated before it can take nginx down
    previous = None
    if os.path.exists(ALIAS_AVAILABLE):
        with open(ALIAS_AVAILABLE, encoding="utf-8") as f:
            previous = f.read()
    with open(ALIAS_AVAILABLE, "w", encoding="utf-8") as f:
        f.write(render_alias_conf(project, subs, domain))
    if not os.path.exists(ALIAS_ENABLED):
        os.symlink(ALIAS_AVAILABLE, ALIAS_ENABLED)
    test = subprocess.run(["sudo", "nginx", "-t"], capture_output=True, text=True)
    if test.returncode != 0:
        if previous is not None:
            with open(ALIAS_AVAILABLE, "w", encoding="utf-8") as f:
                f.write(previous)
        return False, "Nginx rejected the new config, so nothing changed: " + test.stderr[-300:]
    subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=True)

    # 2) + 3) Cloudflare: DNS for hostnames the tunnel doesn't know yet, then
    # one tunnel update with all of them (not one PUT per site)
    account = current_app.config["CLOUDFLARE_ACCOUNT_ID"]
    tunnel = current_app.config["CLOUDFLARE_TUNNEL_ID"]
    url = f"{API_BASE}/accounts/{account}/cfd_tunnel/{tunnel}/configurations"
    current = requests.get(url, headers=_headers(), timeout=20).json()
    if not current.get("success"):
        return False, f"Could not read the tunnel config: {current.get('errors')}"
    ingress = current["result"]["config"]["ingress"]
    have = {rule.get("hostname") for rule in ingress}
    new_hosts = [f"{s}.{domain}" for s in subs if f"{s}.{domain}" not in have]

    failed = []
    for host in new_hosts:
        try:
            ensure_dns_record(host.split(".")[0])
        except RuntimeError as exc:
            failed.append(f"{host}: {exc}")
        time.sleep(0.15)

    if new_hosts:
        catch_all = ingress[-1] if ingress and "hostname" not in ingress[-1] else {"service": "http_status:404"}
        routes = [rule for rule in ingress if "hostname" in rule]
        routes += [{"hostname": h, "service": "http://localhost:80"} for h in new_hosts]
        resp = requests.put(url, headers=_headers(), json={"config": {"ingress": routes + [catch_all]}}, timeout=30).json()
        if not resp.get("success"):
            return False, f"Tunnel update failed: {resp.get('errors')}"

    msg = f"{len(subs)} sites wired; {len(new_hosts)} new hostname(s) added."
    if failed:
        return False, msg + " DNS failed for: " + "; ".join(failed[:5])
    return True, msg
