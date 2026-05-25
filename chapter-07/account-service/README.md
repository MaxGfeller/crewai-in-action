# account-service

Mock CRM, renewal, support, task, and calendar service for the Chapter 7
Customer Account Assistant. The CrewAI assistant consumes this over HTTP so the
chapter code looks like a product integration instead of local file access.

## Run

```bash
cd chapter-07/account-service
cp .env.example .env
uv sync
uv run account-service
```

The service listens on `http://127.0.0.1:8087` by default.

## Useful commands

```bash
uv run list-accounts
uv run reset-artifacts
```

Side-effect endpoints append JSONL files under `artifacts/`.
