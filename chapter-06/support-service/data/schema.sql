-- Chapter 6 — Gmail Support Flow
-- Customer 360 / Support Context schema. Deterministic, local-only.
-- Run `uv run seed` to apply this DDL + data/seed.sql to artifacts/support.sqlite.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS feature_requests;
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    email               TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    plan_tier           TEXT NOT NULL CHECK (plan_tier IN ('free', 'pro', 'enterprise')),
    is_vip              INTEGER NOT NULL DEFAULT 0,
    signup_date         TEXT NOT NULL,               -- ISO date
    prior_ticket_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE orders (
    order_id        TEXT PRIMARY KEY,
    customer_email  TEXT NOT NULL REFERENCES customers(email),
    placed_at       TEXT NOT NULL,                   -- ISO datetime
    status          TEXT NOT NULL CHECK (status IN ('pending','shipped','delivered','refunded','cancelled')),
    total_usd       REAL NOT NULL,
    items_json      TEXT NOT NULL                    -- JSON array of strings
);

CREATE TABLE incidents (
    incident_id          TEXT PRIMARY KEY,
    title                TEXT NOT NULL,
    status               TEXT NOT NULL CHECK (status IN ('investigating','identified','monitoring','resolved')),
    started_at           TEXT NOT NULL,
    product_area         TEXT,
    affected_plans_json  TEXT NOT NULL               -- JSON array of plan_tier strings
);

-- Grows at runtime when the feature_request branch logs a request.
CREATE TABLE feature_requests (
    request_id      TEXT PRIMARY KEY,
    customer_email  TEXT NOT NULL,
    theme           TEXT,
    summary         TEXT NOT NULL,
    logged_at       TEXT NOT NULL
);
