"""Trust & Safety Agent v0.1 — Fixera Division.

Marketplace integrity: dispute triage, review-pattern fraud detection,
partner KYC re-verification scheduling. Built against mock data
matching ai_empire_disputes_summary / ai_empire_reviews_summary
(connector still unresolved -- see CONTEXT.md).

This agent may NEVER unilaterally ban/suspend/penalize (per its own
Boundaries in shared/prompts/fixera_trust-safety_v1.json) -- v0.1
scope is triage and flagging only, never an autonomous action.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

SLA_ESCALATION_HOURS = 48  # a dispute open this long without resolution gets flagged
FRAUD_REVIEW_COUNT_THRESHOLD = 3  # this many low ratings for one reviewee in the window below
FRAUD_REVIEW_WINDOW_DAYS = 7


@dataclass
class DisputeTriage:
    dispute_id: str
    priority: str  # "routine" | "sla_risk" | "overdue"
    reason: str


def triage_dispute(dispute: dict[str, Any], now: Optional[datetime] = None) -> DisputeTriage:
    """Flags disputes at risk of breaching SLA. Never rules on a dispute --
    ruling is a human/admin decision (dispute.ruling stays untouched)."""
    now = now or datetime.now(timezone.utc)
    if dispute.get("status") in ("resolved",):
        return DisputeTriage(dispute["id"], "routine", "already resolved")

    submitted_at = dispute.get("customer_submitted_at") or dispute.get("created_at")
    if not submitted_at:
        return DisputeTriage(dispute["id"], "routine", "no submission timestamp available")

    if isinstance(submitted_at, str):
        submitted_at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))

    age = now - submitted_at
    if age > timedelta(hours=SLA_ESCALATION_HOURS):
        return DisputeTriage(dispute["id"], "overdue", f"open {age.total_seconds() / 3600:.1f}h, exceeds {SLA_ESCALATION_HOURS}h SLA")
    if age > timedelta(hours=SLA_ESCALATION_HOURS * 0.75):
        return DisputeTriage(dispute["id"], "sla_risk", f"open {age.total_seconds() / 3600:.1f}h, approaching {SLA_ESCALATION_HOURS}h SLA")
    return DisputeTriage(dispute["id"], "routine", "within SLA window")


@dataclass
class FraudSignal:
    reviewee_id: str
    reviewee_type: str
    low_rating_count: int
    reason: str


def detect_review_pattern_signals(
    reviews: list[dict[str, Any]],
    now: Optional[datetime] = None,
    low_rating_threshold: int = 2,
) -> list[FraudSignal]:
    """Flags reviewees (not reviewers -- rating patterns targeting one
    partner/customer) with an unusual cluster of low ratings in a short
    window. This is a signal to surface for human review, never an
    automatic penalty -- matches the agent's Boundaries."""
    now = now or datetime.now(timezone.utc)
    window_start = now - timedelta(days=FRAUD_REVIEW_WINDOW_DAYS)

    recent_low_ratings: Counter[tuple[str, str]] = Counter()
    for review in reviews:
        if (review.get("rating") or 5) > low_rating_threshold:
            continue
        created_at = review.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if not created_at or created_at < window_start:
            continue
        key = (review["reviewee_id"], review.get("reviewee_type", "unknown"))
        recent_low_ratings[key] += 1

    signals = []
    for (reviewee_id, reviewee_type), count in recent_low_ratings.items():
        if count >= FRAUD_REVIEW_COUNT_THRESHOLD:
            signals.append(FraudSignal(
                reviewee_id, reviewee_type, count,
                f"{count} ratings <= {low_rating_threshold} within {FRAUD_REVIEW_WINDOW_DAYS} days",
            ))
    return signals


def workers_due_for_kyc_reverification(
    workers: list[dict[str, Any]],
    reverification_interval_days: int = 365,
    now: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Flags verified workers whose verification is old enough to warrant
    re-checking. Uses `created_at` as a stand-in for last-verified date
    since ai_empire_workers_summary doesn't expose a dedicated
    verification-date column -- a real implementation would need that
    added to the view."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=reverification_interval_days)
    due = []
    for worker in workers:
        if worker.get("verification_status") != "verified":
            continue
        created_at = worker.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if created_at and created_at < cutoff:
            due.append(worker)
    return due


def run_trust_safety_sweep() -> dict[str, Any]:
    """Live entry point: fetches real disputes/reviews/workers via the
    Fixera connector and runs all three checks. psycopg2 returns
    timestamp columns as timezone-aware datetime objects already (not
    strings), which the isinstance(str) branches in each check below
    handle transparently -- no special-casing needed for live vs mock
    data."""
    from shared.fixera_connector import fetch_all

    disputes = fetch_all("disputes")
    reviews = fetch_all("reviews")
    workers = fetch_all("workers")

    dispute_triage = [triage_dispute(d) for d in disputes]
    fraud_signals = detect_review_pattern_signals(reviews)
    kyc_due = workers_due_for_kyc_reverification(workers)

    return {
        "dispute_triage": [t for t in dispute_triage if t.priority != "routine"],
        "fraud_signals": fraud_signals,
        "kyc_reverification_due": [w.get("id") for w in kyc_due],
    }
