"""Tools that stage side effects for explicit frontend approval."""

from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from account_assistant.events import record_event


class StageFollowupTaskArgs(BaseModel):
    account_id: str
    task_title: str = Field(description="Short title for the task to stage.")
    details: str
    due_date: str | None = Field(default=None, description="YYYY-MM-DD when known.")


class StageFollowupTaskTool(BaseTool):
    name: str = "stage_followup_task"
    description: str = (
        "Stage a follow-up task for user approval. This does not create the task yet."
    )
    args_schema: type[BaseModel] = StageFollowupTaskArgs

    def _run(
        self,
        account_id: str,
        task_title: str,
        details: str,
        due_date: str | None = None,
    ) -> str:  # type: ignore[override]
        record_event("tool_start", self.name, {"account_id": account_id, "task_title": task_title})
        payload = {
            "account_id": account_id,
            "title": task_title,
            "details": details,
            "due_date": due_date,
            "source": "account-assistant",
        }
        record_event("pending_action", self.name, {
            "type": "create_task",
            "title": task_title,
            "payload": payload,
        })
        record_event("tool_end", self.name, {"ok": True, "type": "create_task"})
        return "Task staged for user approval."


class DraftFollowupEmailArgs(BaseModel):
    account_id: str
    to: list[str]
    subject: str
    body_markdown: str


class DraftFollowupEmailTool(BaseTool):
    name: str = "draft_followup_email"
    description: str = (
        "Stage a follow-up email draft for user approval. This does not create the draft yet."
    )
    args_schema: type[BaseModel] = DraftFollowupEmailArgs

    def _run(
        self,
        account_id: str,
        to: list[str],
        subject: str,
        body_markdown: str,
    ) -> str:  # type: ignore[override]
        record_event("tool_start", self.name, {"account_id": account_id, "subject": subject})
        payload = {
            "account_id": account_id,
            "to": to,
            "subject": subject,
            "body_markdown": body_markdown,
        }
        record_event("pending_action", self.name, {
            "type": "create_email_draft",
            "title": subject,
            "payload": payload,
        })
        record_event("tool_end", self.name, {"ok": True, "type": "create_email_draft"})
        return "Email draft staged for user approval."
