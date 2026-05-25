"""Fake calendar provider backed by the account service."""

from __future__ import annotations

from account_assistant.models import CalendarEventCreate, MeetingSlot
from account_assistant.services import get_account_service


class FakeCalendarProvider:
    def find_slots(self, account_id: str, duration_minutes: int = 45) -> list[MeetingSlot]:
        return get_account_service().calendar_slots(
            account_id=account_id,
            duration_minutes=duration_minutes,
        )

    def create_event(self, payload: CalendarEventCreate) -> dict:
        return get_account_service().create_calendar_event(payload)
