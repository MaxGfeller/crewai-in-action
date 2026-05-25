"""Account context tools for the main conversation agent."""

from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from account_assistant.events import record_event
from account_assistant.services import get_account_service


class LoadAccountContextArgs(BaseModel):
    account: str = Field(
        description="Account id such as acct_acme, or a company name such as Acme."
    )


class LoadAccountContextTool(BaseTool):
    name: str = "load_account_context"
    description: str = (
        "Load account, contacts, contract, usage, support tickets, and invoices. "
        "Use this before answering account-specific questions."
    )
    args_schema: type[BaseModel] = LoadAccountContextArgs

    def _run(self, account: str) -> str:  # type: ignore[override]
        record_event("tool_start", self.name, {"account": account})
        service = get_account_service()
        account_id = account.strip()
        if not account_id.startswith("acct_"):
            account_id = service.search_account(account_id).account_id
        context = service.renewal_context(account_id)
        record_event(
            "ui_surface",
            "account_health_card",
            {
                "type": "account_health_card",
                "title": f"{context.account.name} renewal brief",
                "payload": context.model_dump(),
            },
        )
        record_event(
            "tool_end",
            self.name,
            {
                "ok": True,
                "account_id": context.account.account_id,
                "account_name": context.account.name,
            },
        )
        return context.model_dump_json()
