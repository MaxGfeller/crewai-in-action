"""Scheduling tools for the main conversation agent."""

from __future__ import annotations

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from account_assistant.calendar import get_calendar_provider
from account_assistant.events import record_event


class ProposeMeetingSlotsArgs(BaseModel):
    account_id: str = Field(description="The account id, for example acct_acme.")
    duration_minutes: int = Field(default=45, ge=15, le=120)


class ProposeMeetingSlotsTool(BaseTool):
    name: str = "propose_meeting_slots"
    description: str = (
        "Find candidate meeting slots. This only proposes slots; it does not create "
        "a calendar event without user approval."
    )
    args_schema: type[BaseModel] = ProposeMeetingSlotsArgs

    def _run(self, account_id: str, duration_minutes: int = 45) -> str:  # type: ignore[override]
        record_event(
            "tool_start",
            self.name,
            {"account_id": account_id, "duration_minutes": duration_minutes},
        )
        slots = get_calendar_provider().find_slots(account_id, duration_minutes)
        payload = {
            "account_id": account_id,
            "duration_minutes": duration_minutes,
            "slots": [slot.model_dump() for slot in slots],
        }
        record_event(
            "ui_surface",
            "meeting_slots_card",
            {
                "type": "meeting_slots_card",
                "title": "Candidate meeting slots",
                "payload": payload,
            },
        )
        if slots:
            record_event(
                "pending_action",
                "create_calendar_event",
                {
                    "type": "create_calendar_event",
                    "title": "Create renewal review meeting",
                    "payload": {
                        "account_id": account_id,
                        "slot_id": slots[0].slot_id,
                        "title": "Renewal review",
                        "attendees": [],
                        "starts_at": slots[0].starts_at,
                        "ends_at": slots[0].ends_at,
                    },
                },
            )
        record_event("tool_end", self.name, {"ok": True, "slots": len(slots)})
        return json.dumps(payload)
