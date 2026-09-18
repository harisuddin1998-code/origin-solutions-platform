"""Wires a deployed project's subdomain into the shared Cloudflare Tunnel:
one DNS CNAME to the tunnel, plus one ingress rule so the tunnel knows which
local Nginx vhost to hand that hostname's traffic to. Both are idempotent --
safe to call again on a redeploy. remove_subdomain() reverses both, for
projects/teardown.py when a project is permanently removed.
"""

import requests
from flask import current_app

API_BASE = "https://api.cloudflare.com/client/v4"

# Cloudflare's "record already exists" error code -- not a failure for us.
DNS_RECORD_EXISTS = 81053


def _headers():
    return {
        "Authorization": f"Bearer {current_app.config['CLOUDFLARE_API_TOKEN']}",
        "Content-Type": "application/json",
    }


def ensure_dns_record(subdomain):
    zone_id = current_app.config["CLOUDFLARE_ZONE_ID"]
    tunnel_target = current_app.config["CLOUDFLARE_TUNNEL_TARGET"]

    resp = requests.post(
        f"{API_BASE}/zones/{zone_id}/dns_records",
        headers=_headers(),
        json={"type": "CNAME", "name": subdomain, "content": tunnel_target, "proxied": True},
        timeout=15,
    )
    data = resp.json()
    if data.get("success"):
        return
    if any(err.get("code") == DNS_RECORD_EXISTS for err in data.get("errors", [])):
        return
    raise RuntimeError(f"Cloudflare DNS record for '{subdomain}' failed: {data.get('errors')}")


def ensure_tunnel_route(hostname, service="http://localhost:80"):
    account_id = current_app.config["CLOUDFLARE_ACCOUNT_ID"]
    tunnel_id = current_app.config["CLOUDFLARE_TUNNEL_ID"]
    url = f"{API_BASE}/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations"

    current = requests.get(url, headers=_headers(), timeout=15).json()
    if not current.get("success"):
        raise RuntimeError(f"Could not read tunnel config: {current.get('errors')}")

    ingress = current["result"]["config"]["ingress"]
    if any(rule.get("hostname") == hostname for rule in ingress):
        return

    catch_all = ingress[-1] if ingress and "hostname" not in ingress[-1] else {"service": "http_status:404"}
    routes = [rule for rule in ingress if "hostname" in rule]
    routes.append({"hostname": hostname, "service": service})
    routes.append(catch_all)

    resp = requests.put(url, headers=_headers(), json={"config": {"ingress": routes}}, timeout=15)
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Cloudflare tunnel route for '{hostname}' failed: {data.get('errors')}")


def wire_up_subdomain(subdomain, domain):
    """Adds the DNS record and tunnel route for <subdomain>.<domain> - safe to
    call every deploy, not just the first one."""
    ensure_dns_record(subdomain)
    ensure_tunnel_route(f"{subdomain}.{domain}")


def purge_cache(hostname):
    """Drops Cloudflare's cached copies of a site, right after it redeploys.

    Without this a redeploy looks like it did nothing. Cloudflare caches
    static assets at the edge and rewrites the browser's Cache-Control along
    the way - this zone hands out max-age=14400 even though the origin says
    no-cache - so a pushed CSS or JS change stays invisible for hours while
    the app itself is perfectly up to date.

    Purging by hostname is an Enterprise-only feature, so fall back to
    purging the whole zone when the API refuses it. That is heavier than it
    needs to be (every project's assets get re-fetched once) but it is
    correct, and the alternative is shipping changes nobody can see.

    Never raises: a deploy that worked should not be reported as failed
    because a cache purge didn't.
    """
    zone_id = current_app.config.get("CLOUDFLARE_ZONE_ID")
    if not zone_id:
        return False, "No Cloudflare zone configured - skipped."

    url = f"{API_BASE}/zones/{zone_id}/purge_cache"
    try:
        resp = requests.post(url, headers=_headers(), json={"hosts": [hostname]}, timeout=20)
        data = resp.json()
        if data.get("success"):
            return True, f"Purged Cloudflare cache for {hostname}."

        resp = requests.post(url, headers=_headers(), json={"purge_everything": True}, timeout=20)
        data = resp.json()
        if data.get("success"):
            return True, "Purged the whole Cloudflare zone cache (per-host purge needs Enterprise)."
        return False, f"Cloudflare would not purge the cache: {data.get('errors')}"
    except requests.RequestException as exc:
        return False, f"Could not reach Cloudflare to purge the cache: {exc}"


def remove_dns_record(subdomain, domain):
    zone_id = current_app.config["CLOUDFLARE_ZONE_ID"]

    resp = requests.get(
        f"{API_BASE}/zones/{zone_id}/dns_records",
        headers=_headers(),
        params={"type": "CNAME", "name": f"{subdomain}.{domain}"},
        timeout=15,
    )
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Could not look up DNS record for '{subdomain}': {data.get('errors')}")

    for record in data.get("result", []):
        del_resp = requests.delete(
            f"{API_BASE}/zones/{zone_id}/dns_records/{record['id']}", headers=_headers(), timeout=15
        )
        del_data = del_resp.json()
        if not del_data.get("success"):
            raise RuntimeError(f"Could not delete DNS record for '{subdomain}': {del_data.get('errors')}")


def remove_tunnel_route(hostname):
    account_id = current_app.config["CLOUDFLARE_ACCOUNT_ID"]
    tunnel_id = current_app.config["CLOUDFLARE_TUNNEL_ID"]
    url = f"{API_BASE}/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations"

    current = requests.get(url, headers=_headers(), timeout=15).json()
    if not current.get("success"):
        raise RuntimeError(f"Could not read tunnel config: {current.get('errors')}")

    ingress = current["result"]["config"]["ingress"]
    if not any(rule.get("hostname") == hostname for rule in ingress):
        return

    routes = [rule for rule in ingress if rule.get("hostname") != hostname]

    resp = requests.put(url, headers=_headers(), json={"config": {"ingress": routes}}, timeout=15)
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Cloudflare tunnel route removal for '{hostname}' failed: {data.get('errors')}")


def remove_subdomain(subdomain, domain):
    """Reverses wire_up_subdomain - removes the DNS record and tunnel route
    for <subdomain>.<domain>. Safe to call even if nothing was ever wired
    up (e.g. a project that was added but never successfully deployed)."""
    remove_dns_record(subdomain, domain)
    remove_tunnel_route(f"{subdomain}.{domain}")
