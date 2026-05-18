"""Tool exposing active product incidents to the technical specialist."""

from __future__ import annotations

import json
from typing import Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from gmail_support_flow.services import get_support_service
from gmail_support_flow.state import PlanTier


class _IncidentArg(BaseModel):
    plan_tier: Optional[PlanTier] = Field(
        default=None,
        description="Filter incidents affecting this plan tier.",
    )
    product_area: Optional[str] = Field(
        default=None,
        description=(
            "Optional product-area filter, e.g. 'api_exports', 'dashboard', 'billing'."
        ),
    )


class CheckActiveIncidentsTool(BaseTool):
    name: str = "check_active_incidents"
    description: str = (
        "Return active (non-resolved) product incidents, optionally filtered by "
        "plan tier and product area. Returns a JSON array."
    )
    args_schema: type[BaseModel] = _IncidentArg

    def _run(  # type: ignore[override]
        self,
        plan_tier: Optional[str] = None,
        product_area: Optional[str] = None,
    ) -> str:
        hits = get_support_service().active_incidents(
            plan_tier=plan_tier,  # type: ignore[arg-type]
            product_area=product_area,
        )
        return json.dumps([h.model_dump() for h in hits])
