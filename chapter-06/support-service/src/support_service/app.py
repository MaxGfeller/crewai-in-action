"""FastAPI app exposing the Customer 360 + KB service.

Keep the route handlers thin - they delegate to :mod:`support_service.db`
and :mod:`support_service.kb`. The one non-trivial thing they do is honour
a ``simulate`` query param so Chapter 6.6 can exercise HTTP error paths
deterministically:

- ``?simulate=fail`` -> ``503 Service Unavailable``
- ``?simulate=slow`` -> sleeps ``SUPPORT_SERVICE_SLOW_SECONDS`` (default 5s)
  then responds normally

Readers should think of these as a built-in chaos switch, not part of
the production contract.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from support_service import db
from support_service.kb import INDEX as KB_INDEX
from support_service.models import (
    CustomerProfile,
    FeatureRequestIn,
    FeatureRequestOut,
    IncidentMatch,
    KbArticle,
    PlanTier,
    RecentOrder,
)


app = FastAPI(
    title="support-service",
    version="0.1.0",
    description=(
        "Customer 360 + KB service for the Chapter 6 Gmail support Flow. "
        "All endpoints accept ?simulate=fail|slow for deterministic chaos."
    ),
)


# ---------------------------------------------------------------------------
# Chaos helper - called at the top of every route that wants it.
# ---------------------------------------------------------------------------


def _apply_simulate(simulate: Optional[str]) -> None:
    if simulate is None:
        return
    if simulate == "fail":
        raise HTTPException(
            status_code=503,
            detail="simulated service failure (simulate=fail)",
        )
    if simulate == "slow":
        seconds = float(os.getenv("SUPPORT_SERVICE_SLOW_SECONDS", "5"))
        time.sleep(seconds)
        return
    raise HTTPException(
        status_code=400,
        detail=f"unknown simulate value: {simulate!r}; use 'fail' or 'slow'",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/customers/{email}", response_model=CustomerProfile)
def read_customer(
    email: str,
    simulate: Optional[str] = Query(default=None),
) -> CustomerProfile:
    _apply_simulate(simulate)
    profile = db.get_customer(email.strip().lower())
    if profile is None:
        raise HTTPException(status_code=404, detail=f"customer not found: {email}")
    return profile


@app.get("/customers/{email}/orders", response_model=list[RecentOrder])
def read_orders(
    email: str,
    limit: int = Query(default=5, ge=1, le=20),
    simulate: Optional[str] = Query(default=None),
) -> list[RecentOrder]:
    _apply_simulate(simulate)
    return db.get_recent_orders(email.strip().lower(), limit=limit)


@app.get("/incidents", response_model=list[IncidentMatch])
def read_incidents(
    plan_tier: Optional[PlanTier] = Query(default=None),
    product_area: Optional[str] = Query(default=None),
    simulate: Optional[str] = Query(default=None),
) -> list[IncidentMatch]:
    _apply_simulate(simulate)
    return db.active_incidents_for(plan_tier=plan_tier, product_area=product_area)


@app.get("/kb/search", response_model=list[KbArticle])
def search_kb(
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=3, ge=1, le=10),
    simulate: Optional[str] = Query(default=None),
) -> list[KbArticle]:
    _apply_simulate(simulate)
    return KB_INDEX.search(query, top_k=top_k)


@app.post("/feature-requests", response_model=FeatureRequestOut, status_code=201)
def log_feature_request(
    body: FeatureRequestIn,
    simulate: Optional[str] = Query(default=None),
) -> FeatureRequestOut:
    _apply_simulate(simulate)
    db.insert_feature_request(body)
    return FeatureRequestOut(**body.model_dump())


# FastAPI's default 404 JSON shape is {"detail": "Not Found"} - we keep it.
# Intentionally no CORS middleware; the Flow runs locally and is not a browser.
__all__ = ["app"]
