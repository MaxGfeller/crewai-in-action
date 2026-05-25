"""Tools that delegate specialist work from the main conversation agent."""

from __future__ import annotations

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from account_assistant.crews import RenewalRiskCrew
from account_assistant.events import record_event
from account_assistant.models import ContractRiskReview
from account_assistant.services import get_account_service


class AnalyzeRenewalRiskArgs(BaseModel):
    account_id: str = Field(description="The account id, for example acct_acme.")


class AnalyzeRenewalRiskTool(BaseTool):
    name: str = "analyze_renewal_risk"
    description: str = (
        "Delegate renewal risk analysis to a specialist crew. Use after loading "
        "account context when the user asks about renewal risk or preparation."
    )
    args_schema: type[BaseModel] = AnalyzeRenewalRiskArgs

    def _run(self, account_id: str) -> str:  # type: ignore[override]
        record_event("tool_start", self.name, {"account_id": account_id})
        context = get_account_service().renewal_context(account_id)

        result = RenewalRiskCrew().crew().kickoff(
            inputs={
                "account_json": context.account.model_dump_json(),
                "contract_json": context.contract.model_dump_json(),
                "usage_json": context.usage.model_dump_json(),
                "tickets_json": json.dumps([t.model_dump() for t in context.tickets]),
                "invoices_json": json.dumps([i.model_dump() for i in context.invoices]),
            }
        )
        if not isinstance(result.pydantic, ContractRiskReview):
            raise RuntimeError("Renewal risk specialist did not return ContractRiskReview")
        review = result.pydantic

        record_event(
            "ui_surface",
            "renewal_risk_card",
            {
                "type": "renewal_risk_card",
                "title": f"Renewal risk: {review.risk_level}",
                "payload": review.model_dump(),
            },
        )
        record_event(
            "tool_end",
            self.name,
            {"ok": True, "risk_level": review.risk_level, "risk_count": len(review.risks)},
        )
        return review.model_dump_json()
