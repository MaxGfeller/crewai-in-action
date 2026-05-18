"""CLI entry points for the support service.

- ``uv run seed``              -> apply schema.sql + seed.sql
- ``uv run support-service``   -> uvicorn serving ``support_service.app:app``
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a declared dep
    pass


# ---------------------------------------------------------------------------
# seed
# ---------------------------------------------------------------------------


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _fixture_count(path: Path) -> int:
    with path.open() as fh:
        return len(json.load(fh))


def seed() -> None:
    parser = argparse.ArgumentParser(description="Seed the support-service SQLite database.")
    parser.add_argument("--reset", action="store_true", help="Delete the DB file before seeding.")
    args = parser.parse_args()

    root = _package_root()
    raw = os.getenv("SUPPORT_DB_PATH", "support.sqlite")
    db_path = Path(raw)
    if not db_path.is_absolute():
        db_path = root / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if args.reset and db_path.exists():
        db_path.unlink()

    schema_sql = (root / "data" / "schema.sql").read_text()
    seed_sql = (root / "data" / "seed.sql").read_text()

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.executescript(seed_sql)
        customers = _row_count(conn, "customers")
        orders = _row_count(conn, "orders")
        incidents = _row_count(conn, "incidents")

    kb_count = _fixture_count(root / "data" / "fixtures" / "kb_articles.json")

    print(f"customers: {customers}  orders: {orders}  incidents: {incidents}  kb: {kb_count}")
    print(f"db: {db_path}")


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


def serve() -> None:
    import uvicorn

    host = os.getenv("SUPPORT_SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("SUPPORT_SERVICE_PORT", "8077"))
    # Startup sanity: make sure the DB exists before accepting requests.
    raw = os.getenv("SUPPORT_DB_PATH", "support.sqlite")
    db_path = Path(raw)
    if not db_path.is_absolute():
        db_path = _package_root() / db_path
    if not db_path.exists():
        print(
            f"[support-service] database not found at {db_path}\n"
            f"                  run `uv run seed` first.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[support-service] starting on http://{host}:{port}  db={db_path}")
    uvicorn.run("support_service.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":  # pragma: no cover
    # Allow `python -m support_service.cli seed` as an alternative entry.
    action = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if action == "seed":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        seed()
    else:
        serve()
