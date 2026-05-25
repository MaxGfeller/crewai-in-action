"""JSON fixture and JSONL side-effect store for the mocked account service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from account_service.models import (
    AccountSummary,
    CalendarEventCreate,
    CalendarEventOut,
    EmailDraftCreate,
    EmailDraftOut,
    MeetingSlot,
    RenewalContext,
    TaskCreate,
    TaskOut,
)


def package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fixture_path(name: str) -> Path:
    return package_root() / "data" / "fixtures" / name


def artifacts_root() -> Path:
    root = package_root() / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _load_contexts() -> list[RenewalContext]:
    with fixture_path("renewal_contexts.json").open() as fh:
        return [RenewalContext.model_validate(item) for item in json.load(fh)]


def list_accounts() -> list[AccountSummary]:
    return [context.account for context in _load_contexts()]


def get_context(account_id: str) -> RenewalContext | None:
    normalised = account_id.strip().lower()
    for context in _load_contexts():
        if context.account.account_id.lower() == normalised:
            return context
    return None


def find_account(query: str) -> AccountSummary | None:
    normalised = query.strip().lower()
    for account in list_accounts():
        if account.account_id.lower() == normalised or normalised in account.name.lower():
            return account
    return None


def calendar_slots(account_id: str, duration_minutes: int = 45) -> list[MeetingSlot]:
    with fixture_path("calendar_slots.json").open() as fh:
        all_slots = json.load(fh)
    raw_slots = all_slots.get(account_id, [])
    return [MeetingSlot.model_validate(slot) for slot in raw_slots[:5]]


def _append_jsonl(name: str, payload: dict) -> None:
    path = artifacts_root() / name
    with path.open("a") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def create_task(payload: TaskCreate) -> TaskOut:
    task = TaskOut(
        **payload.model_dump(),
        task_id=f"task_{uuid4().hex[:8]}",
        created_at=_now_iso(),
    )
    _append_jsonl("tasks.jsonl", task.model_dump())
    return task


def create_email_draft(payload: EmailDraftCreate) -> EmailDraftOut:
    draft = EmailDraftOut(
        **payload.model_dump(),
        draft_id=f"draft_{uuid4().hex[:8]}",
        created_at=_now_iso(),
    )
    _append_jsonl("email_drafts.jsonl", draft.model_dump())
    return draft


def create_calendar_event(payload: CalendarEventCreate) -> CalendarEventOut:
    slot_by_id = {slot.slot_id: slot for slot in calendar_slots(payload.account_id)}
    slot = slot_by_id.get(payload.slot_id)
    if slot is None:
        raise KeyError(payload.slot_id)
    event = CalendarEventOut(
        **payload.model_dump(),
        event_id=f"cal_{uuid4().hex[:8]}",
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        created_at=_now_iso(),
    )
    _append_jsonl("calendar_events.jsonl", event.model_dump())
    return event
