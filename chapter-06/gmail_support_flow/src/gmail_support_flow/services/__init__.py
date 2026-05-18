"""Client for the external Customer 360 + KB service.

The Flow talks to ``../support-service`` over HTTP; this package wraps
the httpx calls behind a small Protocol so tests can stub it.
"""

from __future__ import annotations

from gmail_support_flow.services.base import SupportService
from gmail_support_flow.services.support_http import SupportHttpClient


def get_support_service() -> SupportService:
    """Return a client for the support service.

    Instantiated per call so tools and flow methods stay stateless.
    If the chapter ever needs an in-process fake (for tests), this is
    the single dispatch point to branch on.
    """
    return SupportHttpClient()


__all__ = ["SupportService", "SupportHttpClient", "get_support_service"]
