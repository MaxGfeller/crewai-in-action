"""Fake Slack provider: append-only JSONL audit log."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


class SlackFake:
    def __init__(self, outbox_path: Path | None = None) -> None:
        self._outbox_path = outbox_path or (_project_root() / "artifacts" / "slack_outbox.jsonl")
        self._outbox_path.parent.mkdir(parents=True, exist_ok=True)

    def post_message(
        self, channel: str, title: str, body_markdown: str, severity: str = "medium"
    ) -> str:
        ts = f"fake_{uuid4().hex[:12]}"
        record = {
            "ts": ts,
            "channel": channel,
            "title": title,
            "severity": severity,
            "body_markdown": body_markdown,
            "posted_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
                "+00:00", "Z"
            ),
        }
        with self._outbox_path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
        return ts
