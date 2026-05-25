"""Conversation Flow for the Chapter 7 account assistant.

This Flow is the control plane for each chat turn:

- append the new user message to durable state
- estimate prompt size and compact old history when needed
- call the main conversation agent with a message stack
- capture tool events emitted by custom tools
- persist the assistant response, rich surfaces, and pending actions

Specialist work is delegated from the main agent through tools. Some tools
call mocked systems directly; the risk tool wraps a specialist CrewAI crew.
"""

from __future__ import annotations

from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist

from account_assistant.events import RuntimeEvent, capture_events
from account_assistant.main_agent import build_main_agent
from account_assistant.memory import (
    build_messages_for_turn,
    compact_memory,
    prompt_size_for_state,
    recent_messages,
)
from account_assistant.persistence import default_persistence
from account_assistant.settings import max_prompt_tokens
from account_assistant.state import (
    AccountAssistantState,
    PendingAction,
    ToolTrace,
    UiSurface,
)
from account_assistant.thread_titles import derive_session_title, should_refresh_title


@persist(default_persistence())
class AccountAssistantFlow(Flow[AccountAssistantState]):
    """One persisted Flow instance represents one conversation thread."""

    @start()
    def intake(self) -> None:
        self.state.assistant_reply = ""
        self.state.ui_surfaces = []
        self.state.pending_actions = []
        self.state.tool_traces = []
        self.state.last_error = None
        self.state.compacted_this_turn = False

        if not self.state.thread_id:
            self.state.thread_id = self.state.id
        if not self.state.current_message.strip():
            raise RuntimeError("current_message is required")
        self.state.append_user(self.state.current_message.strip())

    @listen(intake)
    def compact_if_needed(self) -> None:
        self.state.estimated_prompt_tokens = prompt_size_for_state(self.state)
        if self.state.estimated_prompt_tokens <= max_prompt_tokens():
            return

        keep = recent_messages(self.state.messages)
        old_count = max(0, len(self.state.messages) - len(keep))
        if old_count == 0:
            return

        old_messages = self.state.messages[:old_count]
        self.state.memory = compact_memory(self.state.memory, old_messages)
        self.state.messages = keep
        self.state.compacted_this_turn = True
        self.state.estimated_prompt_tokens = prompt_size_for_state(self.state)

    @listen(compact_if_needed)
    def run_conversation_agent(self) -> None:
        with capture_events() as events:
            result = build_main_agent().kickoff(build_messages_for_turn(self.state))

        self._apply_runtime_events(events)
        self.state.assistant_reply = result.raw
        self.state.append_assistant(self.state.assistant_reply)

    @listen(run_conversation_agent)
    def update_session_metadata(self) -> None:
        if should_refresh_title(self.state.session_title):
            self.state.session_title = derive_session_title(self.state.messages)

    @listen(update_session_metadata)
    def finalize(self) -> dict:
        return {
            "thread_id": self.state.thread_id,
            "session_title": self.state.session_title,
            "reply": self.state.assistant_reply,
            "ui_surfaces": [surface.model_dump() for surface in self.state.ui_surfaces],
            "pending_actions": [action.model_dump() for action in self.state.pending_actions],
            "compacted": self.state.compacted_this_turn,
        }

    def _apply_runtime_events(self, events: list[RuntimeEvent]) -> None:
        for event in events:
            if event.kind == "tool_end":
                self.state.tool_traces.append(
                    ToolTrace(
                        name=event.name,
                        ok=bool(event.payload.get("ok", True)),
                        args={k: v for k, v in event.payload.items() if k != "ok"},
                        result_preview=str(event.payload)[:240],
                    )
                )
            elif event.kind == "ui_surface":
                if event.payload.get("type") == "account_health_card":
                    account = event.payload.get("payload", {}).get("account", {})
                    account_id = account.get("account_id")
                    if isinstance(account_id, str) and account_id:
                        self.state.active_account_id = account_id
                self.state.ui_surfaces.append(
                    UiSurface(
                        type=str(event.payload.get("type", event.name)),
                        title=str(event.payload.get("title", event.name)),
                        payload=dict(event.payload.get("payload", {})),
                    )
                )
            elif event.kind == "pending_action":
                self.state.pending_actions.append(
                    PendingAction(
                        type=event.payload["type"],
                        title=event.payload["title"],
                        payload=dict(event.payload["payload"]),
                    )
                )
