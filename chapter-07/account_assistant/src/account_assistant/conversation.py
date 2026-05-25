"""Application-facing conversation service shared by CLI and AG-UI server."""

from __future__ import annotations

import io
import json
import sqlite3
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel

from account_assistant.flow import AccountAssistantFlow
from account_assistant.models import CalendarEventCreate, EmailDraftCreate, TaskCreate
from account_assistant.persistence import default_persistence, resolve_persist_db_path
from account_assistant.services import get_account_service
from account_assistant.settings import require_openai_api_key, show_flow_logs
from account_assistant.state import AccountAssistantState, PendingAction, now_iso
from account_assistant.thread_titles import derive_session_title, should_refresh_title


class ThreadSummary(BaseModel):
    thread_id: str
    title: str
    created_at: str
    updated_at: str
    active_account_id: Optional[str] = None
    message_count: int = 0
    last_message_preview: str = ""


class ThreadDetail(BaseModel):
    summary: ThreadSummary
    snapshot: dict[str, Any]
    messages: list[dict[str, Any]]


class TurnResult(BaseModel):
    thread_id: str
    reply: str
    state: AccountAssistantState

    def state_snapshot(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "session_title": self.state.session_title,
            "created_at": self.state.created_at,
            "updated_at": self.state.updated_at,
            "active_account_id": self.state.active_account_id,
            "memory": self.state.memory.model_dump(),
            "messages": [m.model_dump() for m in self.state.messages[-8:]],
            "ui_surfaces": [s.model_dump() for s in self.state.ui_surfaces],
            "pending_actions": [a.model_dump() for a in self.state.pending_actions],
            "tool_traces": [t.model_dump() for t in self.state.tool_traces],
            "compacted_this_turn": self.state.compacted_this_turn,
            "estimated_prompt_tokens": self.state.estimated_prompt_tokens,
        }


class ConversationService:
    def create_thread(self) -> ThreadSummary:
        thread_id = f"thread_{uuid4().hex[:8]}"
        created_at = now_iso()
        return ThreadSummary(
            thread_id=thread_id,
            title="New conversation",
            created_at=created_at,
            updated_at=created_at,
        )

    def list_threads(self, limit: int = 50) -> list[ThreadSummary]:
        db_path = resolve_persist_db_path()
        if not db_path.exists():
            return []

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT flow_uuid, timestamp, state_json
                FROM flow_states
                WHERE id IN (
                    SELECT MAX(id)
                    FROM flow_states
                    GROUP BY flow_uuid
                )
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        threads: list[ThreadSummary] = []
        for thread_id, timestamp, state_json in rows:
            state_dict = json.loads(state_json)
            if not isinstance(state_dict, dict):
                continue
            state = _state_from_dict(state_dict, fallback_timestamp=timestamp)
            threads.append(_thread_summary(thread_id, state, fallback_updated_at=timestamp))
        return threads

    def get_thread(self, thread_id: str) -> ThreadDetail | None:
        state_dict = default_persistence().load_state(thread_id)
        if state_dict is None:
            return None
        state = _state_from_dict(state_dict)
        result = TurnResult(thread_id=thread_id, reply=state.assistant_reply, state=state)
        return ThreadDetail(
            summary=_thread_summary(thread_id, state),
            snapshot=result.state_snapshot(),
            messages=[
                {
                    "id": f"{thread_id}_{index}",
                    "role": message.role,
                    "content": message.content,
                }
                for index, message in enumerate(state.messages)
            ],
        )

    def run_turn(
        self,
        message: str,
        thread_id: Optional[str] = None,
        active_account_id: Optional[str] = None,
    ) -> TurnResult:
        require_openai_api_key()
        resolved_thread_id = thread_id or f"thread_{uuid4().hex[:8]}"
        flow = AccountAssistantFlow()
        inputs = {
            "id": resolved_thread_id,
            "thread_id": resolved_thread_id,
            "current_message": message,
        }
        if active_account_id is not None:
            inputs["active_account_id"] = active_account_id
        if show_flow_logs():
            flow.kickoff(inputs=inputs)
        else:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                flow.kickoff(inputs=inputs)
        state_dump = (
            flow.state.model_dump()
            if hasattr(flow.state, "model_dump")
            else dict(flow.state)
        )
        state = AccountAssistantState.model_validate(state_dump)
        return TurnResult(
            thread_id=resolved_thread_id,
            reply=state.assistant_reply,
            state=state,
        )

    def approve_action(self, action: PendingAction) -> dict:
        service = get_account_service()
        if action.type == "create_task":
            return service.create_task(TaskCreate.model_validate(action.payload))
        if action.type == "create_email_draft":
            return service.create_email_draft(EmailDraftCreate.model_validate(action.payload))
        if action.type == "create_calendar_event":
            return service.create_calendar_event(CalendarEventCreate.model_validate(action.payload))
        raise ValueError(f"unsupported action type: {action.type}")


def get_conversation_service() -> ConversationService:
    return ConversationService()


def _state_from_dict(
    state_dict: dict[str, Any],
    fallback_timestamp: str | None = None,
) -> AccountAssistantState:
    state_dict = dict(state_dict)
    messages = state_dict.get("messages") if isinstance(state_dict.get("messages"), list) else []
    first_message_at = _message_at(messages, 0)
    last_message_at = _message_at(messages, -1)
    state_dict.setdefault("created_at", first_message_at or fallback_timestamp or now_iso())
    state_dict.setdefault("updated_at", last_message_at or fallback_timestamp or state_dict["created_at"])
    state = AccountAssistantState.model_validate(state_dict)
    if should_refresh_title(state.session_title):
        state.session_title = derive_session_title(state.messages)
    return state


def _message_at(messages: list[Any], index: int) -> str | None:
    if not messages:
        return None
    try:
        message = messages[index]
    except IndexError:
        return None
    if isinstance(message, dict) and isinstance(message.get("at"), str):
        return message["at"]
    return None


def _thread_summary(
    thread_id: str,
    state: AccountAssistantState,
    fallback_updated_at: str | None = None,
) -> ThreadSummary:
    last_message = state.messages[-1].content if state.messages else ""
    return ThreadSummary(
        thread_id=thread_id,
        title=state.session_title or "New conversation",
        created_at=state.created_at,
        updated_at=state.updated_at or fallback_updated_at or state.created_at,
        active_account_id=state.active_account_id,
        message_count=len(state.messages),
        last_message_preview=last_message[:140],
    )
