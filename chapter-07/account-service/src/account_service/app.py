"""FastAPI app exposing mocked account and renewal systems."""

from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from account_service import store
from account_service.models import (
    AccountSummary,
    CalendarEventCreate,
    CalendarEventOut,
    EmailDraftCreate,
    EmailDraftOut,
    MeetingSlot,
    RenewalContext,
    TaskCreate,
    TaskOut,
)


app = FastAPI(
    title="account-service",
    version="0.1.0",
    description=(
        "Mock CRM, renewal, support, task, and calendar API for the Chapter 7 "
        "Customer Account Assistant."
    ),
)


def _apply_simulate(simulate: Optional[str]) -> None:
    if simulate is None:
        return
    if simulate == "fail":
        raise HTTPException(status_code=503, detail="simulated account-service failure")
    if simulate == "slow":
        time.sleep(float(os.getenv("ACCOUNT_SERVICE_SLOW_SECONDS", "3")))
        return
    raise HTTPException(status_code=400, detail="simulate must be 'fail' or 'slow'")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/accounts", response_model=list[AccountSummary])
def list_accounts(simulate: Optional[str] = None) -> list[AccountSummary]:
    _apply_simulate(simulate)
    return store.list_accounts()


@app.get("/accounts/search", response_model=AccountSummary)
def search_account(q: str = Query(min_length=2), simulate: Optional[str] = None) -> AccountSummary:
    _apply_simulate(simulate)
    account = store.find_account(q)
    if account is None:
        raise HTTPException(status_code=404, detail=f"account not found for query: {q}")
    return account


@app.get("/accounts/{account_id}/renewal-context", response_model=RenewalContext)
def renewal_context(account_id: str, simulate: Optional[str] = None) -> RenewalContext:
    _apply_simulate(simulate)
    context = store.get_context(account_id)
    if context is None:
        raise HTTPException(status_code=404, detail=f"account not found: {account_id}")
    return context


@app.get("/accounts/{account_id}/calendar-slots", response_model=list[MeetingSlot])
def meeting_slots(
    account_id: str,
    duration_minutes: int = Query(default=45, ge=15, le=120),
    simulate: Optional[str] = None,
) -> list[MeetingSlot]:
    _apply_simulate(simulate)
    if store.get_context(account_id) is None:
        raise HTTPException(status_code=404, detail=f"account not found: {account_id}")
    return store.calendar_slots(account_id, duration_minutes=duration_minutes)


@app.post("/tasks", response_model=TaskOut)
def create_task(body: TaskCreate, simulate: Optional[str] = None) -> TaskOut:
    _apply_simulate(simulate)
    if store.get_context(body.account_id) is None:
        raise HTTPException(status_code=404, detail=f"account not found: {body.account_id}")
    return store.create_task(body)


@app.post("/email-drafts", response_model=EmailDraftOut)
def create_email_draft(
    body: EmailDraftCreate, simulate: Optional[str] = None
) -> EmailDraftOut:
    _apply_simulate(simulate)
    if store.get_context(body.account_id) is None:
        raise HTTPException(status_code=404, detail=f"account not found: {body.account_id}")
    return store.create_email_draft(body)


@app.post("/calendar-events", response_model=CalendarEventOut)
def create_calendar_event(
    body: CalendarEventCreate, simulate: Optional[str] = None
) -> CalendarEventOut:
    _apply_simulate(simulate)
    if store.get_context(body.account_id) is None:
        raise HTTPException(status_code=404, detail=f"account not found: {body.account_id}")
    try:
        return store.create_calendar_event(body)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"slot not found: {body.slot_id}") from None
