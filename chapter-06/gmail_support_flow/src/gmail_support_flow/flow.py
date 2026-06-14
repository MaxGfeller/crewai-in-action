"""The Gmail support triage Flow.

Flow primitives the chapter teaches, in the order they appear below:

- ``@start()`` seeds the state with the thread payload.
- Three ``@listen(intake)`` methods fan out to load Customer 360, recent
  orders, and active incidents in parallel.
- ``@listen(and_(load_customer, load_recent_orders, load_incidents))`` merges them.
- ``@listen(mark_context_loaded)`` runs the triage Crew.
- ``@router(triage)`` branches into five specialist routes.
- Specialist handlers put their output on the state (success) or bump
  ``retry_count`` + ``last_error`` (failure). They do not hide failures in
  ``try/except`` - the router decides what to do next.
- ``@router(or_(handle_billing, handle_technical, handle_feature_request))``
  reads state and returns either ``drafted`` (continue), the same
  specialist label (retry), or ``needs_human`` (escalate).
- ``@listen("drafted")`` converges the three specialist branches to a
  single "create Gmail draft" step.
- ``@persist`` snapshots state after every method so the Flow can resume
  after a Ctrl-C or crash via ``resume_flow(flow_id)``.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from crewai.flow.flow import Flow, and_, listen, or_, router, start
from crewai.flow.persistence import persist

from gmail_support_flow.crews import (
    BillingCrew,
    EscalationCrew,
    FeatureRequestCrew,
    TechnicalCrew,
    TriageCrew,
)
from gmail_support_flow.persistence.store import default_persistence
from gmail_support_flow.providers import get_gmail_provider, get_slack_provider
from gmail_support_flow.services import get_support_service
from gmail_support_flow.state import (
    EmailThread,
    EscalationSummary,
    SpecialistOutput,
    SupportFlowState,
    TriageDecision,
)


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _crew_inputs(state: SupportFlowState) -> dict[str, Any]:
    """Flatten state into a single-level dict for YAML ``{field}`` interpolation.

    CrewAI's task template only substitutes top-level keys, so nested fields
    (``customer.plan_tier``, etc.) must be lifted to siblings.
    """
    thread = state.thread
    customer = state.customer
    route_history_compact = " -> ".join(
        f"{hop.from_step}->{hop.to_step}" for hop in state.route_history
    )
    return {
        "subject": thread.subject if thread else "",
        "from_email": thread.from_email if thread else "",
        "from_name": thread.from_name if thread else "",
        "body": thread.body if thread else "",
        "plan_tier": customer.plan_tier if customer else "unknown",
        "is_vip": bool(customer.is_vip) if customer else False,
        "last_error": state.last_error or "",
        "route_history_compact": route_history_compact,
    }


@persist(default_persistence())
class SupportInboxFlow(Flow[SupportFlowState]):
    """Triage and draft replies to support emails, escalating stuck cases."""

    # ------------------------------------------------------------------
    # 1. Intake
    # ------------------------------------------------------------------
    @start()
    def intake(self) -> None:
        # Resume detection: ``@persist`` rehydrates ``self.state`` from the
        # SQLite snapshot when ``kickoff(inputs={"id": flow_id})`` is called
        # with a flow id that already has prior state. When that happens,
        # ``self.state.thread`` is already populated and ``thread_payload``
        # is None - the @start() method must NOT overwrite the resumed
        # thread, or the recovery semantics from chapter 6.6 break.
        if self.state.thread is not None:
            print(
                f"[flow] resume detected (run_id={self.state.run_id}, "
                f"thread={self.state.thread.thread_id}); skipping intake"
            )
            return

        # CrewAI wraps dict state fields in a LockedDictProxy; pydantic's
        # model_validate gate-keeps on isinstance(..., dict) so we unwrap
        # to a real dict first.
        raw = self.state.thread_payload
        payload: dict = dict(raw) if raw else {}
        if not payload:
            # Fallback: grab the next unread thread.
            unread = get_gmail_provider().list_unread(
                label=os.getenv("GMAIL_LABEL", "book-support-demo"), max_results=1
            )
            if not unread:
                raise RuntimeError("no thread_payload provided and inbox is empty")
            payload = unread[0]

        self.state.thread = EmailThread.model_validate(payload)
        self.state.record_hop("kickoff", "intake", reason="thread received")
        print(
            f"[flow] intake {self.state.thread.thread_id} "
            f"from {self.state.thread.from_email}"
        )

    # ------------------------------------------------------------------
    # 2. Context loads - three @listen(intake) run concurrently
    # ------------------------------------------------------------------
    @listen(intake)
    def load_customer(self) -> None:
        assert self.state.thread is not None
        self.state.customer = get_support_service().get_customer(
            self.state.thread.from_email.lower()
        )

    @listen(intake)
    def load_recent_orders(self) -> None:
        assert self.state.thread is not None
        self.state.recent_orders = get_support_service().get_recent_orders(
            self.state.thread.from_email.lower(), limit=5
        )

    @listen(intake)
    def load_incidents(self) -> None:
        plan = self.state.customer.plan_tier if self.state.customer else None
        self.state.matching_incidents = get_support_service().active_incidents(
            plan_tier=plan
        )

    # ------------------------------------------------------------------
    # 3. Fan-in with and_()
    # ------------------------------------------------------------------
    @listen(and_(load_customer, load_recent_orders, load_incidents))
    def mark_context_loaded(self) -> None:
        self.state.context_loaded = True
        self.state.record_hop("context_loads", "triage")
        print(
            f"[flow] context loaded "
            f"(customer={self.state.customer.plan_tier if self.state.customer else 'unknown'}, "
            f"orders={len(self.state.recent_orders)}, "
            f"incidents={len(self.state.matching_incidents)})"
        )

    # ------------------------------------------------------------------
    # 4. Triage
    # ------------------------------------------------------------------
    @listen(mark_context_loaded)
    def triage(self) -> None:
        result = TriageCrew().crew().kickoff(inputs=_crew_inputs(self.state))
        # ``output_pydantic=TriageDecision`` on the task means CrewAI already
        # validated the model for us; if it's missing the LLM returned garbage
        # and we fall through to the hard-coded needs_human decision below.
        decision = result.pydantic if isinstance(result.pydantic, TriageDecision) else None
        if decision is None:
            decision = TriageDecision(
                category="needs_human",
                confidence=0.0,
                summary_one_line="triage shape validation failed",
                detected_intent="unknown",
                reasoning=f"TriageCrew output did not validate: {result}",
            )
        self.state.triage = decision
        print(f"[flow] triage => {decision.category} (confidence={decision.confidence:.2f})")

    # ------------------------------------------------------------------
    # 5. @router: dynamic routing
    # ------------------------------------------------------------------
    @router(triage)
    def route_by_category(self) -> str:
        triage = self.state.triage
        assert triage is not None
        category = triage.category
        # Low-confidence guardrail: anything under 0.25 that isn't clearly spam
        # goes to a human. This doesn't teach retry semantics but it's the
        # cheapest safety net in production.
        if triage.confidence < 0.25 and category not in ("spam", "needs_human"):
            self.state.record_hop("route_by_category", "needs_human", reason="low confidence")
            return "needs_human"
        self.state.record_hop("route_by_category", category)
        # Explicit string returns keep Flow.plot()'s edge inference happy -
        # it parses the AST for return-string literals.
        if category == "billing":
            return "billing"
        if category == "technical":
            return "technical"
        if category == "feature_request":
            return "feature_request"
        if category == "spam":
            return "spam"
        return "needs_human"

    # ------------------------------------------------------------------
    # 6. Specialist branches
    #
    # Each handler either sets `state.specialist_output` (success) or bumps
    # `state.retry_count` + `state.last_error` (failure). No re-raise: the
    # router that follows makes the call.
    # ------------------------------------------------------------------
    @listen("billing")
    def handle_billing(self) -> None:
        self._run_specialist("billing", BillingCrew)

    @listen("technical")
    def handle_technical(self) -> None:
        self._run_specialist("technical", TechnicalCrew)

    @listen("feature_request")
    def handle_feature_request(self) -> None:
        self._run_specialist("feature_request", FeatureRequestCrew)
        if self.state.specialist_output is not None and self.state.thread is not None:
            get_support_service().log_feature_request(
                request_id=f"fr_{uuid.uuid4().hex[:8]}",
                customer_email=self.state.thread.from_email,
                summary=self.state.specialist_output.proposed_reply_markdown[:280],
                theme=None,
                logged_at=_now_iso(),
            )

    @listen("spam")
    def handle_spam(self) -> None:
        # Rule-based branch - no LLM, no Crew.
        if self.state.thread is not None:
            get_gmail_provider().apply_labels(self.state.thread.thread_id, ["spam"])
            self.state.applied_labels = ["spam"]
        self.state.record_hop("handle_spam", "finalize_spam")

    @listen("needs_human")
    def handle_needs_human(self) -> None:
        # Idempotency: never double-post on resume.
        if self.state.slack_message_ts:
            print(f"[flow] escalation already posted (ts={self.state.slack_message_ts}); skipping")
            return

        result = EscalationCrew().crew().kickoff(inputs=_crew_inputs(self.state))
        summary = (
            result.pydantic if isinstance(result.pydantic, EscalationSummary) else None
        )
        if summary is None:
            thread = self.state.thread
            summary = EscalationSummary(
                title=(
                    f"Support escalation for "
                    f"{thread.from_email if thread else 'unknown sender'}"
                ),
                body_markdown=(
                    f"*Subject:* {thread.subject if thread else '(no subject)'}\n"
                    f"*Last error:* {self.state.last_error or 'n/a'}\n"
                    f"*Triage:* "
                    f"{self.state.triage.category if self.state.triage else 'n/a'}\n"
                ),
                severity="medium",
            )
        self.state.escalation_summary = summary

        slack = get_slack_provider()
        channel = os.getenv("SLACK_CHANNEL", "#support-escalations")
        ts = slack.post_message(
            channel=channel,
            title=summary.title,
            body_markdown=summary.body_markdown,
            severity=summary.severity,
        )
        self.state.slack_message_ts = ts
        self.state.escalated = True
        self.state.record_hop("handle_needs_human", "finalize_escalation")
        print(f"[flow] slack escalation posted ts={ts}")

    # ------------------------------------------------------------------
    # 7. @router after specialist: retry, escalate, or draft.
    # ------------------------------------------------------------------
    @router(or_(handle_billing, handle_technical, handle_feature_request))
    def route_specialist_outcome(self) -> str:
        # Success path: the specialist produced a validated output.
        if self.state.specialist_output is not None:
            self.state.record_hop("route_specialist_outcome", "drafted")
            return "drafted"

        # Failure path - decide retry vs. escalate.
        if self.state.retry_count >= self.state.max_retries:
            self.state.record_hop(
                "route_specialist_outcome",
                "needs_human",
                reason=f"exhausted retries: {self.state.last_error}",
            )
            return "needs_human"

        # Re-dispatch to the same specialist route. Explicit string returns
        # keep Flow.plot()'s edge inference accurate.
        category = self.state.triage.category if self.state.triage else "needs_human"
        self.state.record_hop(
            "route_specialist_outcome",
            category,
            reason=f"retry {self.state.retry_count}/{self.state.max_retries}",
        )
        if category == "billing":
            return "billing"
        if category == "technical":
            return "technical"
        if category == "feature_request":
            return "feature_request"
        return "needs_human"

    # ------------------------------------------------------------------
    # 8. Convergence + draft creation
    # ------------------------------------------------------------------
    @listen("drafted")
    def converge_specialist(self) -> None:
        assert self.state.specialist_output is not None
        assert self.state.thread is not None
        provider = get_gmail_provider()
        draft_id = provider.create_draft(
            thread_id=self.state.thread.thread_id,
            body_markdown=self.state.specialist_output.proposed_reply_markdown,
        )
        labels = list({*self.state.applied_labels, "drafted", self.state.specialist_output.category})
        provider.apply_labels(self.state.thread.thread_id, labels)
        self.state.draft_id = draft_id
        self.state.applied_labels = labels
        self.state.terminal = True
        self.state.record_hop("converge_specialist", "finalize_success")
        print(f"[flow] draft created: {draft_id} labels={labels}")
        print("[flow] terminal (success)")

    # ------------------------------------------------------------------
    # 9. Terminal states for escalation and spam
    # ------------------------------------------------------------------
    @listen(handle_needs_human)
    def finalize_escalation(self) -> None:
        if not self.state.escalated:
            return
        self.state.terminal = True
        print("[flow] terminal (escalated)")

    @listen(handle_spam)
    def finalize_spam(self) -> None:
        self.state.terminal = True
        print("[flow] terminal (spam)")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _run_specialist(self, route: str, crew_cls: type) -> None:
        """Run one specialist Crew. On failure, update state for the router."""
        try:
            # Chapter 6.6 deterministic failure path: if the thread body
            # carries the "KB-POISON" marker, force a real HTTP failure
            # against the support service with ``simulate=fail``. This
            # surfaces as ``httpx.HTTPStatusError`` in the event log,
            # which is exactly the failure shape production Flows see
            # when an upstream service misbehaves.
            if self.state.thread and "KB-POISON" in self.state.thread.body:
                get_support_service().search_kb(
                    query=self.state.thread.body, simulate="fail"
                )
            result = crew_cls().crew().kickoff(inputs=_crew_inputs(self.state))
            parsed = (
                result.pydantic
                if isinstance(result.pydantic, SpecialistOutput)
                else None
            )
            if parsed is None:
                raise ValueError("specialist output did not validate against SpecialistOutput")
            self.state.specialist_output = parsed
            self.state.last_error = None
            self.state.record_hop(f"handle_{route}", "route_specialist_outcome")
        except Exception as exc:
            self.state.specialist_output = None
            self.state.last_error = f"{type(exc).__name__}: {exc}"
            self.state.retry_count += 1
            self.state.record_hop(
                f"handle_{route}", "route_specialist_outcome",
                reason=f"failed: {self.state.last_error}",
            )
            print(
                f"[flow] {route} failed (attempt {self.state.retry_count}/"
                f"{self.state.max_retries}): {self.state.last_error}"
            )
            # Deliberately do NOT re-raise - the router decides the next hop.
