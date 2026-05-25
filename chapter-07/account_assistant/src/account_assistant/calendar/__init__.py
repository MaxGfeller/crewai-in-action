"""Calendar provider selection."""

from __future__ import annotations

import os

from account_assistant.calendar.base import CalendarProvider
from account_assistant.calendar.fake import FakeCalendarProvider
from account_assistant.calendar.google import GoogleCalendarProvider


def get_calendar_provider() -> CalendarProvider:
    if os.getenv("CALENDAR_PROVIDER", "fake").strip().lower() == "google":
        return GoogleCalendarProvider()
    return FakeCalendarProvider()


__all__ = ["CalendarProvider", "get_calendar_provider"]
