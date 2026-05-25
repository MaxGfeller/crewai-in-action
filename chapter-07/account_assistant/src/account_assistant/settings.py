"""Small environment-backed settings helpers."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def require_openai_api_key() -> None:
    if os.getenv("OPENAI_API_KEY"):
        return
    raise RuntimeError(
        "OPENAI_API_KEY is required. This example always uses the real "
        "CrewAI conversation agent; only the account/calendar systems are mocked."
    )


def max_prompt_tokens() -> int:
    return int(os.getenv("MAX_PROMPT_TOKENS", "3200"))


def recent_message_turns() -> int:
    return int(os.getenv("RECENT_MESSAGE_TURNS", "4"))


def show_flow_logs() -> bool:
    return os.getenv("SHOW_FLOW_LOGS", "").strip().lower() in {"1", "true", "yes", "on"}


def account_service_url() -> str:
    return os.getenv("ACCOUNT_SERVICE_URL", "http://127.0.0.1:8087").rstrip("/")
