# Agency CRM — Architecture Plan

## Tech Stack
- **Frontend**: React 18 + TypeScript + Vite + React Router v6
- **Backend**: FastAPI (Python) + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Styling**: Custom CSS with premium design system
- **Auth**: JWT-based (mock for now)

## Database Schema

### Core
- `users` — id, name, email, role, avatar, created_at
- `contacts` — id, user_id, name, company, email, phone, website, social_links, tags, notes, source, status, created_at, updated_at
- `companies` — id, name, domain, phone, address, city, state, country, website, linkedin, industry, size, notes, created_at

### Sales
- `pipelines` — id, name, stages (JSON), created_at
- `deals` — id, pipeline_id, contact_id, company_id, name, amount, stage, probability, expected_close_date, lost_reason, owner_id, created_at, updated_at

### Email
- `email_templates` — id, name, subject, body, variables (JSON), created_at
- `email_sequences` — id, name, steps (JSON), status, created_at
- `email_settings` — id, user_id, provider (smtp/gmail/office365), host, port, username, password, created_at
- `email_log` — id, deal_id, contact_id, template_id, subject, body, sent_at, opened_at, clicked_at

### Tasks & Calendar
- `tasks` — id, title, description, assigned_to, due_date, status, priority, related_to (contact/deal), created_at
- `events` — id, title, description, start_time, end_time, all_day, related_to, created_at

### Projects
- `projects` — id, deal_id, name, description, status, start_date, deadline, client_approved, created_at
- `project_members` — id, project_id, user_id, role
- `milestones` — id, project_id, name, due_date, completed

### Invoices & Payments
- `invoices` — id, deal_id, contact_id, number, items (JSON), subtotal, tax, discount, total, status, due_date, created_at
- `payments` — id, invoice_id, amount, method, transaction_id, paid_at

### Proposals & Quotations
- `proposals` — id, deal_id, contact_id, content (JSON), status, sent_at, signed_at, created_at
- `quotations` — id, deal_id, contact_id, items (JSON), total, status, created_at

### Automation
- `workflows` — id, name, trigger (JSON), actions (JSON), status, created_at

### Notifications
- `notifications` — id, user_id, title, message, type, read, link, created_at

## API Structure
```
/api/auth/       — login, register, profile
/api/contacts/   — CRUD + search + import/export
/api/companies/  — CRUD
/api/pipelines/  — CRUD + stages
/api/deals/      — CRUD + stage transitions
/api/email/      — templates, sequences, settings, send
/api/tasks/      — CRUD
/api/calendar/   — events CRUD
/api/projects/   — CRUD + members + milestones
/api/invoices/   — CRUD + payments
/api/proposals/  — CRUD
/api/quotations/ — CRUD
/api/automation/ — workflows CRUD
/api/notifications/ — list + mark read
/api/reports/    — aggregated data
/api/ai/         — AI-powered features
```

## Frontend Structure
```
src/
  components/     — reusable UI (Button, Card, Modal, Table, Kanban, etc.)
  pages/          — route-level pages
  services/       — API client
  hooks/          — custom hooks
  utils/          — helpers
  types/          — TypeScript interfaces
  contexts/       — Auth, Theme, etc.
  layouts/        — App shell, Sidebar, Topbar
```

## Build Order (Module by Module)
1. Project setup + Design System
2. Authentication & Shell
3. Dashboard
4. CRM (Contacts, Companies)
5. Pipelines & Deals
6. Email (Templates, Sequences, Settings)
7. Tasks & Calendar
8. Projects
9. Invoices & Payments
10. Proposals & Quotations
11. Automation Builder
12. Reporting & Analytics
13. AI Features
14. Polish & Performance
</｜｜DSML｜｜>