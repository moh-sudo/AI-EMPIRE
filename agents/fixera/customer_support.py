"""Customer Support Agent v0.1 — Fixera Division.

Customer issue resolution: ticket triage and status communication.
Owns sendSupportTicketConfirmation and sendTicketStatusUpdate.

Reads real tickets via shared.fixera_connector's ai_empire_tickets_summary
view (support_tickets.user_type='customer'). That view excludes free-text
subject/message content, admin_note, and user PII (name/email) -- see
infrastructure/fixera_connector_reference.sql.

Per its own Boundaries: never approves or executes a refund itself --
that belongs to Financial Operations. This agent communicates status
(including reading an already-made refund_decision), it doesn't
authorize payment.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

SLA_HOURS_BY_PRIORITY = {
    "urgent": 4,
    "high": 8,  # confirmed a real value in production support_tickets.priority
    "normal": 24,
    "low": 72,
}
DEFAULT_PRIORITY = "normal"


@dataclass
class TicketTriage:
    ticket_id: str
    priority: str
    sla_status: str  # "within_sla" | "at_risk" | "breached"
    hours_open: float


def triage_ticket(ticket: dict[str, Any], now: Optional[datetime] = None) -> TicketTriage:
    """SLA status for an open support ticket. Closed/resolved tickets are
    always within_sla regardless of age."""
    now = now or datetime.now(timezone.utc)
    priority = ticket.get("priority") or DEFAULT_PRIORITY
    sla_hours = SLA_HOURS_BY_PRIORITY.get(priority, SLA_HOURS_BY_PRIORITY[DEFAULT_PRIORITY])

    if ticket.get("status") in ("resolved", "closed"):
        return TicketTriage(ticket["id"], priority, "within_sla", 0.0)

    created_at = ticket.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if not created_at:
        return TicketTriage(ticket["id"], priority, "within_sla", 0.0)

    hours_open = (now - created_at).total_seconds() / 3600
    if hours_open > sla_hours:
        sla_status = "breached"
    elif hours_open > sla_hours * 0.75:
        sla_status = "at_risk"
    else:
        sla_status = "within_sla"
    return TicketTriage(ticket["id"], priority, sla_status, round(hours_open, 1))


def prioritize_queue(tickets: list[dict[str, Any]], now: Optional[datetime] = None) -> list[TicketTriage]:
    """Sorts open tickets by SLA urgency: breached first, then at_risk,
    then within_sla, each ordered by hours open (longest-waiting first)."""
    now = now or datetime.now(timezone.utc)
    status_rank = {"breached": 0, "at_risk": 1, "within_sla": 2}
    triaged = [triage_ticket(t, now) for t in tickets if t.get("status") not in ("resolved", "closed")]
    return sorted(triaged, key=lambda t: (status_rank[t.sla_status], -t.hours_open))


def build_status_update_email(ticket: dict[str, Any], new_status: str, recipient_email: str) -> dict[str, str]:
    """sendTicketStatusUpdate content. Never mentions a refund decision --
    refund authorization belongs to Financial Operations, this agent only
    communicates ticket status."""
    return {
        "to": recipient_email,
        "subject": f"Update on your support ticket #{ticket.get('id')}",
        "html": f"<p>Your ticket status is now: {new_status}.</p>",
    }


def run_support_queue_sweep() -> list[TicketTriage]:
    """Live entry point: fetches real tickets via the Fixera connector,
    filters to customer-side tickets, and returns the prioritized queue."""
    from shared.fixera_connector import fetch_all

    tickets = fetch_all("tickets")
    customer_tickets = [t for t in tickets if t.get("user_type") == "customer"]
    return prioritize_queue(customer_tickets)
