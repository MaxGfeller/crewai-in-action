"""HTTP client for the mocked account service."""

from __future__ import annotations

from functools import lru_cache

import httpx

from account_assistant.models import (
    AccountSummary,
    CalendarEventCreate,
    EmailDraftCreate,
    MeetingSlot,
    RenewalContext,
    TaskCreate,
)
from account_assistant.settings import account_service_url


class AccountService:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or account_service_url()).rstrip("/")

    def health(self) -> dict:
        resp = httpx.get(f"{self.base_url}/health", timeout=3.0)
        resp.raise_for_status()
        return resp.json()

    def list_accounts(self) -> list[AccountSummary]:
        resp = httpx.get(f"{self.base_url}/accounts", timeout=5.0)
        resp.raise_for_status()
        return [AccountSummary.model_validate(item) for item in resp.json()]

    def search_account(self, query: str) -> AccountSummary:
        resp = httpx.get(
            f"{self.base_url}/accounts/search",
            params={"q": query},
            timeout=5.0,
        )
        resp.raise_for_status()
        return AccountSummary.model_validate(resp.json())

    def renewal_context(self, account_id: str) -> RenewalContext:
        resp = httpx.get(
            f"{self.base_url}/accounts/{account_id}/renewal-context",
            timeout=8.0,
        )
        resp.raise_for_status()
        return RenewalContext.model_validate(resp.json())

    def calendar_slots(self, account_id: str, duration_minutes: int = 45) -> list[MeetingSlot]:
        resp = httpx.get(
            f"{self.base_url}/accounts/{account_id}/calendar-slots",
            params={"duration_minutes": duration_minutes},
            timeout=5.0,
        )
        resp.raise_for_status()
        return [MeetingSlot.model_validate(item) for item in resp.json()]

    def create_task(self, payload: TaskCreate) -> dict:
        resp = httpx.post(f"{self.base_url}/tasks", json=payload.model_dump(), timeout=5.0)
        resp.raise_for_status()
        return resp.json()

    def create_email_draft(self, payload: EmailDraftCreate) -> dict:
        resp = httpx.post(
            f"{self.base_url}/email-drafts",
            json=payload.model_dump(),
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json()

    def create_calendar_event(self, payload: CalendarEventCreate) -> dict:
        resp = httpx.post(
            f"{self.base_url}/calendar-events",
            json=payload.model_dump(),
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json()


@lru_cache(maxsize=1)
def get_account_service() -> AccountService:
    return AccountService()
