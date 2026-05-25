"""Shared models for the assistant side of the account-service boundary."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class AccountSummary(BaseModel):
    account_id: str
    name: str
    tier: str
    owner: str
    renewal_date: str
    arr_usd: int
    health: Literal["healthy", "watch", "at_risk"]


class Contact(BaseModel):
    name: str
    role: str
    email: str
    influence: str


class ContractTerms(BaseModel):
    account_id: str
    renewal_date: str
    notice_period_days: int
    auto_renews: bool
    payment_terms: str
    discount_expires: Optional[str] = None
    contracted_seats: int
    special_terms: list[str] = Field(default_factory=list)


class UsageSignal(BaseModel):
    account_id: str
    active_users: int
    active_users_change_pct: float
    seats_used_pct: float
    weekly_projects: int
    weekly_projects_change_pct: float
    last_admin_login: str
    notable_features: list[str] = Field(default_factory=list)


class SupportTicket(BaseModel):
    ticket_id: str
    title: str
    severity: Literal["low", "medium", "high"]
    status: str
    opened_at: str
    product_area: str


class Invoice(BaseModel):
    invoice_id: str
    amount_usd: int
    due_date: str
    status: Literal["paid", "open", "overdue"]


class MeetingSlot(BaseModel):
    slot_id: str
    starts_at: str
    ends_at: str
    label: str


class RenewalContext(BaseModel):
    account: AccountSummary
    contacts: list[Contact] = Field(default_factory=list)
    contract: ContractTerms
    usage: UsageSignal
    tickets: list[SupportTicket] = Field(default_factory=list)
    invoices: list[Invoice] = Field(default_factory=list)


class ContractRiskReview(BaseModel):
    account_id: str
    risk_level: Literal["low", "medium", "high"]
    summary: str
    risks: list[str] = Field(default_factory=list)
    recommended_questions: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class TaskCreate(BaseModel):
    account_id: str
    title: str
    details: str
    due_date: Optional[str] = None
    source: str = "account-assistant"


class EmailDraftCreate(BaseModel):
    account_id: str
    to: list[str]
    subject: str
    body_markdown: str


class CalendarEventCreate(BaseModel):
    account_id: str
    slot_id: str
    title: str
    attendees: list[str]
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
