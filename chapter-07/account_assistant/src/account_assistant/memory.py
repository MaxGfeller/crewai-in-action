"""Prompt assembly and conversation compaction."""

from __future__ import annotations

import json

from crewai import Agent

from account_assistant.settings import recent_message_turns
from account_assistant.state import (
    AccountAssistantState,
    ChatMessage,
    ConversationMemory,
)

MAIN_AGENT_SYSTEM_PROMPT = """You are a customer account assistant embedded in a CRM.

You receive a compact long-term memory plus recent messages. Use tools whenever
you need account data, renewal risk analysis, meeting slots, or staged actions.

Rules:
- Be concise and specific.
- Never claim you created a task, draft, or calendar event unless the action was approved.
- If a side effect is useful, stage it with a tool and ask for approval.
- Mention which account you are using when there could be ambiguity.
"""


def estimate_tokens(text: str) -> int:
    # This is deliberately simple for the chapter. Production systems should use
    # the target model tokenizer.
    return max(1, len(text) // 4)


def recent_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    keep = max(1, recent_message_turns()) * 2
    return messages[-keep:]


def build_messages_for_turn(state: AccountAssistantState) -> list[dict[str, str]]:
    packed = [
        {"role": "system", "content": MAIN_AGENT_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": "Long-term conversation memory:\n"
            + state.memory.model_dump_json(),
        },
    ]
    if state.active_account_id:
        packed.append(
            {
                "role": "system",
                "content": f"Current selected account id: {state.active_account_id}",
            }
        )
    for message in recent_messages(state.messages):
        packed.append({"role": message.role, "content": message.content})
    return packed


def prompt_size_for_state(state: AccountAssistantState) -> int:
    return estimate_tokens(json.dumps(build_messages_for_turn(state)))


def compact_memory(
    memory: ConversationMemory,
    old_messages: list[ChatMessage],
) -> ConversationMemory:
    if not old_messages:
        return memory

    summarizer = Agent(
        role="Conversation memory curator",
        goal="Maintain compact memory for a turn-based account assistant",
        backstory=(
            "You preserve durable facts, decisions, preferences, open questions, "
            "pending actions, and important tool results while dropping small talk."
        ),
        llm="gpt-5.4",
        respect_context_window=True,
    )
    result = summarizer.kickoff(
        [
            {
                "role": "system",
                "content": (
                    "Update the memory object. Keep summary under 250 words. "
                    "Return valid JSON matching the ConversationMemory fields."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "existing_memory": memory.model_dump(),
                        "messages_to_compact": [m.model_dump() for m in old_messages],
                    }
                ),
            },
        ]
    )
    try:
        return ConversationMemory.model_validate_json(result.raw)
    except Exception:
        return memory
