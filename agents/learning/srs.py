"""Spaced Repetition (SRS) engine -- Learning Division.

Simplified SM-2 algorithm (the same family Anki uses) -- fully
deterministic, no LLM anywhere in this file, consistent with the
architecture-first pattern: scheduling genuinely doesn't need a model,
so nothing here is stubbed.

Three-level rating (AGAIN/GOOD/EASY) rather than SM-2's original 0-5
quality scale -- simpler to type/say over Telegram or voice, still
captures the core signal (failed / remembered / remembered easily).
"""

from datetime import UTC, datetime
from datetime import date as date_cls

MIN_EASE_FACTOR = 1.3
DEFAULT_EASE_FACTOR = 2.5


def add_card(
    category: str, front: str, back: str, source_type: str = "manual", source_reference: str | None = None
) -> dict:
    from shared.db import get_client

    result = (
        get_client()
        .table("learning_cards")
        .insert(
            {
                "category": category,
                "front": front,
                "back": back,
                "source_type": source_type,
                "source_reference": source_reference,
            }
        )
        .execute()
    )
    return result.data[0]


def get_due_cards(limit: int = 20) -> list[dict]:
    from shared.db import get_client

    today = datetime.now(UTC).date().isoformat()
    result = (
        get_client()
        .table("learning_cards")
        .select("*")
        .eq("active", True)
        .lte("next_review_date", today)
        .order("next_review_date")
        .limit(limit)
        .execute()
    )
    return result.data


def list_categories() -> list[dict]:
    """Returns every category with an active card, plus how many cards
    and how many are due right now -- lets Mohamed see what topics
    exist without having to remember exact spelling/casing he used
    before."""
    from shared.db import get_client

    today = datetime.now(UTC).date().isoformat()
    result = get_client().table("learning_cards").select("category, next_review_date").eq("active", True).execute()

    counts: dict[str, dict] = {}
    for row in result.data:
        cat = row["category"]
        entry = counts.setdefault(cat, {"category": cat, "total": 0, "due": 0})
        entry["total"] += 1
        if row["next_review_date"] <= today:
            entry["due"] += 1

    return sorted(counts.values(), key=lambda c: c["category"].lower())


def get_due_count() -> int:
    from shared.db import get_client

    today = datetime.now(UTC).date().isoformat()
    result = (
        get_client()
        .table("learning_cards")
        .select("id", count="exact")
        .eq("active", True)
        .lte("next_review_date", today)
        .execute()
    )
    return result.count or 0


def _compute_next_state(
    rating: str, repetitions: int, interval_days: int, ease_factor: float
) -> tuple[int, int, float]:
    """Returns (new_repetitions, new_interval_days, new_ease_factor).
    Pure function, unit-testable without touching the DB."""
    rating = rating.upper()

    if rating == "AGAIN":
        return 0, 1, max(MIN_EASE_FACTOR, ease_factor - 0.2)

    new_repetitions = repetitions + 1
    if new_repetitions == 1:
        new_interval = 1
    elif new_repetitions == 2:
        new_interval = 6
    else:
        multiplier = ease_factor * 1.3 if rating == "EASY" else ease_factor
        new_interval = max(1, round(interval_days * multiplier))

    new_ease_factor = min(2.5, ease_factor + 0.15) if rating == "EASY" else ease_factor
    return new_repetitions, new_interval, new_ease_factor


def rate_card(card_id: str, rating: str) -> dict:
    """rating is one of AGAIN, GOOD, EASY (case-insensitive). Returns
    the updated card row, or {"ok": False, "reason": ...} if the
    rating or card_id is invalid."""
    if rating.upper() not in ("AGAIN", "GOOD", "EASY"):
        return {"ok": False, "reason": f"Invalid rating '{rating}' -- must be AGAIN, GOOD, or EASY."}

    from shared.db import get_client

    client = get_client()
    existing = client.table("learning_cards").select("*").eq("id", card_id).execute()
    if not existing.data:
        return {"ok": False, "reason": f"No card found with id {card_id}."}
    card = existing.data[0]

    new_reps, new_interval, new_ef = _compute_next_state(
        rating, card["repetitions"], card["interval_days"], float(card["ease_factor"])
    )
    now = datetime.now(UTC)
    next_review = now.date().toordinal() + new_interval
    next_review_date = date_cls.fromordinal(next_review).isoformat()

    result = (
        client.table("learning_cards")
        .update(
            {
                "repetitions": new_reps,
                "interval_days": new_interval,
                "ease_factor": new_ef,
                "next_review_date": next_review_date,
                "last_reviewed_at": now.isoformat(),
            }
        )
        .eq("id", card_id)
        .execute()
    )

    return {"ok": True, "card": result.data[0]}
