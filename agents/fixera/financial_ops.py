"""Financial Operations Agent v0.1 — Fixera Division.

Movement of money: commissions, refunds, wallet management. Built
against mock data matching ai_empire_payments_summary (connector still
unresolved -- see CONTEXT.md). M-Pesa Daraja integration is explicitly
blocked in CONTEXT.md until company registration completes, so this
agent's v0.1 scope is the *decision* only -- classifying a transaction
per the Escalation Ladder (Track 1 -- Financial). It never executes a
payment itself: the Approval Matrix is explicit that "Execute payment"
is AI Agent: No, Mohamed: Yes. Auto-processing below-threshold
transactions means clearing them for someone/something else to
execute, not executing them directly.
"""

from dataclasses import dataclass
from typing import Any

DEFAULT_APPROVAL_THRESHOLD = 5000  # KSh, per the Escalation Ladder's stated
# current approval_matrix value. Always passed as a parameter -- never
# hardcoded elsewhere -- so a real approval_matrix value can override it.

DECISION_AUTO_PROCESS = "auto_process"
DECISION_ESCALATE_HUMAN = "escalate_human"
DECISION_EMERGENCY_HOLD = "emergency_hold"


@dataclass
class TransactionDecision:
    decision: str
    reason: str


def classify_transaction(
    payment: dict[str, Any],
    threshold: float = DEFAULT_APPROVAL_THRESHOLD,
    has_active_dispute: bool = False,
    suspected_fraud: bool = False,
) -> TransactionDecision:
    """Per the Escalation Ladder (Track 1 -- Financial):
    - Emergency Hold: suspected fraud, unauthorized payment, cascading loss
    - Human Authority: above threshold, dispute-linked, or any irreversible
      action -- this agent cannot execute these itself regardless of amount
    - Auto-Process: below threshold, no active dispute, not fraud-flagged
    """
    if suspected_fraud:
        return TransactionDecision(DECISION_EMERGENCY_HOLD, "suspected fraud or unauthorized payment")

    amount = payment.get("amount") or 0
    if has_active_dispute:
        return TransactionDecision(DECISION_ESCALATE_HUMAN, "transaction is linked to an active dispute")
    if amount > threshold:
        return TransactionDecision(DECISION_ESCALATE_HUMAN, f"amount {amount} exceeds threshold {threshold}")

    return TransactionDecision(DECISION_AUTO_PROCESS, f"amount {amount} within threshold {threshold}, no dispute")


def classify_batch(
    payments: list[dict[str, Any]],
    threshold: float = DEFAULT_APPROVAL_THRESHOLD,
    disputed_ref_ids: set[str] | None = None,
    fraud_flagged_ids: set[str] | None = None,
) -> list[tuple[dict[str, Any], TransactionDecision]]:
    """Classify a batch of payments. disputed_ref_ids/fraud_flagged_ids
    are sets of payment `ref_id` values the caller already knows about
    (e.g. from ai_empire_disputes_summary once the connector works)."""
    disputed_ref_ids = disputed_ref_ids or set()
    fraud_flagged_ids = fraud_flagged_ids or set()
    results = []
    for payment in payments:
        decision = classify_transaction(
            payment,
            threshold=threshold,
            has_active_dispute=payment.get("ref_id") in disputed_ref_ids,
            suspected_fraud=payment.get("id") in fraud_flagged_ids,
        )
        results.append((payment, decision))
    return results


def run_classification_sweep(threshold: float = DEFAULT_APPROVAL_THRESHOLD) -> list[dict[str, Any]]:
    """Live entry point: fetches real payments + disputes via the Fixera
    connector, cross-references disputed booking refs, and classifies
    every payment. No fraud signal source exists yet (no fraud-detection
    view/table) -- fraud_flagged_ids stays empty rather than fabricated.
    """
    from shared.fixera_connector import fetch_all

    payments = fetch_all("payments")
    disputes = fetch_all("disputes")

    # booking_id vs payment.ref_id aren't type-checked against ref_type
    # here (a payment could reference a moving_request/supplier_order
    # instead of a booking) -- safe in practice since these are UUIDs and
    # cross-type collision is not realistically possible, but worth
    # tightening to a ref_type=='booking' filter if this gets extended.
    open_dispute_booking_ids = {d.get("booking_id") for d in disputes if d.get("status") not in ("resolved",)}

    results = []
    for payment, decision in classify_batch(payments, threshold=threshold, disputed_ref_ids=open_dispute_booking_ids):
        results.append({"payment_id": payment.get("id"), "decision": decision.decision, "reason": decision.reason})
    return results
