"""Calendar provider protocol used by the scheduling tool."""

from __future__ import annotations

from typing import Protocol

from account_assistant.models import CalendarEventCreate, MeetingSlot


class CalendarProvider(Protocol):
    def find_slots(self, account_id: str, duration_minutes: int = 45) -> list[MeetingSlot]:
        """Return candidate slots for a meeting."""

    def create_event(self, payload: CalendarEventCreate) -> dict:
        """Create a calendar event after explicit user approval."""
