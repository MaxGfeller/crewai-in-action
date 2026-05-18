"""Typed Pydantic state for the Gmail support Flow.

Everything on ``SupportFlowState`` is JSON-serialisable so ``@persist`` can
snapshot the whole object to SQLite after each method. We deliberately keep
every nested model in this single file so a chapter listing can show the
full state schema at once.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from crewai.flow.flow import FlowState
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (as ``Literal`` aliases for static-friendliness and Crew YAML reuse).
# ---------------------------------------------------------------------------

RouteLabel = Literal[
    "billing",
    "technical",
    "feature_request",
    "spam",
    "needs_human",
    "retry_triage",
]

TriageCategory = Literal["billing", "technical", "feature_request", "spam", "needs_human"]
SpecialistCategory = Literal["billing", "technical", "feature_request"]
PlanTier = Literal["free", "pro", "enterprise"]
OrderStatus = Literal["pending", "shipped", "delivered", "refunded", "cancelled"]
IncidentStatus = Literal["investigating", "identified", "monitoring", "resolved"]


# ---------------------------------------------------------------------------
# Nested models.
# ---------------------------------------------------------------------------


class EmailThread(BaseModel):
    thread_id: str
    from_email: str
    from_name: Optional[str] = None
    subject: str
    body: str
    received_at: str  # ISO-8601 string, kept as str for easy JSON persistence
    labels: list[str] = Field(default_factory=list)


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


class TriageDecision(BaseModel):
    category: TriageCategory
    confidence: float
    summary_one_line: str
    detected_intent: str
    reasoning: str


class SpecialistOutput(BaseModel):
    category: SpecialistCategory
    proposed_reply_markdown: str
    kb_article_ids: list[str] = Field(default_factory=list)
    needs_followup: bool = False
    escalation_reason: Optional[str] = None


class EscalationSummary(BaseModel):
    """Payload the EscalationCrew produces; the Flow method posts it to Slack."""

    title: str
    body_markdown: str
    severity: Literal["low", "medium", "high"] = "medium"


class RouteHopEntry(BaseModel):
    at: str  # ISO datetime
    from_step: str
    to_step: str
    reason: str


# ---------------------------------------------------------------------------
# The Flow state itself.
# ---------------------------------------------------------------------------


class SupportFlowState(FlowState):
    # --- Intake ---
    # Raw payload handed to ``kickoff(inputs={"thread_payload": ...})``.
    # The @start method validates it into ``thread`` below.
    thread_payload: Optional[dict] = None
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    thread: Optional[EmailThread] = None

    # --- Context (fan-in targets of @listen(and_(...))) ---
    customer: Optional[CustomerProfile] = None
    recent_orders: list[RecentOrder] = Field(default_factory=list)
    matching_incidents: list[IncidentMatch] = Field(default_factory=list)
    context_loaded: bool = False

    # --- Triage / routing ---
    triage: Optional[TriageDecision] = None
    route_history: list[RouteHopEntry] = Field(default_factory=list)
    current_route: Optional[str] = None

    # --- Specialist work ---
    specialist_output: Optional[SpecialistOutput] = None
    escalation_summary: Optional[EscalationSummary] = None

    # --- Side-effects applied ---
    draft_id: Optional[str] = None
    applied_labels: list[str] = Field(default_factory=list)
    slack_message_ts: Optional[str] = None

    # --- Error handling / recovery ---
    retry_count: int = 0
    max_retries: int = 2
    last_error: Optional[str] = None
    escalated: bool = False
    terminal: bool = False

    # ------------------------------------------------------------------
    # Small helpers used by the Flow and listeners. These keep the
    # "mutate in place" contract of @persist clean.
    # ------------------------------------------------------------------
    def record_hop(self, from_step: str, to_step: str, reason: str = "") -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.route_history.append(
            RouteHopEntry(
                at=now.isoformat().replace("+00:00", "Z"),
                from_step=from_step,
                to_step=to_step,
                reason=reason,
            )
        )
        self.current_route = to_step
