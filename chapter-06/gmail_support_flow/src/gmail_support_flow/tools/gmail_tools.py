"""Gmail-facing tools. The Flow methods call these directly; we don't hand
them to agents by default because "send-like" actions should stay
deterministic (and, in this chapter, draft-only).
"""

from __future__ import annotations

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from gmail_support_flow.providers import get_gmail_provider


class _ReadArg(BaseModel):
    label: str = Field(
        default="book-support-demo",
        description="Gmail label to filter unread messages by.",
    )
    max_results: int = Field(default=20, ge=1, le=100)


class GmailReadUnreadTool(BaseTool):
    name: str = "gmail_read_unread"
    description: str = (
        "Return unread Gmail threads matching a label. JSON array of threads."
    )
    args_schema: type[BaseModel] = _ReadArg

    def _run(self, label: str = "book-support-demo", max_results: int = 20) -> str:  # type: ignore[override]
        provider = get_gmail_provider()
        return json.dumps(provider.list_unread(label=label, max_results=max_results))


class _DraftArg(BaseModel):
    thread_id: str = Field(description="Gmail thread id.")
    body_markdown: str = Field(description="Draft body in markdown.")
    subject_prefix: str = Field(default="Re: ")


class GmailCreateDraftTool(BaseTool):
    name: str = "gmail_create_draft"
    description: str = (
        "Create a Gmail draft on the given thread. Returns the draft id. "
        "NEVER sends the email - drafts are reviewed by a human (see chapter 9)."
    )
    args_schema: type[BaseModel] = _DraftArg

    def _run(  # type: ignore[override]
        self, thread_id: str, body_markdown: str, subject_prefix: str = "Re: "
    ) -> str:
        provider = get_gmail_provider()
        return provider.create_draft(thread_id, body_markdown, subject_prefix=subject_prefix)


class _LabelArg(BaseModel):
    thread_id: str = Field(description="Gmail thread id.")
    labels: list[str] = Field(description="Labels to apply.")


class GmailApplyLabelTool(BaseTool):
    name: str = "gmail_apply_label"
    description: str = "Apply labels to a Gmail thread. Returns 'ok'."
    args_schema: type[BaseModel] = _LabelArg

    def _run(self, thread_id: str, labels: list[str]) -> str:  # type: ignore[override]
        provider = get_gmail_provider()
        provider.apply_labels(thread_id, labels)
        return "ok"
