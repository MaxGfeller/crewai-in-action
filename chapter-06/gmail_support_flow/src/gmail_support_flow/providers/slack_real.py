"""Real Slack provider (``slack_sdk.WebClient``)."""

from __future__ import annotations

import os
from typing import Any

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except Exception as exc:  # pragma: no cover - only raised in real mode
    WebClient = None  # type: ignore[assignment]
    _IMPORT_ERROR: Exception | None = exc
else:
    _IMPORT_ERROR = None


_SEVERITY_ICONS = {"low": ":information_source:", "medium": ":warning:", "high": ":rotating_light:"}


class SlackReal:
    def __init__(self) -> None:
        if _IMPORT_ERROR is not None:
            raise RuntimeError(
                "Real Slack provider requires slack_sdk. Install deps or "
                "set PROVIDERS_MODE=fake."
            ) from _IMPORT_ERROR
        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            raise RuntimeError(
                "SLACK_BOT_TOKEN not set. Set it in .env or switch "
                "PROVIDERS_MODE=fake."
            )
        self._client: Any = WebClient(token=token)

    def post_message(
        self, channel: str, title: str, body_markdown: str, severity: str = "medium"
    ) -> str:
        icon = _SEVERITY_ICONS.get(severity, ":warning:")
        text = f"{icon} *{title}*\n{body_markdown}"
        try:
            resp = self._client.chat_postMessage(channel=channel, text=text, mrkdwn=True)
        except SlackApiError as exc:  # pragma: no cover - network path
            raise RuntimeError(f"Slack post failed: {exc.response.get('error')}") from exc
        return str(resp["ts"])
