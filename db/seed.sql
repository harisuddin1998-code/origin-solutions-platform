-- Sample data. Seed users (with hashed passwords) are inserted separately by db/init_db.py.
USE saas_master_db;

INSERT INTO roles (name) VALUES
  ('super_admin'), ('developer'), ('qc'), ('marketing'), ('sales'),
  ('tenant_admin'), ('tenant_staff')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO tenants (name, subdomain, status, plan) VALUES
  ('Demo Retail Co', 'tenant1', 'active', 'pro')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO ad_accounts (tenant_id, platform, account_name, external_account_id, status)
SELECT t.id, 'meta', 'Demo Retail Co - Meta Ads', 'act_1001', 'active' FROM tenants t WHERE t.subdomain = 'tenant1'
UNION ALL
SELECT t.id, 'tiktok', 'Demo Retail Co - TikTok Ads', 'tt_2002', 'active' FROM tenants t WHERE t.subdomain = 'tenant1';

INSERT INTO whatsapp_instances (tenant_id, ad_account_id, phone_number, display_name, status)
SELECT t.id, a.id, '+15550001111', 'Demo Retail Sales Line', 'active'
FROM tenants t
JOIN ad_accounts a ON a.tenant_id = t.id AND a.platform = 'meta'
WHERE t.subdomain = 'tenant1';

INSERT INTO leads (tenant_id, source, name, phone, message, status)
SELECT t.id, 'meta', 'Ayesha Khan', '+923001234567', 'Interested in the summer promo', 'New' FROM tenants t WHERE t.subdomain = 'tenant1'
UNION ALL
SELECT t.id, 'whatsapp', 'Bilal Ahmed', '+923004445566', 'Asked about pricing', 'Contacted' FROM tenants t WHERE t.subdomain = 'tenant1'
UNION ALL
SELECT t.id, 'tiktok', 'Sara Malik', '+923007778899', 'Wants a demo this week', 'Demo Scheduled' FROM tenants t WHERE t.subdomain = 'tenant1';

INSERT INTO tasks (tenant_id, title, description, status, priority)
SELECT NULL, 'Fix login redirect bug', 'Users land on 404 after login on dev subdomain', 'todo', 'high'
UNION ALL
SELECT NULL, 'Build financial report export', 'Add CSV export to Super Admin financials page', 'in_progress', 'medium';

INSERT INTO complaints (tenant_id, subject, description, status, priority)
SELECT t.id, 'POS receipt not printing', 'Thermal printer not triggered after checkout', 'open', 'medium' FROM tenants t WHERE t.subdomain = 'tenant1';

INSERT INTO inventory_items (tenant_id, name, sku, quantity, price)
SELECT t.id, 'Wireless Mouse', 'SKU-WM-001', 42, 12.50 FROM tenants t WHERE t.subdomain = 'tenant1'
UNION ALL
SELECT t.id, 'USB-C Cable', 'SKU-UC-002', 120, 5.00 FROM tenants t WHERE t.subdomain = 'tenant1';

INSERT INTO fleet_vehicles (tenant_id, name, plate_number, status, driver_name)
SELECT t.id, 'Delivery Van 1', 'LEA-1234', 'active', 'Usman Tariq' FROM tenants t WHERE t.subdomain = 'tenant1';
