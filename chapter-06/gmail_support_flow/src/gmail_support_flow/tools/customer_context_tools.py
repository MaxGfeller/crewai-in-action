"""Tools that expose the Customer 360 service to specialist agents.

The agents should reach for :class:`GetCustomerProfileTool` before drafting a
billing reply, and :class:`GetRecentOrdersTool` when a refund or renewal is
involved. Both are deterministic - they call the HTTP support service
rather than letting the LLM write SQL.
"""

from __future__ import annotations

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from gmail_support_flow.services import get_support_service


class _EmailArg(BaseModel):
    email: str = Field(description="The sender's email address, lower-case preferred.")


class GetCustomerProfileTool(BaseTool):
    name: str = "customer_profile"
    description: str = (
        "Return the customer's plan tier, VIP flag, signup date and prior-ticket count "
        "given their email address. Returns a JSON string, or '{}' if unknown."
    )
    args_schema: type[BaseModel] = _EmailArg

    def _run(self, email: str) -> str:  # type: ignore[override]
        profile = get_support_service().get_customer(email.strip().lower())
        if profile is None:
            return "{}"
        return profile.model_dump_json()


class _RecentOrdersArg(BaseModel):
    email: str = Field(description="The customer's email address.")
    limit: int = Field(default=5, ge=1, le=20, description="Max orders to return.")


class GetRecentOrdersTool(BaseTool):
    name: str = "recent_orders"
    description: str = (
        "Return the customer's most recent orders (newest first) as a JSON array."
    )
    args_schema: type[BaseModel] = _RecentOrdersArg

    def _run(self, email: str, limit: int = 5) -> str:  # type: ignore[override]
        orders = get_support_service().get_recent_orders(
            email.strip().lower(), limit=limit
        )
        return json.dumps([o.model_dump() for o in orders])
