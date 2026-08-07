"""Partner Support Agent v0.1 — Fixera Division.

Partner-side issue resolution: ticket management and partner
communications. Owns notifySupportTeam.

Reads real tickets via shared.fixera_connector's ai_empire_tickets_summary
view (support_tickets.user_type='partner').

Per its own Boundaries: never approves or executes a payout/commission
adjustment itself -- that belongs to Financial Operations.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# Partner tickets get a tighter escalation window than customer tickets --
# partners are the supply side of the marketplace, an unresolved partner
# issue can mean a worker stops taking jobs.
ESCALATE_TO_TEAM_AFTER_HOURS = 12


@dataclass
class PartnerTicketStatus:
    ticket_id: str
    needs_team_notification: bool
    hours_open: float
    reason: str


def check_needs_escalation(ticket: dict[str, Any], now: datetime | None = None) -> PartnerTicketStatus:
    """Decides whether a partner ticket needs an internal team
    notification (notifySupportTeam) -- open longer than the escalation
    window, or explicitly flagged high-priority regardless of age."""
    now = now or datetime.now(UTC)

    if ticket.get("status") in ("resolved", "closed"):
        return PartnerTicketStatus(ticket["id"], False, 0.0, "already resolved")

    if ticket.get("priority") == "urgent":
        return PartnerTicketStatus(ticket["id"], True, 0.0, "flagged urgent")

    created_at = ticket.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if not created_at:
        return PartnerTicketStatus(ticket["id"], False, 0.0, "no creation timestamp available")

    hours_open = (now - created_at).total_seconds() / 3600
    if hours_open > ESCALATE_TO_TEAM_AFTER_HOURS:
        return PartnerTicketStatus(
            ticket["id"],
            True,
            round(hours_open, 1),
            f"open {hours_open:.1f}h, exceeds {ESCALATE_TO_TEAM_AFTER_HOURS}h window",
        )
    return PartnerTicketStatus(ticket["id"], False, round(hours_open, 1), "within window")


def build_team_notification(ticket: dict[str, Any], status: PartnerTicketStatus) -> dict[str, str]:
    """notifySupportTeam content -- goes to Fixera's internal support
    team, not to the partner. Uses `user_id` (the actual support_tickets
    column, confirmed via information_schema) -- an earlier version of
    this used a nonexistent `partner_id` field, fixed when wiring to
    real data."""
    return {
        "subject": f"Partner ticket #{ticket.get('id')} needs attention",
        "html": f"<p>Reason: {status.reason}</p><p>Partner: {ticket.get('user_id', 'unknown')}</p>",
    }


def run_partner_support_sweep() -> list[dict[str, Any]]:
    """Live entry point: fetches real tickets via the Fixera connector,
    filters to partner-side tickets, and returns notifications for those
    needing team escalation."""
    from shared.fixera_connector import fetch_all

    tickets = fetch_all("tickets")
    partner_tickets = [t for t in tickets if t.get("user_type") == "partner"]

    notifications = []
    for ticket in partner_tickets:
        status = check_needs_escalation(ticket)
        if status.needs_team_notification:
            notifications.append(build_team_notification(ticket, status))
    return notifications
