"""CEO/Lead Agent -- Fixera Division.

Aggregates all 8 Fixera agents' live sweeps into one combined daily
briefing, same role Forex's CEO/Lead Agent plays for that division
(governance Law 12, Chain of Command & Agent Authority Matrix, applied
at the division level) -- Work Quality Authority only, never
Constitutional Authority. This agent reports what the other 8 agents
found; it never approves, executes, or modifies anything itself. Each
underlying agent already enforces its own boundaries (Partner
Verification never changes verification_status, Financial Ops never
executes a payment, Platform Governance never modifies schema, Service
Delivery never actually assigns a booking) -- this agent adds none of
that authority, it just gives Mohamed one voice instead of 8 separate
pings.

Unlike Forex's 11 agents, none of Fixera's 8 write to memory_knowledge
themselves -- they're pure functions returning structured data to
whatever calls them. This agent calls each one's run_*_sweep() live
entry point directly (matching exactly how Forex's CEO/Lead calls
Research/News Filter/Market Analytics/Performance Review), then
persists the combined summary itself.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any


def _section(
    title: str, items: list, empty_message: str, formatter: Callable[[Any], str] = str, limit: int = 15
) -> str:
    """Shared formatting helper: a titled section reporting either a
    clean/empty state or a capped list of items. Caps at `limit` items
    with a '+N more' note so one noisy agent can't blow out the whole
    report -- the full data is still in that agent's own return value
    for anyone who needs it, this is just the summary."""
    if not items:
        return f"{title}: {empty_message}"
    shown = items[:limit]
    lines = [f"  - {formatter(i)}" for i in shown]
    if len(items) > limit:
        lines.append(f"  ... and {len(items) - limit} more")
    return f"{title} ({len(items)}):\n" + "\n".join(lines)


def run_daily_briefing() -> dict:
    """Live entry point: calls all 8 Fixera agents' sweeps, aggregates
    into one combined report. Each call is isolated in its own
    try/except -- one agent's failure (e.g. a connector hiccup) must
    never take down the whole briefing, same fail-safe principle
    already used by Forex's CEO/Lead run_daily_briefing()."""
    from agents.fixera._memory_helpers import safe_add_knowledge

    sections: list[str] = []

    try:
        from agents.fixera.service_delivery import run_dispatch_sweep

        results = run_dispatch_sweep()
        unmatched = [r for r in results if not r.get("matched_worker_id")]
        sections.append(
            _section(
                "SERVICE DELIVERY",
                results,
                "no unassigned bookings needing dispatch.",
                formatter=lambda r: (
                    f"booking {r.get('booking_id')} -> "
                    + (
                        f"matched worker {r['matched_worker_id']}"
                        if r.get("matched_worker_id")
                        else "NO ELIGIBLE WORKER FOUND"
                    )
                ),
            )
            + (f"\n  ({len(unmatched)} of {len(results)} found no eligible worker)" if unmatched else "")
        )
    except Exception as e:
        sections.append(f"SERVICE DELIVERY: unavailable ({e})")

    try:
        from agents.fixera.financial_ops import DECISION_AUTO_PROCESS, run_classification_sweep

        results = run_classification_sweep()
        escalations = [r for r in results if r["decision"] != DECISION_AUTO_PROCESS]
        sections.append(
            _section(
                "FINANCIAL OPERATIONS",
                escalations,
                f"{len(results)} payment(s) classified, none needing escalation.",
                formatter=lambda r: f"payment {r['payment_id']}: {r['decision']} -- {r['reason']}",
            )
        )
    except Exception as e:
        sections.append(f"FINANCIAL OPERATIONS: unavailable ({e})")

    try:
        from agents.fixera.trust_safety import run_trust_safety_sweep

        r = run_trust_safety_sweep()
        parts = []
        if r["dispute_triage"]:
            parts.append(
                _section(
                    "  Disputes needing attention",
                    r["dispute_triage"],
                    "",
                    formatter=lambda t: f"{t.dispute_id}: {t.priority} ({t.reason})",
                )
            )
        if r["fraud_signals"]:
            parts.append(_section("  Fraud signals", r["fraud_signals"], "", formatter=str))
        if r["kyc_reverification_due"]:
            parts.append(f"  KYC re-verification due: {len(r['kyc_reverification_due'])} worker(s)")
        sections.append(
            "TRUST & SAFETY:\n" + "\n".join(parts)
            if parts
            else "TRUST & SAFETY: clean -- no disputes at risk, no fraud signals, no KYC re-verifications due."
        )
    except Exception as e:
        sections.append(f"TRUST & SAFETY: unavailable ({e})")

    try:
        from agents.fixera.platform_governance import run_governance_sweep

        findings = run_governance_sweep()
        sections.append(
            _section(
                "PLATFORM GOVERNANCE",
                findings,
                "no schema drift detected -- documentation matches production.",
                formatter=lambda f: f"{f.kind}: {f.target} (documented in {f.documented_in}) -- {f.detail}",
            )
        )
    except Exception as e:
        sections.append(f"PLATFORM GOVERNANCE: unavailable ({e})")

    try:
        from agents.fixera.marketplace_intelligence import run_intelligence_sweep

        r = run_intelligence_sweep()
        bottlenecks = r.get("bottlenecks", [])
        sections.append(
            _section(
                "MARKETPLACE INTELLIGENCE",
                bottlenecks,
                "no service bottlenecks detected.",
                formatter=lambda s: (
                    f"{s.service}: {s.open_booking_count} open booking(s) vs {s.eligible_worker_count} eligible worker(s) (ratio {s.ratio:.1f})"
                ),
            )
        )
    except Exception as e:
        sections.append(f"MARKETPLACE INTELLIGENCE: unavailable ({e})")

    try:
        from agents.fixera.customer_support import run_support_queue_sweep

        queue = run_support_queue_sweep()
        breached = [t for t in queue if t.sla_status == "breached"]
        sections.append(
            _section(
                "CUSTOMER SUPPORT",
                breached,
                f"{len(queue)} ticket(s) in queue, none breaching SLA.",
                formatter=lambda t: (
                    f"ticket {t.ticket_id}: {t.priority} priority, open {t.hours_open:.1f}h ({t.sla_status})"
                ),
            )
        )
    except Exception as e:
        sections.append(f"CUSTOMER SUPPORT: unavailable ({e})")

    try:
        from agents.fixera.partner_support import run_partner_support_sweep

        notifications = run_partner_support_sweep()
        sections.append(
            _section(
                "PARTNER SUPPORT",
                notifications,
                "no partner tickets needing team escalation.",
                formatter=lambda n: n.get("subject", str(n)),
            )
        )
    except Exception as e:
        sections.append(f"PARTNER SUPPORT: unavailable ({e})")

    try:
        from agents.fixera.partner_verification import run_verification_sweep

        flags = run_verification_sweep()
        sections.append(
            _section(
                "PARTNER VERIFICATION",
                flags,
                "no partners with missing or stale verification items.",
                formatter=lambda f: f"partner {f.partner_id} ({f.partner_role}): missing {', '.join(f.missing)}",
            )
        )
    except Exception as e:
        sections.append(f"PARTNER VERIFICATION: unavailable ({e})")

    generated_at = datetime.now(UTC)
    summary = (
        f"Fixera Division Daily Briefing (CEO/Lead Agent)\n{generated_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        + "\n\n".join(sections)
    )

    safe_add_knowledge(
        division="fixera",
        agent_id="fixera-ceo-lead-v0.1",
        content=summary,
        source="daily_briefing",
        metadata={"section_count": len(sections), "generated_at": generated_at.isoformat()},
    )

    return {"summary": summary, "sections": sections, "generated_at": generated_at.isoformat()}


TELEGRAM_MESSAGE_LIMIT = 4096  # Telegram's own hard limit on sendMessage text length


def _chunk_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Splits on section boundaries (double newline) first, only
    hard-splitting a single oversized section as a last resort --
    mirrors agents/forex/ceo_lead.py's _chunk_for_telegram() exactly."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for part in text.split("\n\n"):
        candidate = f"{current}\n\n{part}" if current else part
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(part) <= limit:
                current = part
            else:
                for i in range(0, len(part), limit):
                    chunks.append(part[i : i + limit])
                current = ""
    if current:
        chunks.append(current)
    return chunks


def run_daily_briefing_and_notify() -> dict:
    """Live entry point for both the scheduled push and the on-demand
    Telegram trigger -- runs the same run_daily_briefing() either way,
    then delivers it over Telegram (Fixera's own dedicated bot,
    TELEGRAM_FIXERA_BOT_TOKEN -- kept separate from both Forex bots per
    Mohamed's explicit choice, 2026-07-27) in as many messages as
    needed."""
    from agents.fixera._telegram import send_telegram

    briefing = run_daily_briefing()
    chunks = _chunk_for_telegram(briefing["summary"])

    send_results = [send_telegram(chunk, token_env="TELEGRAM_FIXERA_BOT_TOKEN") for chunk in chunks]
    return {
        "briefing": briefing,
        "telegram_messages_sent": sum(1 for r in send_results if r.get("sent")),
        "telegram_messages_total": len(chunks),
        "telegram_results": send_results,
    }
