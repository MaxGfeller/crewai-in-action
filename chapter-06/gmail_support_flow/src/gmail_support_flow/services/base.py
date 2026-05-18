"""Structural protocol for the Customer 360 + KB service client.

The Flow depends only on this Protocol. The concrete implementation is
an httpx client in :mod:`support_http`; swapping in a test double only
requires matching this shape.

``simulate`` is an escape hatch the service exposes for Chapter 6.6
failure demos - the server honours ``fail`` (returns 503) and ``slow``
(sleeps, then responds).
"""

from __future__ import annotations

from typing import Optional, Protocol

from gmail_support_flow.state import (
    CustomerProfile,
    IncidentMatch,
    PlanTier,
    RecentOrder,
)


class KbArticle(Protocol):
    """Shape the support service returns for a KB article.

    A Protocol rather than a Pydantic class because the Flow only reads
    it - it never round-trips into persisted state.
    """

    id: str
    theme: str
    title: str
    body: str


class SupportService(Protocol):
    """Customer 360 + KB HTTP service surface the Flow consumes."""

    def get_customer(
        self, email: str, *, simulate: Optional[str] = None
    ) -> Optional[CustomerProfile]:
        ...

    def get_recent_orders(
        self, email: str, *, limit: int = 5, simulate: Optional[str] = None
    ) -> list[RecentOrder]:
        ...

    def active_incidents(
        self,
        *,
        plan_tier: Optional[PlanTier] = None,
        product_area: Optional[str] = None,
        simulate: Optional[str] = None,
    ) -> list[IncidentMatch]:
        ...

    def search_kb(
        self,
        query: str,
        *,
        top_k: int = 3,
        simulate: Optional[str] = None,
    ) -> list[dict]:
        """Return a list of article dicts - kept as ``dict`` so tool
        output is trivially JSON-serialisable back to the LLM."""
        ...

    def log_feature_request(
        self,
        *,
        request_id: str,
        customer_email: str,
        summary: str,
        theme: Optional[str],
        logged_at: str,
        simulate: Optional[str] = None,
    ) -> None:
        ...
