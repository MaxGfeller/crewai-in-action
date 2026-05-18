"""Structural protocols for the external integrations.

The Flow only depends on these Protocols. Swapping fake for real is a matter
of flipping ``PROVIDERS_MODE``; no call-site changes.
"""

from __future__ import annotations

from typing import Protocol


class GmailProvider(Protocol):
    """Minimal Gmail API surface the Flow needs. Never sends email."""

    def list_unread(self, label: str, max_results: int = 20) -> list[dict]:
        ...

    def create_draft(
        self,
        thread_id: str,
        body_markdown: str,
        subject_prefix: str = "Re: ",
    ) -> str:
        ...

    def apply_labels(self, thread_id: str, labels: list[str]) -> None:
        ...

    def thread_by_id(self, thread_id: str) -> dict | None:
        """Convenience lookup used by ``run-one --thread-id``."""


class SlackProvider(Protocol):
    def post_message(
        self, channel: str, title: str, body_markdown: str, severity: str = "medium"
    ) -> str:
        ...
