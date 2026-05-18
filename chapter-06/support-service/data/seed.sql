-- Chapter 6 — deterministic seed data for the Customer 360 service.
-- 8 customers, 20 orders, 3 incidents (one resolved — must NOT appear in tool output).

-- Customers --------------------------------------------------------------
INSERT INTO customers (email, name, plan_tier, is_vip, signup_date, prior_ticket_count) VALUES
  ('alice@acme.test',       'Alice Nakamura',   'pro',        1, '2023-04-14',  5),
  ('bob@globex.test',       'Bob Ortega',       'enterprise', 1, '2021-11-02', 12),
  ('carla@initech.test',    'Carla Schmidt',    'pro',        0, '2024-02-09',  2),
  ('dan@umbrella.test',     'Dan Wright',       'free',       0, '2025-01-20',  0),
  ('erin@hooli.test',       'Erin Olofsson',    'enterprise', 0, '2022-08-15',  4),
  ('felix@piedpiper.test',  'Felix Mendez',     'pro',        0, '2024-09-30',  1),
  ('greta@tyrell.test',     'Greta Rasmussen',  'free',       0, '2025-03-11',  0),
  ('hiro@wayne.test',       'Hiro Tanaka',      'pro',        0, '2023-12-01',  3);

-- Orders (20 rows across customers) --------------------------------------
INSERT INTO orders (order_id, customer_email, placed_at, status, total_usd, items_json) VALUES
  ('ord_001', 'alice@acme.test',      '2026-03-01T10:12:00Z', 'delivered', 129.00, '["Pro seat annual renewal"]'),
  ('ord_002', 'alice@acme.test',      '2026-04-10T08:41:00Z', 'refunded',   45.00, '["Add-on: priority email"]'),
  ('ord_003', 'alice@acme.test',      '2026-04-15T14:20:00Z', 'pending',    89.00, '["Extra seat"]'),
  ('ord_004', 'bob@globex.test',      '2026-02-20T09:00:00Z', 'delivered', 1899.00,'["Enterprise renewal", "SSO add-on"]'),
  ('ord_005', 'bob@globex.test',      '2026-04-05T11:05:00Z', 'shipped',   299.00, '["Advanced reporting module"]'),
  ('ord_006', 'carla@initech.test',   '2026-01-16T16:30:00Z', 'delivered', 129.00, '["Pro seat annual renewal"]'),
  ('ord_007', 'carla@initech.test',   '2026-04-12T13:44:00Z', 'cancelled',  25.00, '["SMS notifications add-on"]'),
  ('ord_008', 'dan@umbrella.test',    '2026-03-22T07:19:00Z', 'delivered',   0.00, '["Free plan onboarding kit"]'),
  ('ord_009', 'erin@hooli.test',      '2026-03-30T12:00:00Z', 'delivered', 2499.00,'["Enterprise seats x 25"]'),
  ('ord_010', 'erin@hooli.test',      '2026-04-17T15:10:00Z', 'pending',   399.00, '["Dedicated CSM hour pack"]'),
  ('ord_011', 'felix@piedpiper.test', '2026-02-28T10:05:00Z', 'delivered', 129.00, '["Pro seat annual renewal"]'),
  ('ord_012', 'felix@piedpiper.test', '2026-04-08T09:22:00Z', 'refunded',   45.00, '["Priority email add-on"]'),
  ('ord_013', 'greta@tyrell.test',    '2026-03-15T17:50:00Z', 'delivered',   0.00, '["Free plan onboarding kit"]'),
  ('ord_014', 'hiro@wayne.test',      '2026-02-01T08:12:00Z', 'delivered', 129.00, '["Pro seat annual renewal"]'),
  ('ord_015', 'hiro@wayne.test',      '2026-03-28T14:44:00Z', 'shipped',    69.00, '["Custom domain add-on"]'),
  ('ord_016', 'hiro@wayne.test',      '2026-04-11T18:05:00Z', 'pending',   129.00, '["Pro seat manual top-up"]'),
  ('ord_017', 'bob@globex.test',      '2026-04-16T19:00:00Z', 'shipped',   249.00, '["Audit log extension"]'),
  ('ord_018', 'alice@acme.test',      '2026-01-02T10:00:00Z', 'delivered', 129.00, '["Pro seat annual renewal"]'),
  ('ord_019', 'erin@hooli.test',      '2026-04-18T10:00:00Z', 'shipped',   199.00, '["Advanced reporting module"]'),
  ('ord_020', 'carla@initech.test',   '2026-04-18T12:30:00Z', 'pending',    89.00, '["Extra seat"]');

-- Incidents --------------------------------------------------------------
-- NOTE: inc_c is resolved; the CheckActiveIncidentsTool must skip it.
INSERT INTO incidents (incident_id, title, status, started_at, product_area, affected_plans_json) VALUES
  ('inc_a', 'Elevated 5xx on API exports',      'investigating', '2026-04-19T08:12:00Z', 'api_exports',  '["pro","enterprise"]'),
  ('inc_b', 'Slow dashboard loads in EU region', 'monitoring',   '2026-04-19T06:30:00Z', 'dashboard',    '["free","pro","enterprise"]'),
  ('inc_c', 'Billing webhook delivery delays',  'resolved',      '2026-04-12T09:00:00Z', 'billing',      '["pro","enterprise"]');
