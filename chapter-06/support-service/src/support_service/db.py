"""Thin SQLite access layer for the support service.

Endpoints in :mod:`support_service.app` call these helpers; the HTTP
layer does no SQL of its own. Sync stdlib ``sqlite3`` is enough - the
Flow never fans out concurrent requests to this service.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from support_service.models import (
    CustomerProfile,
    FeatureRequestIn,
    IncidentMatch,
    PlanTier,
    RecentOrder,
)


def _package_root() -> Path:
    # src/support_service/db.py -> repo-local root of this service.
    return Path(__file__).resolve().parents[2]


def resolve_db_path() -> Path:
    raw = os.getenv("SUPPORT_DB_PATH", "support.sqlite")
    path = Path(raw)
    if not path.is_absolute():
        path = _package_root() / path
    return path


@contextmanager
def connect(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    db_path = db_path or resolve_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def get_customer(email: str) -> Optional[CustomerProfile]:
    with connect() as conn:
        row = conn.execute(
            "SELECT email, name, plan_tier, is_vip, signup_date, prior_ticket_count "
            "FROM customers WHERE email = ?",
            (email,),
        ).fetchone()
    if row is None:
        return None
    return CustomerProfile(
        email=row["email"],
        name=row["name"],
        plan_tier=row["plan_tier"],
        is_vip=bool(row["is_vip"]),
        signup_date=row["signup_date"],
        prior_ticket_count=int(row["prior_ticket_count"]),
    )


def get_recent_orders(email: str, limit: int = 5) -> list[RecentOrder]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT order_id, placed_at, status, total_usd, items_json "
            "FROM orders WHERE customer_email = ? "
            "ORDER BY placed_at DESC LIMIT ?",
            (email, limit),
        ).fetchall()
    return [
        RecentOrder(
            order_id=r["order_id"],
            placed_at=r["placed_at"],
            status=r["status"],
            total_usd=float(r["total_usd"]),
            items=json.loads(r["items_json"]),
        )
        for r in rows
    ]


def active_incidents_for(
    plan_tier: Optional[PlanTier] = None,
    product_area: Optional[str] = None,
) -> list[IncidentMatch]:
    """Return non-resolved incidents, optionally filtered by plan and area."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT incident_id, title, status, started_at, product_area, affected_plans_json "
            "FROM incidents WHERE status != 'resolved'"
        ).fetchall()

    results: list[IncidentMatch] = []
    for r in rows:
        affected = json.loads(r["affected_plans_json"])
        if plan_tier is not None and plan_tier not in affected:
            continue
        if product_area is not None and r["product_area"] != product_area:
            continue
        results.append(
            IncidentMatch(
                incident_id=r["incident_id"],
                title=r["title"],
                status=r["status"],
                started_at=r["started_at"],
                product_area=r["product_area"],
                affected_plans=affected,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def insert_feature_request(fr: FeatureRequestIn) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO feature_requests "
            "(request_id, customer_email, theme, summary, logged_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (fr.request_id, fr.customer_email, fr.theme, fr.summary, fr.logged_at),
        )
        conn.commit()
