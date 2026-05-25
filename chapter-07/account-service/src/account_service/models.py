"""Pydantic models for the mocked account service HTTP contract."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


HealthStatus = Literal["healthy", "watch", "at_risk"]
TicketSeverity = Literal["low", "medium", "high"]
TicketStatus = Literal["open", "waiting_on_customer", "resolved"]
InvoiceStatus = Literal["paid", "open", "overdue"]


class AccountSummary(BaseModel):
    account_id: str
    name: str
    tier: Literal["growth", "enterprise", "strategic"]
    owner: str
    renewal_date: str
    arr_usd: int
    health: HealthStatus


class Contact(BaseModel):
    name: str
    role: str
    email: str
    influence: Literal["decision_maker", "champion", "technical", "finance"]


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
    severity: TicketSeverity
    status: TicketStatus
    opened_at: str
    product_area: str


class Invoice(BaseModel):
    invoice_id: str
    amount_usd: int
    due_date: str
    status: InvoiceStatus


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


class TaskCreate(BaseModel):
    account_id: str
    title: str
    details: str
    due_date: Optional[str] = None
    source: str = "account-assistant"


class TaskOut(TaskCreate):
    task_id: str
    created_at: str


class EmailDraftCreate(BaseModel):
    account_id: str
    to: list[str]
    subject: str
    body_markdown: str


class EmailDraftOut(EmailDraftCreate):
    draft_id: str
    created_at: str


class CalendarEventCreate(BaseModel):
    account_id: str
    slot_id: str
    title: str
    attendees: list[str]


class CalendarEventOut(CalendarEventCreate):
    event_id: str
    starts_at: str
    ends_at: str
    created_at: str
