"""Typed state for the Chapter 7 conversation Flow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from crewai.flow.flow import FlowState
from pydantic import BaseModel, Field


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    at: str = Field(default_factory=now_iso)


class ConversationMemory(BaseModel):
    summary: str = ""
    stable_facts: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    pending_actions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    important_tool_results: list[str] = Field(default_factory=list)


class UiSurface(BaseModel):
    surface_id: str = Field(default_factory=lambda: f"surface_{uuid4().hex[:8]}")
    type: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)


class PendingAction(BaseModel):
    action_id: str = Field(default_factory=lambda: f"action_{uuid4().hex[:8]}")
    type: Literal["create_task", "create_email_draft", "create_calendar_event"]
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: Literal["staged", "approved", "cancelled"] = "staged"


class ToolTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: f"tool_{uuid4().hex[:8]}")
    name: str
    ok: bool
    args: dict[str, Any] = Field(default_factory=dict)
    result_preview: str = ""


class AccountAssistantState(FlowState):
    # Inputs for the current turn. ``thread_id`` is also used as the Flow id.
    thread_id: str = ""
    current_message: str = ""
    active_account_id: Optional[str] = None
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    session_title: str = "New conversation"
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

    # Durable conversation memory.
    messages: list[ChatMessage] = Field(default_factory=list)
    memory: ConversationMemory = Field(default_factory=ConversationMemory)
    estimated_prompt_tokens: int = 0
    compacted_this_turn: bool = False

    # Runtime output for the most recent turn.
    assistant_reply: str = ""
    ui_surfaces: list[UiSurface] = Field(default_factory=list)
    pending_actions: list[PendingAction] = Field(default_factory=list)
    tool_traces: list[ToolTrace] = Field(default_factory=list)
    last_error: Optional[str] = None

    def append_user(self, content: str) -> None:
        self.messages.append(ChatMessage(role="user", content=content))
        self.updated_at = now_iso()

    def append_assistant(self, content: str) -> None:
        self.messages.append(ChatMessage(role="assistant", content=content))
        self.updated_at = now_iso()
