"""In-process event capture for tools invoked by the conversation agent."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


EventKind = Literal["tool_start", "tool_end", "ui_surface", "pending_action"]


class RuntimeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:8]}")
    kind: EventKind
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)


_EVENTS: ContextVar[list[RuntimeEvent] | None] = ContextVar("account_tool_events", default=None)


def record_event(kind: EventKind, name: str, payload: dict[str, Any] | None = None) -> None:
    events = _EVENTS.get()
    if events is None:
        return
    events.append(RuntimeEvent(kind=kind, name=name, payload=payload or {}))


@contextmanager
def capture_events() -> Iterator[list[RuntimeEvent]]:
    events: list[RuntimeEvent] = []
    token = _EVENTS.set(events)
    try:
        yield events
    finally:
        _EVENTS.reset(token)
