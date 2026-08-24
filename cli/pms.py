#!/usr/bin/env python
"""Small CLI for the platform - run from VS Code's integrated terminal (or
any terminal). Talks to the app's token-authenticated API (core/cli_api.py),
not the browser session - generate a token from your portal dashboard first.

Usage:
    python cli/pms.py login <token>
    python cli/pms.py whoami
    python cli/pms.py projects
    python cli/pms.py status
    python cli/pms.py deploy <project_id>      (super_admin tokens only)
    python cli/pms.py deploy <project_id> --dry-run   (preview steps, no changes)
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

TOKEN_FILE = Path.home() / ".pms_token"
API_URL = os.environ.get("PMS_API_URL", "http://127.0.0.1:5000").rstrip("/")


def load_token():
    if not TOKEN_FILE.exists():
        print("Not logged in. Run: python cli/pms.py login <token>")
        sys.exit(1)
    return TOKEN_FILE.read_text().strip()


def request(method, path, **kwargs):
    token = load_token()
    response = requests.request(
        method, f"{API_URL}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=15, **kwargs
    )
    try:
        data = response.json()
    except ValueError:
        print(f"Unexpected response ({response.status_code}): {response.text[:200]}")
        sys.exit(1)

    if response.status_code >= 400:
        print(f"Error: {data.get('error', response.text)}")
        sys.exit(1)
    return data


def cmd_login(args):
    TOKEN_FILE.write_text(args.token.strip())
    TOKEN_FILE.chmod(0o600)
    print(f"Token saved to {TOKEN_FILE}")


def cmd_whoami(_args):
    print(json.dumps(request("GET", "/api/cli/whoami"), indent=2))


def cmd_projects(_args):
    print(json.dumps(request("GET", "/api/cli/projects"), indent=2))


def cmd_status(_args):
    print(json.dumps(request("GET", "/api/cli/status"), indent=2))


def cmd_deploy(args):
    path = f"/api/cli/deploy/{args.project_id}"
    if args.dry_run:
        path += "?dry_run=1"
    print(json.dumps(request("POST", path), indent=2))


def main():
    parser = argparse.ArgumentParser(prog="pms", description="Platform management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_login = sub.add_parser("login", help="Save your API token locally")
    p_login.add_argument("token")
    p_login.set_defaults(func=cmd_login)

    sub.add_parser("whoami", help="Show the current token's identity").set_defaults(func=cmd_whoami)
    sub.add_parser("projects", help="List your projects").set_defaults(func=cmd_projects)
    sub.add_parser("status", help="Show your open tasks / pending QC items").set_defaults(func=cmd_status)

    p_deploy = sub.add_parser("deploy", help="Deploy an approved project (super_admin only)")
    p_deploy.add_argument("project_id", type=int)
    p_deploy.add_argument(
        "--dry-run", action="store_true", help="Preview the deploy steps without running anything (containerized projects only)"
    )
    p_deploy.set_defaults(func=cmd_deploy)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
