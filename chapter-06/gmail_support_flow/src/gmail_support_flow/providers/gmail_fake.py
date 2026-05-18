"""Local Gmail stand-in.

Reads unread threads from ``data/fixtures/inbox_tickets.json``; writes
created drafts to ``artifacts/runs/<run_id>/draft_<thread_id>.md``; tracks
labels in-memory so readers can follow a full Flow without touching OAuth.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _artifacts_root() -> Path:
    root = _project_root() / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


class GmailFake:
    """In-memory inbox backed by the fixture JSON."""

    def __init__(self, fixture_path: Optional[Path] = None) -> None:
        self._fixture_path = fixture_path or (
            _project_root() / "data" / "fixtures" / "inbox_tickets.json"
        )
        self._threads: dict[str, dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _load(self) -> None:
        with self._fixture_path.open() as fh:
            threads = json.load(fh)
        for t in threads:
            self._threads[t["thread_id"]] = {
                **t,
                "labels": list(t.get("labels", [])),
                "read": False,
                "draft": None,
            }

    # ------------------------------------------------------------------
    # GmailProvider surface
    # ------------------------------------------------------------------
    def list_threads(
        self, label: str, max_results: int = 20, unread_only: bool = False
    ) -> list[dict]:
        hits: list[dict] = []
        for t in self._threads.values():
            if unread_only and t.get("read"):
                continue
            if label and label not in t["labels"]:
                continue
            hits.append(self._to_payload(t))
            if len(hits) >= max_results:
                break
        return hits

    def list_unread(self, label: str, max_results: int = 20) -> list[dict]:
        return self.list_threads(label=label, max_results=max_results, unread_only=True)

    def thread_by_id(self, thread_id: str) -> Optional[dict]:
        t = self._threads.get(thread_id)
        return self._to_payload(t) if t else None

    def create_draft(
        self,
        thread_id: str,
        body_markdown: str,
        subject_prefix: str = "Re: ",
    ) -> str:
        thread = self._threads.get(thread_id)
        if thread is None:
            raise KeyError(f"thread not found: {thread_id}")

        run_id = os.getenv("GMAIL_FAKE_RUN_ID") or uuid4().hex
        draft_dir = _artifacts_root() / "runs" / run_id
        draft_dir.mkdir(parents=True, exist_ok=True)
        draft_path = draft_dir / f"draft_{thread_id}.md"

        subject = f"{subject_prefix}{thread['subject']}"
        draft_path.write_text(
            f"# Draft reply to thread {thread_id}\n"
            f"**Subject:** {subject}\n"
            f"**To:** {thread['from_email']}\n\n"
            f"{body_markdown}\n"
        )

        draft_id = f"draft_{thread_id}_{uuid4().hex[:6]}"
        thread["draft"] = {"id": draft_id, "path": str(draft_path), "subject": subject}
        return draft_id

    def apply_labels(self, thread_id: str, labels: list[str]) -> None:
        thread = self._threads.get(thread_id)
        if thread is None:
            raise KeyError(f"thread not found: {thread_id}")
        for label in labels:
            if label not in thread["labels"]:
                thread["labels"].append(label)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _to_payload(self, t: dict[str, Any]) -> dict[str, Any]:
        return {
            "thread_id": t["thread_id"],
            "from_email": t["from_email"],
            "from_name": t.get("from_name"),
            "subject": t["subject"],
            "body": t["body"],
            "received_at": t["received_at"],
            "labels": list(t["labels"]),
        }

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
