-- Full schema for the multi-tenant SaaS / software-house management platform.
-- Single shared database, every tenant-owned table carries tenant_id.

CREATE DATABASE IF NOT EXISTS saas_master_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE saas_master_db;

CREATE TABLE IF NOT EXISTS tenants (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(150) NOT NULL,
  subdomain     VARCHAR(63) NOT NULL UNIQUE,
  status        ENUM('active','suspended','killed') NOT NULL DEFAULT 'active',
  plan          VARCHAR(50) NOT NULL DEFAULT 'trial',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS roles (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id     INT NULL,
  role_id       INT NOT NULL,
  name          VARCHAR(150) NOT NULL,
  email         VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  status        ENUM('active','disabled') NOT NULL DEFAULT 'active',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY (role_id) REFERENCES roles(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ad_accounts (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id             INT NOT NULL,
  platform              ENUM('meta','tiktok','google') NOT NULL,
  account_name          VARCHAR(150) NOT NULL,
  external_account_id   VARCHAR(100) NOT NULL,
  status                ENUM('active','paused','disconnected') NOT NULL DEFAULT 'active',
  connected_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS whatsapp_instances (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id     INT NOT NULL,
  ad_account_id INT NULL,
  phone_number  VARCHAR(30) NOT NULL,
  display_name  VARCHAR(150) NOT NULL,
  status        ENUM('active','inactive') NOT NULL DEFAULT 'active',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY (ad_account_id) REFERENCES ad_accounts(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS leads (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id     INT NOT NULL,
  source        ENUM('meta','tiktok','whatsapp','manual') NOT NULL DEFAULT 'manual',
  name          VARCHAR(150) NOT NULL,
  phone         VARCHAR(30) NULL,
  message       TEXT NULL,
  status        ENUM('New','Contacted','Demo Scheduled','Converted','Lost') NOT NULL DEFAULT 'New',
  assigned_to   INT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS whatsapp_messages (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id             INT NOT NULL,
  whatsapp_instance_id  INT NOT NULL,
  lead_id               INT NULL,
  direction             ENUM('inbound','outbound') NOT NULL,
  body                  TEXT NOT NULL,
  sent_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY (whatsapp_instance_id) REFERENCES whatsapp_instances(id) ON DELETE CASCADE,
  FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tasks (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id     INT NULL,
  title         VARCHAR(200) NOT NULL,
  description   TEXT NULL,
  assigned_to   INT NULL,
  assigned_by   INT NULL,
  status        ENUM('todo','in_progress','qc_review','done') NOT NULL DEFAULT 'todo',
  priority      ENUM('low','medium','high') NOT NULL DEFAULT 'medium',
  due_date      DATE NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS complaints (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id     INT NULL,
  raised_by     INT NULL,
  subject       VARCHAR(200) NOT NULL,
  description   TEXT NULL,
  status        ENUM('open','in_progress','resolved') NOT NULL DEFAULT 'open',
  priority      ENUM('low','medium','high') NOT NULL DEFAULT 'medium',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY (raised_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS code_audits (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id     INT NULL,
  developer_id  INT NULL,
  file_ref      VARCHAR(255) NOT NULL,
  findings      JSON NULL,
  status        ENUM('pending','passed','failed') NOT NULL DEFAULT 'pending',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY (developer_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inventory_items (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id     INT NOT NULL,
  name          VARCHAR(150) NOT NULL,
  sku           VARCHAR(80) NOT NULL,
  quantity      INT NOT NULL DEFAULT 0,
  price         DECIMAL(10,2) NOT NULL DEFAULT 0,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pos_sales (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id     INT NOT NULL,
  item_id       INT NULL,
  quantity      INT NOT NULL DEFAULT 1,
  total         DECIMAL(10,2) NOT NULL DEFAULT 0,
  cashier_id    INT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE SET NULL,
  FOREIGN KEY (cashier_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS fleet_vehicles (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  tenant_id     INT NOT NULL,
  name          VARCHAR(150) NOT NULL,
  plate_number  VARCHAR(50) NOT NULL,
  status        ENUM('active','maintenance','inactive') NOT NULL DEFAULT 'active',
  driver_name   VARCHAR(150) NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_log (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  actor_user_id   INT NULL,
  action          VARCHAR(100) NOT NULL,
  target_type     VARCHAR(50) NULL,
  target_id       INT NULL,
  details         JSON NULL,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Internal software delivery pipeline: Dev -> QC -> Super Admin deploy.
CREATE TABLE IF NOT EXISTS projects (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(150) NOT NULL,
  description   TEXT NULL,
  subdomain     VARCHAR(63) NOT NULL UNIQUE,
  tenant_id     INT NULL,
  status        ENUM('planning','in_dev','in_qc','changes_requested','approved','live','paused','archived')
                  NOT NULL DEFAULT 'planning',
  developer_id  INT NULL,
  qc_id         INT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL,
  FOREIGN KEY (developer_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (qc_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS deployments (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  project_id        INT NOT NULL,
  version_label     VARCHAR(50) NOT NULL,
  prompt            TEXT NULL,
  ai_review_summary TEXT NULL,
  preview_url       VARCHAR(255) NULL,
  status            ENUM('building','review_ready','changes_requested','approved','deployed','failed')
                      NOT NULL DEFAULT 'building',
  triggered_by      INT NULL,
  created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (triggered_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS qc_reviews (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  deployment_id INT NOT NULL,
  reviewer_id   INT NULL,
  verdict       ENUM('approved','changes_requested') NOT NULL,
  comments      TEXT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (deployment_id) REFERENCES deployments(id) ON DELETE CASCADE,
  FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS project_id INT NULL;

-- Real GitHub-driven delivery pipeline (replaces the old AI-simulated push/review).
ALTER TABLE projects ADD COLUMN IF NOT EXISTS github_repo VARCHAR(150) NULL;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS github_webhook_secret VARCHAR(100) NULL;

ALTER TABLE deployments ADD COLUMN IF NOT EXISTS commit_sha VARCHAR(64) NULL;
ALTER TABLE deployments ADD COLUMN IF NOT EXISTS commit_message TEXT NULL;
ALTER TABLE deployments ADD COLUMN IF NOT EXISTS commit_author VARCHAR(150) NULL;
ALTER TABLE deployments ADD COLUMN IF NOT EXISTS commit_url VARCHAR(255) NULL;
ALTER TABLE deployments ADD COLUMN IF NOT EXISTS files_changed JSON NULL;

-- Manually-recorded URL for where a project's software is actually running once
-- deployed (this platform tracks the delivery pipeline, it does not host the
-- clients software itself, so Admin records the real live URL here).
ALTER TABLE projects ADD COLUMN IF NOT EXISTS live_url VARCHAR(255) NULL;

-- Automated per-client VPS deploy (Docker container per project, reverse-proxied
-- by subdomain). Port is the host-side port Nginx proxies to, container_name
-- is stored (not just recomputed) so redeploys always target the right container.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS port INT NULL;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS container_name VARCHAR(150) NULL;

-- Personal access tokens for the CLI tool (cli/pms.py). Only a hash is ever stored.
CREATE TABLE IF NOT EXISTS api_tokens (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  token_hash    CHAR(64) NOT NULL UNIQUE,
  name          VARCHAR(100) NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_used_at  TIMESTAMP NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Agency CRM: prospect/client companies, contacts, sales pipeline (deals),
-- proposals/quotations/invoicing, and a global notification center.
-- `companies` are the agency's own prospects/clients - distinct from `tenants`,
-- which are already-onboarded paying SaaS customers. A company links to a
-- tenant once its deal is won (see crm/helpers.py::provision_from_deal).
CREATE TABLE IF NOT EXISTS companies (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(150) NOT NULL,
  domain        VARCHAR(150) NULL,
  industry      VARCHAR(100) NULL,
  size          VARCHAR(50) NULL,
  phone         VARCHAR(30) NULL,
  website       VARCHAR(150) NULL,
  city          VARCHAR(100) NULL,
  country       VARCHAR(100) NULL,
  notes         TEXT NULL,
  tenant_id     INT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS contacts (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  company_id    INT NULL,
  lead_id       INT NULL,
  name          VARCHAR(150) NOT NULL,
  email         VARCHAR(150) NULL,
  phone         VARCHAR(30) NULL,
  job_title     VARCHAR(100) NULL,
  owner_id      INT NULL,
  status        ENUM('new','engaged','qualified','customer','lost') NOT NULL DEFAULT 'new',
  notes         TEXT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
  FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL,
  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS deals (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  company_id            INT NOT NULL,
  contact_id            INT NULL,
  name                  VARCHAR(200) NOT NULL,
  amount                DECIMAL(10,2) NOT NULL DEFAULT 0,
  stage                 ENUM('qualified','proposal_sent','negotiation','won','lost') NOT NULL DEFAULT 'qualified',
  probability           INT NOT NULL DEFAULT 50,
  expected_close_date   DATE NULL,
  owner_id              INT NULL,
  lost_reason           TEXT NULL,
  created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS proposals (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  deal_id       INT NOT NULL,
  title         VARCHAR(200) NOT NULL,
  content       TEXT NULL,
  status        ENUM('draft','sent','accepted','rejected') NOT NULL DEFAULT 'draft',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS quotations (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  deal_id       INT NOT NULL,
  items         JSON NULL,
  total         DECIMAL(10,2) NOT NULL DEFAULT 0,
  status        ENUM('draft','sent','accepted','rejected') NOT NULL DEFAULT 'draft',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Agency billing its own clients - distinct from tenants' internal pos_sales.
CREATE TABLE IF NOT EXISTS client_invoices (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  deal_id       INT NULL,
  company_id    INT NOT NULL,
  number        VARCHAR(50) NOT NULL UNIQUE,
  items         JSON NULL,
  subtotal      DECIMAL(10,2) NOT NULL DEFAULT 0,
  tax           DECIMAL(10,2) NOT NULL DEFAULT 0,
  discount      DECIMAL(10,2) NOT NULL DEFAULT 0,
  total         DECIMAL(10,2) NOT NULL DEFAULT 0,
  status        ENUM('draft','sent','paid','overdue','cancelled') NOT NULL DEFAULT 'draft',
  due_date      DATE NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE SET NULL,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS client_payments (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  invoice_id        INT NOT NULL,
  amount            DECIMAL(10,2) NOT NULL,
  method            VARCHAR(50) NOT NULL DEFAULT 'bank_transfer',
  transaction_ref   VARCHAR(150) NULL,
  paid_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (invoice_id) REFERENCES client_invoices(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  title         VARCHAR(200) NOT NULL,
  message       TEXT NULL,
  link          VARCHAR(255) NULL,
  is_read       BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
