"""Bug Detection & Debugging -- Audit & Verification Division.

Implements governance/policies/self_healing_governance.md v0.1:
detects recurring failures (real data from memory_experience, where
every agent in this project already logs its own failures via
safe_add_experience), diagnoses root cause with real Ollama judgment
(Mohamed's explicit choice, 2026-08-03 -- diagnosis is closer to the
research/QA-judgment tasks already proven to work well), but
DELIBERATELY does not draft actual code fixes -- Mohamed's own
explicit choice given the real, well-documented gap between small
general chat models and code-generation quality. Every finding is
logged as a real pending proposal (audit_bug_proposals) and sent to
Mohamed via Telegram for his review -- Rule 8 (risk-based approval):
v0.1 treats everything as needing his explicit approval, since no
risk-classifier exists yet to safely support an auto-deploy tier.

Rule 3 (Root Cause Before Fix) and Rule 6 (Explain Every Change) are
both enforced structurally here -- diagnose_root_cause() always runs
before anything is proposed, and the Telegram message always includes
the real symptom + real diagnosis, never a bare "something's wrong."
"""

from datetime import UTC, datetime, timedelta

MIN_OCCURRENCES = 3  # fewer than this in the window isn't a pattern, just noise
WINDOW_HOURS = 24


def detect_recurring_failures() -> list[dict]:
    """Real query against memory_experience -- every agent in this
    project already logs its own failures there via
    safe_add_experience(outcome='failed'/'blocked'/...). Groups by
    (division, agent_id, event_type) and flags combinations that
    recurred at least MIN_OCCURRENCES times in the last WINDOW_HOURS."""
    from shared.db import get_client

    since = (datetime.now(UTC) - timedelta(hours=WINDOW_HOURS)).isoformat()
    result = (
        get_client()
        .table("memory_experience")
        .select("division,agent_id,event_type,outcome,context,metadata,created_at")
        .in_("outcome", ["failed", "blocked", "rejected", "approve_failed"])
        .gte("created_at", since)
        .execute()
    )

    clusters: dict[tuple, list[dict]] = {}
    for row in result.data:
        key = (row["division"], row["agent_id"], row["event_type"])
        clusters.setdefault(key, []).append(row)

    return [
        {
            "division": division,
            "agent_id": agent_id,
            "event_type": event_type,
            "occurrences": len(rows),
            "sample": rows[:5],
        }
        for (division, agent_id, event_type), rows in clusters.items()
        if len(rows) >= MIN_OCCURRENCES
    ]


DIAGNOSIS_SYSTEM_PROMPT = (
    "You are a debugging assistant reviewing a recurring failure pattern in an "
    "AI agent system. You are given the division, agent, event type, how many "
    "times it recurred, and sample failure records (context + error metadata). "
    "Identify the most likely root cause based ONLY on the evidence given -- if "
    "the evidence isn't enough to be confident, say so plainly rather than "
    "guessing. Do not propose a code fix -- root cause analysis only. Keep it "
    "clear and concise, suitable for a chat message."
)


def diagnose_root_cause(cluster: dict) -> dict:
    """Real Ollama call -- diagnosis only, never a fix (that stays
    stubbed, see propose_fix())."""
    from shared.models.ollama_client import chat as ollama_chat

    prompt = (
        f"Division: {cluster['division']}\nAgent: {cluster['agent_id']}\n"
        f"Event type: {cluster['event_type']}\nOccurrences in last {WINDOW_HOURS}h: {cluster['occurrences']}\n\n"
        f"Sample failure records:\n{cluster['sample']}"
    )
    return ollama_chat(prompt, system=DIAGNOSIS_SYSTEM_PROMPT)


def propose_fix(diagnosis: str) -> dict:
    """THE stub. Drafting an actual code fix needs real code-generation
    quality that the current 3B Ollama model doesn't reliably have --
    Mohamed's explicit, informed choice (2026-08-03), not an oversight.
    Root cause diagnosis above stays real; only this step is
    disconnected."""
    return {
        "ok": False,
        "reason": "Fix drafting not connected yet -- root cause diagnosis is real, but drafting an actual code change needs a stronger model than the current 3B Ollama setup can reliably provide. Please review the diagnosis and write the fix yourself for now.",
    }


def _save_proposal(cluster: dict, diagnosis_text: str, fix_available: bool) -> dict:
    from shared.db import get_client

    status = "pending" if fix_available else "fix_unavailable"
    result = (
        get_client()
        .table("audit_bug_proposals")
        .insert(
            {
                "agent_id": cluster["agent_id"],
                "division": cluster["division"],
                "symptom": f"{cluster['event_type']} recurred {cluster['occurrences']}x in {WINDOW_HOURS}h",
                "root_cause": diagnosis_text,
                "proposed_fix": None,
                "status": status,
            }
        )
        .execute()
    )
    return result.data[0]


def run_bug_detection_sweep(notify: bool = True) -> dict:
    """Live entry point: detect -> diagnose (real) -> QA review the
    diagnosis (Two-Agent Rule: this agent is never sole
    developer+reviewer) -> propose fix (stubbed) -> save as a pending
    proposal -> notify Mohamed via Telegram with the full symptom +
    diagnosis + QA verdict (Rule 6: explain every change, even one
    that can't be auto-fixed yet). Each cluster isolated in its own
    try/except."""
    from agents.audit.qa import review_output

    clusters = detect_recurring_failures()
    proposals = []

    for cluster in clusters:
        try:
            diagnosis = diagnose_root_cause(cluster)
            diagnosis_text = (
                diagnosis["reply"] if diagnosis.get("ok") else f"(diagnosis unavailable: {diagnosis.get('reason')})"
            )

            qa_result = review_output(context=str(cluster["sample"]), output=diagnosis_text)

            fix = propose_fix(diagnosis_text)
            proposal = _save_proposal(cluster, diagnosis_text, fix.get("ok", False))
            proposals.append({**proposal, "qa": qa_result})

            if notify:
                from agents.audit._telegram import send_telegram

                qa_line = "PASS -- no concerns" if qa_result["passed"] else f"FLAGGED -- {qa_result['concerns']}"
                message = (
                    f"[Bug Detected] {cluster['division']}/{cluster['agent_id']}\n"
                    f"Symptom: {cluster['event_type']} recurred {cluster['occurrences']}x in {WINDOW_HOURS}h\n\n"
                    f"Root cause (Ollama diagnosis):\n{diagnosis_text}\n\n"
                    f"QA review: {qa_line}\n\n"
                    f"Fix: {fix['reason']}\n\n"
                    f'Reply "PROPOSAL {proposal["id"]} ACK" to confirm you\'ve seen this.'
                )
                send_telegram(message, token_env="TELEGRAM_AUDIT_BOT_TOKEN")
        except Exception as e:
            proposals.append({"error": str(e), "cluster": cluster})

    return {"clusters_found": len(clusters), "proposals": proposals}
