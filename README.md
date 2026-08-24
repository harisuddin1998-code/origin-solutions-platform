# Software House Management Platform

Flask + MySQL multi-tenant SaaS / software-house management platform with 6
role-based portals. Everything is real: a manual task-assignment flow, a
GitHub-webhook-driven Dev → QC → Deploy pipeline (QC reviews actual commits,
not AI-generated text), an Agency CRM (companies/deals/invoices), and a small
CLI for scripting against the platform from a terminal. Deployable to a
single-hostname host like PythonAnywhere (everything is path-based, no
subdomains or WebSockets required).

## 1. Prerequisites

- Python 3.10 (`py -3.10 --version`)
- A local MySQL server (MySQL 8.x / MariaDB) running and reachable

## 2. Set up the virtual environment

```
py -3.10 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure environment variables

`.env` already exists in this project with a `FLASK_SECRET_KEY` generated.
Open it and set `MYSQL_PASSWORD` (and `MYSQL_USER`/`MYSQL_HOST` if your local
MySQL isn't `root` on `127.0.0.1`) — leave `MYSQL_PASSWORD` empty if you're
using a default XAMPP/WAMP MySQL install (no root password).

`.env.example` is the template if you ever need to recreate `.env`.

## 4. Create and seed the database

```
python db/init_db.py
```

This creates the `saas_master_db` database, runs `db/schema.sql`, runs
`db/seed.sql` (tenant1 + sample ad accounts/leads/tasks/inventory), and
inserts demo login users. It's safe to re-run for schema/role/tenant changes,
but will duplicate the sample leads/tasks/etc rows if re-run — for a clean
slate, drop `saas_master_db` first.

**Demo accounts** (password for all: `Passw0rd!`):

| Portal | Path | Email |
|---|---|---|
| Super Admin | `/admin` | superadmin@demo.local |
| Developer | `/dev` | dev@demo.local |
| QC | `/qc` | qc@demo.local |
| Marketing Hub | `/marketing` | marketing@demo.local |
| Sales & Call Center | `/sales` | sales@demo.local |
| Tenant (Demo Retail Co) | `/t/tenant1` | admin@tenant1.local |

## 5. Run the server

```
python app.py
```

Starts on `http://127.0.0.1:5000`. Log in at `http://127.0.0.1:5000/login` —
you'll be redirected to the right portal path automatically based on your
role, or go straight to any path in the table above.

## 6. Assigning work (Super Admin)

**Tasks**: Super Admin → **Tasks** → **+ New Task** — pick a user, optionally
a project, fill in the rest, done. No chat, no NLP — a plain form.

**Projects**: Super Admin → **Projects** — each row has Developer/QC dropdown
selects to staff a project directly.

## 7. The real Dev → QC → Deploy pipeline

1. As the assigned developer, open a project in the Dev Portal and connect it
   to a GitHub repo (`owner/repo`). You get back a webhook secret and a
   payload URL.
2. On GitHub: repo → **Settings** → **Webhooks** → **Add webhook** → paste
   the payload URL, set content type to `application/json`, paste the
   secret, and set it to fire on **just the push event**.
3. Every real `git push` now lands in QC's queue automatically — the actual
   commit message, author, and changed files, not a simulated summary.
4. QC reviews it (Approve / Request Changes) from `/qc`.
5. Once approved, Super Admin hits **Deploy** on the Projects page (or
   `python cli/pms.py deploy <project_id>` from a terminal).

**Testing this locally**: GitHub can't reach `127.0.0.1`. Either run
`ngrok http 5000` and use the ngrok URL as the payload URL, or simulate a
push yourself:

```bash
python - <<'EOF'
import hmac, hashlib, json, requests
secret = "<paste the project's webhook secret>"
payload = json.dumps({
    "head_commit": {
        "id": "abc1234567890",
        "message": "Fix the login redirect bug",
        "author": {"name": "Dana Developer"},
        "url": "https://github.com/owner/repo/commit/abc1234",
        "added": [], "removed": [], "modified": ["app.py"],
    }
}).encode()
sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
requests.post(
    "http://127.0.0.1:5000/webhooks/github/<project_id>",
    data=payload,
    headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": sig, "Content-Type": "application/json"},
)
EOF
```

## 8. CLI tool (`cli/pms.py`)

Run from VS Code's integrated terminal (or any terminal) once you've
generated a token from your portal dashboard's "API Access" box:

```
pip install -r requirements-dev.txt   # once, for the `requests` library
python cli/pms.py login <token>
python cli/pms.py whoami
python cli/pms.py projects
python cli/pms.py status
python cli/pms.py deploy <project_id>   # super_admin tokens only
```

`PMS_API_URL` env var overrides the default `http://127.0.0.1:5000`.

## 9. Try the mocked Marketing → Sales lead flow

1. Go to the Marketing Hub → **WhatsApp Inbox** (or Overview) and click
   **Simulate Incoming Lead**.
2. That page and the Sales **Lead Funnel** both poll every ~10s, so the new
   lead shows up shortly without a manual refresh (see "Polling" below).

The same fabrication logic backs `GET /mock/meta/leads`, `GET
/mock/tiktok/leads`, and `POST /mock/whatsapp/webhook` (needs an
`X-Webhook-Token` header matching `WHATSAPP_WEBHOOK_TOKEN` in `.env`) if you
want to hit them directly with curl/Postman. These stay mocked deliberately —
they stand in for paid ad platform APIs, unlike the Dev/QC pipeline which is
now fully real.

## Going live: resetting demo data

Before deploying for real, run this **instead of** `db/init_db.py`:

```
python db/reset_demo_data.py
```

It creates the schema and seeds only `roles` plus one real Super Admin login
you provide interactively (name/email/password) — no demo tenants, leads,
deals, or projects ship to production. Safe to re-run; it never deletes data.

## Deploying to PythonAnywhere

**One-time setup** (through their dashboard, not a script):
1. Create the web app via their "Add a new web app" wizard → manual Flask
   config → point it at a virtualenv and set the WSGI file to import
   `app:app` from wherever you'll put the code (default assumed: `mysite`,
   configurable via `PA_REMOTE_DIR` in `.env`).
2. Create a MySQL database via their "Databases" tab, and put *that* host's
   credentials in the **server's own `.env`** (never copy your local `.env`
   over — `deploy/pythonanywhere.py` deliberately skips uploading `.env` so
   it can never clobber the server's).
3. Get an API token from your PythonAnywhere "Account" page.

**Every push after that:**
```
pip install -r requirements-dev.txt   # once, for the `requests` library
python deploy/pythonanywhere.py
```
Reads `PA_USERNAME`/`PA_API_TOKEN`/`PA_REMOTE_DIR` from `.env`, uploads every
changed file via PythonAnywhere's Files API, and reloads the web app — no SSH
needed (works on the free tier).

## Deploying the platform itself (on-premise / VPS, one-time)

This is separate from `projects/vps_deploy.py` (which deploys *client*
projects as their own Docker containers) - this section is the one-time
setup for the main Super Admin/Dev/QC/Sales/Tenant app itself on a Linux
server you control (a rented VPS, or a physical machine on your own
network).

**Prerequisites**: Ubuntu (or similar) server, MySQL, Nginx, Certbot
(`python3-certbot-nginx`), Git, Python 3.10+, Docker (only needed if you'll
also use `projects/vps_deploy.py` for client deploys) - and a domain whose
DNS A record (and, for client deploys, a wildcard `*` A record) points at
this server's public IP.

1. `git clone` this repo onto the server, then:
   ```
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt -r requirements-prod.txt
   ```
2. Create a real `.env` on the server (never copy your local dev `.env` -
   put real `MYSQL_*` credentials, a fresh `FLASK_SECRET_KEY`, and your real
   `DEPLOY_DOMAIN`/`DEPLOY_ADMIN_EMAIL` in it).
3. Seed the database for production - use `python db/reset_demo_data.py`,
   **not** `db/init_db.py` (see "Going live: resetting demo data" above).
4. Install and start the Gunicorn service:
   - Edit the `REPLACE_WITH_*` placeholders in
     [deploy/gunicorn_originsolutions.service](deploy/gunicorn_originsolutions.service)
   - `sudo cp deploy/gunicorn_originsolutions.service /etc/systemd/system/originsolutions.service`
   - `sudo systemctl daemon-reload && sudo systemctl enable --now originsolutions`
5. Install the Nginx vhost and get a certificate:
   - Edit the `REPLACE_WITH_*` placeholders in
     [deploy/nginx_originsolutions.conf.example](deploy/nginx_originsolutions.conf.example)
   - Follow the numbered steps in that file's header comment (copy into
     `sites-available`, symlink into `sites-enabled`, `nginx -t`, reload,
     then run the `certbot` command shown there)

After this one-time setup, `https://<your-domain>` serves the platform
itself. From there, Super Admin's **Deploy** button on the Projects page
handles every *client* project going live on its own subdomain
automatically (see `projects/vps_deploy.py`) - no repeat of this section
needed per client.

## Project layout

```
app.py                app factory + entrypoint
config.py              .env-backed Config
core/                   db access, auth/RBAC, tenant-path+kill-switch middleware,
                          api_auth.py (CLI token auth), cli_api.py (CLI's own API)
blueprints/               one package per portal (auth, super_admin, dev_portal, qc_portal, marketing, sales, tenant_app)
crm/                       agency CRM (companies/deals/invoices) + notifications
projects/                   Dev -> QC -> Deploy pipeline; github.py + webhook_api.py handle real GitHub pushes
mock_integrations/         fake Meta/TikTok/WhatsApp endpoints + shared fake-lead helper (still mocked, deliberately)
db/                          schema.sql, seed.sql, init_db.py, reset_demo_data.py
deploy/                       deploy/pythonanywhere.py
cli/                          pms.py - terminal tool talking to core/cli_api.py
templates/, static/           shared base layout, polling JS
```

## Notes

- **Path-based routing, not subdomains**: every portal lives under its own
  path prefix (`/admin`, `/dev`, `/qc`, `/marketing`, `/sales`,
  `/t/<tenant_subdomain>`) rather than a subdomain. This is deliberate so the
  app runs unmodified on hosts (like PythonAnywhere's free tier) that don't
  support wildcard subdomains.
- **Polling, not WebSockets**: pages that would benefit from an instant push
  (WhatsApp inbox, lead funnel, project boards, the notification bell) poll
  on an interval instead (`static/js/poll-refresh.js`, `static/js/notif-bell.js`)
  — a deliberate trade-off for hosts without WebSocket support. The tenant
  kill switch itself doesn't need polling: it's enforced in
  `core/middleware.py` on every request regardless.
- **No AI in this pipeline on purpose**: an earlier version had Gemini
  generating simulated code reviews from a developer's text prompt. It's been
  removed entirely in favor of the real GitHub webhook flow above.
- Tailwind is loaded via CDN (`cdn.tailwindcss.com`) — no Node/npm build step.
  Fine for a small deployment; swap for a compiled build if it ever matters.
- Multi-tenant isolation uses raw SQL (PyMySQL) with `tenant_id` filters
  written explicitly into every tenant-scoped query — see `core/db.py`.
