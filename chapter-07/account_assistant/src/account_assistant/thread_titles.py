"""Conversation title helpers owned by the Flow control plane."""

from __future__ import annotations

import re

from account_assistant.state import ChatMessage


GENERIC_TITLES = {
    "",
    "New conversation",
    "Hello",
    "Hi",
    "Hey",
    "Hello! Who are you",
    "What can you do",
}


def should_refresh_title(title: str) -> bool:
    return title.strip() in GENERIC_TITLES


def derive_session_title(messages: list[ChatMessage]) -> str:
    """Derive a short stable title from user messages without another LLM call."""

    user_messages = [message.content for message in messages if message.role == "user"]
    if not user_messages:
        return "New conversation"

    source = next(
        (message for message in user_messages if not _is_greeting_or_meta(message)),
        user_messages[0],
    )
    title = _clean(source)
    return _truncate_words(title, max_chars=46) or "New conversation"


def _is_greeting_or_meta(text: str) -> bool:
    normalized = _clean(text).lower()
    if len(normalized.split()) > 7:
        return False
    return normalized.startswith(("hello", "hi", "hey")) or "what can you do" in normalized


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(please\s+|can you\s+|could you\s+)", "", text, flags=re.I)
    text = text.strip(" .?!")
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _truncate_words(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    words: list[str] = []
    for word in text.split():
        candidate = " ".join([*words, word])
        if len(candidate) > max_chars:
            break
        words.append(word)
    return " ".join(words).rstrip(",:;-") or text[:max_chars].rstrip()
