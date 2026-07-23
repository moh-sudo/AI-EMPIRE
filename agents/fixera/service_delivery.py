"""Service Delivery Agent v0.1 — Fixera Division.

Booking lifecycle + dispatch. Built against mock data matching the
ai_empire_bookings_summary / ai_empire_workers_summary view schemas
documented in infrastructure/fixera_connector_reference.sql, since the
live connector isn't working yet (see CONTEXT.md Session Log,
2026-07-23). Ready to plug into real data once the connector is fixed.

Dispatch logic matches Fixera's own roadmap note: "Phase 1 uses flat
pool with wallet gate" -- the fuller multi-factor Dispatch Decision
Framework (Eligibility -> Trade Match -> Wallet Compliance -> Distance
-> Rating -> Workload -> ETA) is Fixera's own future Phase 2, not
implemented here. GPS tracking is not implemented in v0.1 -- no live
telemetry source to build against yet.
"""

from dataclasses import dataclass
from typing import Any, Optional

DEFAULT_WALLET_MINIMUM = 500  # KSh -- matches the value Fixera's own trg_wallet_gate
# is documented to use (even though we found it isn't actually enforced in
# production). Never hardcoded elsewhere -- always passed as a parameter so a
# real platform_settings.wallet_minimum value can override it once available.


def is_eligible_worker(worker: dict[str, Any], booking: dict[str, Any], wallet_minimum: float) -> bool:
    """Phase 1 eligibility: online/available, matching service, wallet gate."""
    if worker.get("status") != "online" and not worker.get("is_available"):
        return False
    if not worker.get("onboarding_complete"):
        return False
    if worker.get("verification_status") != "verified":
        return False
    if worker.get("service") != booking.get("service"):
        return False
    if (worker.get("wallet_balance") or 0) < wallet_minimum:
        return False
    return True


def match_partner(
    booking: dict[str, Any],
    worker_pool: list[dict[str, Any]],
    wallet_minimum: float = DEFAULT_WALLET_MINIMUM,
) -> Optional[dict[str, Any]]:
    """Flat-pool matching: filter to eligible workers, then pick by
    highest rating, breaking ties by lowest total_jobs (load balancing --
    prefer workers who've had fewer jobs among equally-rated options)."""
    eligible = [w for w in worker_pool if is_eligible_worker(w, booking, wallet_minimum)]
    if not eligible:
        return None
    eligible.sort(key=lambda w: (-(w.get("rating") or 0), w.get("total_jobs") or 0))
    return eligible[0]


@dataclass
class LifecycleEvent:
    event: str  # "confirmed" | "cancelled" | "completed"
    booking: dict[str, Any]


def detect_lifecycle_event(old_status: str, new_status: str, booking: dict[str, Any]) -> Optional[LifecycleEvent]:
    """Detect a booking status transition worth acting on."""
    if old_status == new_status:
        return None
    if new_status == "cancelled":
        return LifecycleEvent("cancelled", booking)
    if new_status == "completed":
        return LifecycleEvent("completed", booking)
    if old_status in ("pending", "upcoming") and new_status == "confirmed":
        return LifecycleEvent("confirmed", booking)
    return None


# Email ownership per the Master Governance doc: Service Delivery owns
# sendBookingConfirmation, sendReceipt, sendCancellationConfirmation.
#
# NOTE: ai_empire_bookings_summary deliberately excludes customer email/phone
# (PII minimization, see infrastructure/fixera_connector_reference.sql). This
# agent can decide *that* an email should fire, but can't look up *who* to
# send it to -- that requires either extending the connector view (a
# deliberate privacy trade-off, not to be done by accident) or Fixera's own
# system supplying the recipient when it invokes this agent. Send functions
# below take an explicit recipient rather than pretending to have one.

EVENT_TO_EMAIL_SUBJECT = {
    "confirmed": "Booking Confirmed",
    "completed": "Your Receipt",
    "cancelled": "Booking Cancelled",
}


def build_lifecycle_email(event: LifecycleEvent, recipient_email: str) -> dict[str, str]:
    """Builds the email params for a lifecycle event. Caller sends it via
    shared.notifications.resend_client.send_email -- kept separate so this
    stays testable without hitting the real Resend API."""
    booking = event.booking
    subject = EVENT_TO_EMAIL_SUBJECT[event.event]
    if event.event == "confirmed":
        html = f"<p>Your booking for {booking.get('service')} is confirmed.</p>"
    elif event.event == "completed":
        html = f"<p>Thanks for using Fixera. Amount: {booking.get('price')}.</p>"
    else:  # cancelled
        reason = booking.get("cancellation_reason") or "no reason given"
        html = f"<p>Your booking for {booking.get('service')} was cancelled ({reason}).</p>"
    return {"to": recipient_email, "subject": subject, "html": html}
