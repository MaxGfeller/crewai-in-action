"""Optional Google Calendar provider.

The chapter defaults to a fixture-backed calendar provider. This provider shows
that the same seam can call a real calendar once the reader supplies OAuth
credentials. It deliberately creates events only from an already staged approval
action.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from account_assistant.models import CalendarEventCreate, MeetingSlot
from account_assistant.settings import project_root


SCOPES = [
    "https://www.googleapis.com/auth/calendar.freebusy",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleCalendarProvider:
    def __init__(self) -> None:
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    def _token_path(self) -> Path:
        raw = os.getenv("GOOGLE_CALENDAR_TOKEN_JSON", "artifacts/google_calendar_token.json")
        path = Path(raw)
        if not path.is_absolute():
            path = project_root() / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _credentials_path(self) -> Path:
        raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
        if not raw:
            raise RuntimeError("GOOGLE_CREDENTIALS_JSON is required for Google Calendar mode")
        return Path(raw).expanduser()

    def _service(self):
        token_path = self._token_path()
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._credentials_path()),
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json())
        return build("calendar", "v3", credentials=creds)

    def find_slots(self, account_id: str, duration_minutes: int = 45) -> list[MeetingSlot]:
        service = self._service()
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=10)).isoformat()
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": self.calendar_id}],
        }
        busy = (
            service.freebusy()
            .query(body=body)
            .execute()
            .get("calendars", {})
            .get(self.calendar_id, {})
            .get("busy", [])
        )

        slots: list[MeetingSlot] = []
        cursor = now + timedelta(days=1)
        while len(slots) < 3 and cursor < now + timedelta(days=10):
            if cursor.weekday() < 5 and 9 <= cursor.hour <= 15:
                start = cursor
                end = cursor + timedelta(minutes=duration_minutes)
                overlaps = any(
                    start.isoformat() < item["end"] and end.isoformat() > item["start"]
                    for item in busy
                )
                if not overlaps:
                    slots.append(
                        MeetingSlot(
                            slot_id=f"google_{account_id}_{len(slots) + 1}",
                            starts_at=start.isoformat(),
                            ends_at=end.isoformat(),
                            label=start.strftime("%a %b %d, %I:%M %p UTC"),
                        )
                    )
            cursor += timedelta(hours=1)
        return slots

    def create_event(self, payload: CalendarEventCreate) -> dict:
        if not payload.starts_at or not payload.ends_at:
            raise RuntimeError("Google Calendar approvals require starts_at and ends_at")
        event = {
            "summary": payload.title,
            "start": {"dateTime": payload.starts_at},
            "end": {"dateTime": payload.ends_at},
            "attendees": [{"email": email} for email in payload.attendees],
        }
        created = (
            self._service()
            .events()
            .insert(calendarId=self.calendar_id, body=event, sendUpdates="none")
            .execute()
        )
        return created
