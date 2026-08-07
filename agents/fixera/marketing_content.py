"""Marketing content generation + quality review -- Fixera Division.

Architecture-only per Mohamed's explicit instruction (2026-07-31): the
real LLM connection is deliberately NOT wired here yet -- he'll
connect it once he has bigger hardware than his current M1 MacBook
(8GB unified memory, already confirmed too small for vision-capable
models at usable speed, and a clear step down from GPT-4-class text
reasoning). Every function below is fully real, working plumbing --
state, gating, logging, Telegram wiring -- with the actual model calls
isolated into exactly two functions (_call_content_model,
_call_vision_review_model) that return an honest "not connected yet"
result today instead of silently faking content. Wiring a real model
later means implementing those two functions; nothing else in this
pipeline needs to change.

Full intended pipeline (Mohamed's own design, 2026-07-27/28): generate
draft -> CEO/Lead quality review (catches what "a human being can
spot," e.g. whether AI-generated images/video look genuinely
realistic, not cartoonish) -> only once review passes does Mohamed get
notified on Telegram -> his explicit reply is what actually calls
publish_post(confirmed=True). generate_and_review_draft() is the new
orchestration entry point for that whole chain -- it calls the
already-built, already-verified stage_post() at the very end (see
marketing.py, 2026-08-01). stage_post()/handle_approval_reply()/
publish_post() are untouched by this file.

Deliberately fails closed: with both model calls stubbed, this can
never reach stage_post() today -- proven by test, not just asserted --
so there's no path for placeholder/stub content to accidentally reach
Mohamed's real Facebook Page.
"""


def _call_content_model(topic: str) -> dict:
    """THE stub for draft generation. Realistic to wire to Ollama for
    plain text once Mohamed's ready (already proven working for the
    Fixera/Forex chat features) -- deliberately left disconnected for
    now so this pipeline's first version stays fully predictable while
    its plumbing gets tested, per his explicit instruction."""
    return {
        "ok": False,
        "reason": "Content generation model not connected yet -- architecture-only per Mohamed's 2026-07-31 instruction.",
    }


def _call_vision_review_model(draft_text: str, media_paths: list[str] | None = None) -> dict:
    """THE stub for the CEO/Lead's quality-review judgment. Real
    image/video realism-checking needs a vision-capable model --
    genuinely impractical at usable speed on the current 8GB M1 (see
    CONTEXT.md, 2026-07-31 RAM/GPT-4 discussion) -- so this stays
    disconnected until better hardware, independent of the text-model
    decision above."""
    return {
        "ok": False,
        "reason": "Quality-review model not connected yet -- architecture-only per Mohamed's 2026-07-31 instruction.",
    }


def generate_and_review_draft(topic: str, media_paths: list[str] | None = None) -> dict:
    """Runs the full generate -> review chain for a given topic. Every
    attempt is logged to memory_experience, successful or not -- a real
    audit trail of what content pipeline runs actually happened, same
    principle as every other real-world-action agent in this project.
    Today, since both model calls are stubbed, this always stops before
    stage_post() -- intentional, not a bug: it proves the pipeline's
    shape and gating without ever risking stub/placeholder text
    reaching Mohamed's real Page. Once a real model is wired into
    _call_content_model (and, separately, _call_vision_review_model),
    this same function starts working end to end with zero changes
    needed here."""
    from agents.fixera._memory_helpers import safe_add_experience

    def _log(event_type: str, outcome: str, metadata: dict) -> None:
        safe_add_experience(
            division="fixera",
            agent_id="fixera-marketing-v0.1",
            event_type=event_type,
            context=topic,
            outcome=outcome,
            metadata=metadata,
        )

    generation = _call_content_model(topic)
    _log("content_generation_attempted", "ok" if generation.get("ok") else "blocked", generation)
    if not generation.get("ok"):
        return {"staged": False, "stage": "generation", "reason": generation["reason"]}

    review = _call_vision_review_model(generation["draft_text"], media_paths)
    _log("content_review_attempted", "ok" if review.get("ok") else "blocked", review)
    if not review.get("ok"):
        return {"staged": False, "stage": "review", "reason": review["reason"]}
    if not review.get("passed"):
        reason = review.get("reason", "quality review did not pass")
        _log("content_review_rejected", "rejected", {"reason": reason})
        return {"staged": False, "stage": "review", "reason": reason}

    from agents.fixera.marketing import stage_post

    stage_result = stage_post(generation["draft_text"])
    _log("content_staged", "staged", stage_result)
    return {"staged": True, "stage": "done", **stage_result}
