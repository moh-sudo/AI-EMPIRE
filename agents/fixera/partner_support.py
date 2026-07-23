"""Partner Support Agent v0.1 — Fixera Division.

Partner-side issue resolution: ticket management and partner
communications. Owns notifySupportTeam.

Built against a generic mock ticket shape, same known gap as Customer
Support -- no partner-ticket view exists in the connector yet.

Per its own Boundaries: never approves or executes a payout/commission
adjustment itself -- that belongs to Financial Operations.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

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


def check_needs_escalation(ticket: dict[str, Any], now: Optional[datetime] = None) -> PartnerTicketStatus:
    """Decides whether a partner ticket needs an internal team
    notification (notifySupportTeam) -- open longer than the escalation
    window, or explicitly flagged high-priority regardless of age."""
    now = now or datetime.now(timezone.utc)

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
        return PartnerTicketStatus(ticket["id"], True, round(hours_open, 1), f"open {hours_open:.1f}h, exceeds {ESCALATE_TO_TEAM_AFTER_HOURS}h window")
    return PartnerTicketStatus(ticket["id"], False, round(hours_open, 1), "within window")


def build_team_notification(ticket: dict[str, Any], status: PartnerTicketStatus) -> dict[str, str]:
    """notifySupportTeam content -- goes to Fixera's internal support
    team, not to the partner."""
    return {
        "subject": f"Partner ticket #{ticket.get('id')} needs attention",
        "html": f"<p>Reason: {status.reason}</p><p>Partner: {ticket.get('partner_id', 'unknown')}</p>",
    }
