# support-service

The Customer 360 + Knowledge Base HTTP service the Gmail Support Flow
(`../gmail_support_flow`) consumes. It owns the SQLite database, the KB
corpus, and the BM25 index. Running this as a separate process is the
point: Chapter 6's Flow must treat customer data as a **remote
dependency**, not a file path it can peek at.

## Setup

```bash
cd chapter-06/support-service
cp .env.example .env
uv sync
uv run seed                         # applies data/schema.sql + data/seed.sql
```

Expected seed output:
`customers: 8  orders: 20  incidents: 3  kb: 10`.

## Run

```bash
uv run support-service              # starts FastAPI on 127.0.0.1:8077
```

In a second terminal, the Flow picks up `SUPPORT_SERVICE_URL` from its
own `.env` and calls this service.

## Endpoints

| Method & path                        | Purpose                          |
|---|---|
| `GET /health`                        | Liveness check                   |
| `GET /customers/{email}`             | Customer profile or `404`        |
| `GET /customers/{email}/orders`      | Recent orders (newest first)     |
| `GET /incidents`                     | Active incidents, filter by `plan_tier`, `product_area` |
| `GET /kb/search?query=...`           | BM25 over KB articles            |
| `POST /feature-requests`             | Append a logged feature request  |

Every endpoint accepts a `simulate` query param for Chapter 6.6:

- `?simulate=fail` → `503 Service Unavailable`
- `?simulate=slow` → sleeps for 5 seconds, then responds normally

This is how the retry + escalation scene in the book reproduces an HTTP
failure without requiring a flaky network.
