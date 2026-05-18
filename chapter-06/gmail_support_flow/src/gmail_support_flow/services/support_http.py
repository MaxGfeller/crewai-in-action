"""httpx-backed client for the support-service HTTP API.

The service runs on ``SUPPORT_SERVICE_URL`` (default
``http://127.0.0.1:8077``). Failures surface as
``httpx.HTTPStatusError`` / ``httpx.RequestError`` - specialist
handlers catch them and route through :func:`route_specialist_outcome`
in :mod:`gmail_support_flow.flow`.

HTTP-level retry on transient errors is deliberately NOT built in. The
chapter teaches recovery at the Flow level (retry-via-router, then
``@persist`` for kill-and-resume); sneaking retries into the transport
would hide that material.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from gmail_support_flow.services.base import SupportService
from gmail_support_flow.state import (
    CustomerProfile,
    IncidentMatch,
    PlanTier,
    RecentOrder,
)


DEFAULT_TIMEOUT_SECONDS = 10.0


def _base_url() -> str:
    return os.getenv("SUPPORT_SERVICE_URL", "http://127.0.0.1:8077").rstrip("/")


def _params(simulate: Optional[str], **extra: Any) -> dict[str, Any]:
    params = {k: v for k, v in extra.items() if v is not None}
    if simulate is not None:
        params["simulate"] = simulate
    return params


class SupportHttpClient(SupportService):
    """Thin synchronous httpx client. One instance per call site is fine.

    We deliberately do NOT pool a single ``httpx.Client`` across Flow
    runs - the verbosity of opening a connection per tool invocation is
    negligible for the chapter's scale, and it keeps Flow methods
    unambiguously sync.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = (base_url or _base_url()).rstrip("/")
        self._timeout = timeout_seconds

    # ---- helpers --------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any]) -> httpx.Response:
        resp = httpx.get(
            f"{self._base_url}{path}",
            params=params,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp

    def _post(self, path: str, json: dict[str, Any], params: dict[str, Any]) -> httpx.Response:
        resp = httpx.post(
            f"{self._base_url}{path}",
            json=json,
            params=params,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp

    # ---- SupportService surface ----------------------------------------

    def get_customer(
        self, email: str, *, simulate: Optional[str] = None
    ) -> Optional[CustomerProfile]:
        params = _params(simulate)
        try:
            resp = self._get(f"/customers/{email}", params)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        return CustomerProfile.model_validate(resp.json())

    def get_recent_orders(
        self, email: str, *, limit: int = 5, simulate: Optional[str] = None
    ) -> list[RecentOrder]:
        params = _params(simulate, limit=limit)
        resp = self._get(f"/customers/{email}/orders", params)
        return [RecentOrder.model_validate(r) for r in resp.json()]

    def active_incidents(
        self,
        *,
        plan_tier: Optional[PlanTier] = None,
        product_area: Optional[str] = None,
        simulate: Optional[str] = None,
    ) -> list[IncidentMatch]:
        params = _params(simulate, plan_tier=plan_tier, product_area=product_area)
        resp = self._get("/incidents", params)
        return [IncidentMatch.model_validate(r) for r in resp.json()]

    def search_kb(
        self,
        query: str,
        *,
        top_k: int = 3,
        simulate: Optional[str] = None,
    ) -> list[dict]:
        params = _params(simulate, query=query, top_k=top_k)
        resp = self._get("/kb/search", params)
        return list(resp.json())

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
        self._post(
            "/feature-requests",
            json={
                "request_id": request_id,
                "customer_email": customer_email,
                "summary": summary,
                "theme": theme,
                "logged_at": logged_at,
            },
            params=_params(simulate),
        )
