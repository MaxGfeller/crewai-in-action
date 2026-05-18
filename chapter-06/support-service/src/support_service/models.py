"""Pydantic response models for the support service HTTP API.

These shapes are also consumed (as plain JSON) by the Gmail support
Flow. The Flow defines its own Pydantic models mirroring these; we
deliberately do not share a module across the service boundary, because
that would defeat the point of modelling this as an external system.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

PlanTier = Literal["free", "pro", "enterprise"]
OrderStatus = Literal["pending", "shipped", "delivered", "refunded", "cancelled"]
IncidentStatus = Literal["investigating", "identified", "monitoring", "resolved"]


class CustomerProfile(BaseModel):
    email: str
    name: str
    plan_tier: PlanTier
    is_vip: bool
    signup_date: str
    prior_ticket_count: int


class RecentOrder(BaseModel):
    order_id: str
    placed_at: str
    status: OrderStatus
    total_usd: float
    items: list[str]


class IncidentMatch(BaseModel):
    incident_id: str
    title: str
    status: IncidentStatus
    started_at: str
    product_area: Optional[str] = None
    affected_plans: list[PlanTier] = Field(default_factory=list)


class KbArticle(BaseModel):
    id: str
    theme: str
    title: str
    body: str


class FeatureRequestIn(BaseModel):
    request_id: str
    customer_email: str
    summary: str
    theme: Optional[str] = None
    logged_at: str


class FeatureRequestOut(FeatureRequestIn):
    pass
