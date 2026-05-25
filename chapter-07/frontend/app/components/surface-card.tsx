import { AlertTriangle, CalendarClock, ListChecks, Mail, ShieldCheck } from "lucide-react";

import { Metric } from "./metric";
import type { UiSurface } from "./types";

export function SurfaceCard({ surface }: { surface: UiSurface }) {
  if (surface.type === "account_health_card") {
    const account = surface.payload.account ?? {};
    const usage = surface.payload.usage ?? {};
    const contract = surface.payload.contract ?? {};
    const contacts = surface.payload.contacts ?? [];
    const tickets = surface.payload.tickets ?? [];
    const invoices = surface.payload.invoices ?? [];

    return (
      <article className="surface accountSurface">
        <header>
          <ShieldCheck size={20} />
          <div>
            <p className="eyebrow">Account brief</p>
            <h2>{surface.title}</h2>
          </div>
        </header>
        <div className="surfaceGrid">
          <Metric label="Owner" value={account.owner ?? "unknown"} />
          <Metric label="ARR" value={`$${Number(account.arr_usd ?? 0).toLocaleString()}`} />
          <Metric label="Renewal" value={contract.renewal_date ?? account.renewal_date ?? "-"} />
          <Metric label="Usage trend" value={`${usage.active_users_change_pct ?? 0}%`} />
        </div>
        <div className="tagRow">
          <span className={`health health-${account.health}`}>{account.health}</span>
          <span>{Math.round(usage.seats_used_pct ?? 0)}% seats active</span>
          <span>{invoices.filter((invoice: any) => invoice.status === "overdue").length} overdue invoices</span>
        </div>
        <div className="surfaceColumns">
          <section>
            <h3>Buying group</h3>
            <div className="compactList">
              {contacts.slice(0, 3).map((contact: any) => (
                <div key={contact.email}>
                  <strong>{contact.name}</strong>
                  <span>{contact.role} / {contact.influence}</span>
                </div>
              ))}
            </div>
          </section>
          <section>
            <h3>Open support</h3>
            <div className="compactList">
              {tickets.map((ticket: any) => (
                <div key={ticket.ticket_id}>
                  <strong>{ticket.ticket_id}</strong>
                  <span>{ticket.severity} / {ticket.title}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </article>
    );
  }

  if (surface.type === "renewal_risk_card") {
    const payload = surface.payload;
    return (
      <article className="surface riskSurface">
        <header>
          <AlertTriangle size={20} />
          <div>
            <p className="eyebrow">Risk review</p>
            <h2>{payload.risk_level} renewal risk</h2>
          </div>
        </header>
        <p>{payload.summary}</p>
        <ul>
          {(payload.risks ?? []).map((risk: string) => <li key={risk}>{risk}</li>)}
        </ul>
      </article>
    );
  }

  if (surface.type === "meeting_slots_card") {
    return (
      <article className="surface">
        <header>
          <CalendarClock size={20} />
          <div>
            <p className="eyebrow">Calendar</p>
            <h2>{surface.title}</h2>
          </div>
        </header>
        <div className="slotList">
          {(surface.payload.slots ?? []).map((slot: any) => (
            <div className="slot" key={slot.slot_id}>{slot.label}</div>
          ))}
        </div>
      </article>
    );
  }

  if (surface.type === "support_issues_card") {
    return (
      <article className="surface supportSurface">
        <header>
          <ListChecks size={20} />
          <div>
            <p className="eyebrow">Support</p>
            <h2>{surface.title}</h2>
          </div>
        </header>
        <div className="compactList">
          {(surface.payload.tickets ?? []).map((ticket: any) => (
            <div key={ticket.ticket_id}>
              <strong>{ticket.ticket_id}: {ticket.title}</strong>
              <span>{ticket.severity} / {ticket.status} / {ticket.product_area}</span>
            </div>
          ))}
        </div>
      </article>
    );
  }

  return (
    <article className="surface">
      <header>
        <Mail size={20} />
        <div>
          <p className="eyebrow">{surface.type}</p>
          <h2>{surface.title}</h2>
        </div>
      </header>
      <pre>{JSON.stringify(surface.payload, null, 2)}</pre>
    </article>
  );
}
