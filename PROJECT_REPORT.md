# Origin Solutions — Project Report

**Prepared:** 18 August 2026
**Purpose:** a complete picture of what this platform does and how it's built, for merging with another CRM system.

---

## 1. What this project is

A multi-tenant SaaS platform that runs an entire software house's internal
operations — not a demo, a working system: a real GitHub-webhook-driven
Dev → QC → Deploy pipeline, a real Agency CRM (companies/deals/invoices), a
real multi-source lead scraper, and six role-based portals tying it together.

Stack: **Flask + MySQL** on the backend, server-rendered **Jinja + Tailwind**
(via CDN, no build step) on the frontend, deployed **path-based** rather than
by subdomain (`/admin`, `/dev`, `/qc`, `/marketing`, `/sales`,
`/t/<tenant_subdomain>`) so it runs unmodified on hosts without wildcard
subdomain support.

## 2. Core objectives

1. Let a Super Admin run the whole business from one place — staffing,
   deployments, finances, client complaints — without touching a database
   directly.
2. Give Sales a real pipeline: capture leads (from ad platforms, or now from
   an in-app scraper), convert them to deals, and hand off to delivery.
3. Make the Dev → QC → Deploy pipeline reflect *real* work — actual GitHub
   commits reviewed by QC, not a simulated approval step.
4. Give each client (tenant) their own branded, isolated app instance,
   deployable to its own subdomain with one click.
5. Centralize the agency's own commercial paperwork — invoices, proposals,
   quotations — against the same deals Sales is working.

## 3. Portals and what each one owns

| Portal | Path | Objective |
|---|---|---|
| **Auth** | `/login` | Session-based login, role-based redirect to the right portal home |
| **Super Admin** | `/admin` | Command center: tenant lifecycle, project staffing, task assignment, agency financials, user directory, client complaints. Rebuilt today with a left-sidebar layout (was a top-nav layout shared with every other portal). |
| **Developer Portal** | `/dev` | Connect a project to a GitHub repo, get a webhook secret; every real `git push` lands here automatically |
| **QC Portal** | `/qc` | Review actual commits (message, author, changed files) from the webhook — Approve / Request Changes, not an AI-generated review |
| **Marketing Hub** | `/marketing` | Simulated Meta/TikTok/WhatsApp lead capture — deliberately mocked (see §5) — feeding the same `leads` table Sales works from |
| **Sales & Call Center** | `/sales` | Lead funnel, lead → deal conversion, companies, deals, tasks, and — new — **Lead Generation**: a real scraper (Google Search + Facebook + LinkedIn + optional Google Places API) that finds and scores businesses as leads directly inside the portal |
| **Tenant App** | `/t/<subdomain>` | The client-facing side of the platform once a tenant is provisioned |

## 4. Agency CRM (`crm/`)

Not a separate app — a shared module used by Super Admin and Sales:

- **Companies** and **Contacts** — the account layer under every deal
- **Deals** — pipeline stages (`qualified → proposal_sent → negotiation → won/lost`), with a `won` deal auto-provisioning a new tenant login
- **Proposals** and **Quotations** — attached per deal
- **Invoices** and **Payments** — attached per deal or per company, with a `pay` action recording the payment
- **Notifications** — in-app bell, used e.g. when Sales forwards a deal to Super Admin

This is the layer most likely to overlap with your boss's existing CRM —
worth comparing field-for-field before merging (see §8).

## 5. What's real vs intentionally mocked

| Feature | Status |
|---|---|
| Dev → QC → Deploy pipeline | **Real** — actual GitHub webhooks, signature-verified |
| Agency CRM (companies/deals/invoices/proposals/quotations) | **Real** |
| Lead Generation scraper (Sales) | **Real** — live Google/Facebook/LinkedIn scraping, contact extraction, lead scoring |
| Per-client VPS deploy (`projects/vps_deploy.py`) | **Real** — one Docker container + Nginx vhost + Let's Encrypt cert per client, on approval |
| Meta / TikTok / WhatsApp lead capture | **Mocked, by design** — stands in for paid ad-platform APIs until a client actually needs the real integration; see `mock_integrations/` |
| CLI tool (`cli/pms.py`) | **Real** — scriptable terminal access via personal API tokens |

## 6. Two adjacent projects in this repo

Both exist alongside the main Flask app and are relevant context for the merge:

- **`agencycrm/`** — a standalone React + TypeScript + Vite frontend with a
  FastAPI backend. Built as a *visual/UX reference*: a polished sidebar
  dashboard, Kanban pipeline board, and card-based layout. Its Python
  environment was broken (pointed at a Python install no longer on this
  machine) and has been repaired. Its look is what today's Super Admin
  redesign was modeled on.
- **`lead generation/`** — a standalone FastAPI scraper ("LeadGen Pro") that
  used to run as its own separate app on port 8000. Its entire engine has
  now been ported into `blueprints/sales/lead_engine.py` and its UI rebuilt
  as `blueprints/sales/templates/sales/lead_generation.html`, so the
  capability lives inside the Sales portal instead of as a fourth standalone
  service. The original standalone copy is left in place, unmodified, as
  the source reference.

## 7. Data model (key tables)

- **Identity/tenancy:** `users`, `roles`, `tenants`
- **Sales/CRM:** `leads`, `companies`, `contacts`, `deals`, `proposals`,
  `quotations`, `client_invoices`, `payments`
- **Delivery:** `projects`, `tasks`, `deployments`
- **Governance:** `complaints`, `audit_log`, `notifications`

Multi-tenant isolation is enforced with explicit `tenant_id` filters on every
tenant-scoped query (raw SQL via PyMySQL, no ORM) — see `core/db.py`.

## 8. Merging with the other CRM — what to line up

Before merging, map these against your boss's CRM to see what's duplicate vs
complementary:

- **Likely overlapping:** contacts, companies, deals/pipeline stages,
  invoices, proposals/quotations, notifications — standard CRM territory
  both systems probably already do.
- **Likely unique to this platform:** the Dev → QC → Deploy pipeline, the
  per-client Docker+subdomain provisioning, the lead-generation scraper, the
  multi-portal role structure (Dev/QC/Marketing/Tenant on top of
  Sales/Admin). If the other CRM is sales-only, these are the parts worth
  keeping rather than replacing.
- **Data migration point:** if contacts/deals move into the other CRM's
  schema, the `tenant_id`-scoped queries throughout `core/`, `crm/`, and
  `blueprints/sales/` will need updating to match — this is the main
  engineering cost of a merge, not the UI.

## 9. Production-readiness gaps (before either system goes live for real clients)

- No CSRF protection on forms yet (plain POSTs throughout)
- No password-reset flow — only seeded demo passwords
- No automated tests
- The lead scraper should be rate-limited before heavy use (it visits
  Google/Facebook/LinkedIn on demand)
- Minimum viable hosting: a single 4 GB/2 vCPU VPS (~$5–7/month all-in) comfortably
  runs the platform plus roughly 10–20 lightweight client deployments; see
  `projects/vps_deploy.py` for how each client's container is provisioned.

## 10. Changes made in this session

- Repaired `agencycrm`'s broken Python virtual environment (Python 3.12 no
  longer installed on this machine — recreated with the available interpreter
  and reinstalled dependencies)
- Ported the standalone lead-generation scraper into the Sales portal as
  `blueprints/sales/lead_engine.py` + `blueprints/sales/templates/sales/lead_generation.html`,
  wired to new routes in `blueprints/sales/routes.py`; verified end-to-end
  with a live search
- Added `requests`, `beautifulsoup4`, `pandas`, `openpyxl` to
  `requirements.txt` for the scraper's dependencies
- Rebuilt the Super Admin portal on a new sidebar layout
  (`blueprints/super_admin/templates/super_admin/_layout.html`), replacing
  the shared top-nav layout for that portal only — every other portal is
  unchanged
