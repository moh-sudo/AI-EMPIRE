"""Habit Tracker -- Personal Division.

Real, working data layer against AI_EMPIRE's own Supabase (not
Fixera's -- this is Mohamed's own personal data, no connector/scoping
needed, full read/write access via shared.db.get_client()). Two
tables: personal_habits (the habit list) and personal_habit_completions
(one row per habit per day actually done) -- see
infrastructure/database/migrations/0004_personal_division_habits.sql.

Deliberately no LLM anywhere in this module -- habit tracking is
fully deterministic (add a habit, mark a date done, check what's done
today), consistent with the architecture-first pattern used everywhere
in this project: nothing here needs a model, so nothing here is
stubbed.
"""

from datetime import UTC, datetime
from datetime import date as date_cls


def add_habit(name: str) -> dict:
    from shared.db import get_client

    result = get_client().table("personal_habits").insert({"name": name}).execute()
    return result.data[0]


def list_active_habits() -> list[dict]:
    from shared.db import get_client

    result = get_client().table("personal_habits").select("*").eq("active", True).order("created_at").execute()
    return result.data


def deactivate_habit(habit_id: str) -> dict:
    from shared.db import get_client

    result = get_client().table("personal_habits").update({"active": False}).eq("id", habit_id).execute()
    return result.data[0] if result.data else {}


def mark_habit_done(habit_id: str, on_date: date_cls | None = None) -> dict:
    """Idempotent -- marking the same habit done twice on the same day
    is a no-op, not an error (personal_habit_completions has a real
    UNIQUE(habit_id, completed_date) constraint, not just app-side
    logic)."""
    from postgrest.exceptions import APIError

    from shared.db import get_client

    target_date = (on_date or datetime.now(UTC).date()).isoformat()
    try:
        result = (
            get_client()
            .table("personal_habit_completions")
            .insert({"habit_id": habit_id, "completed_date": target_date})
            .execute()
        )
        return {"marked": True, "already_done": False, "row": result.data[0]}
    except APIError as e:
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            return {"marked": True, "already_done": True}
        raise


def get_today_status(on_date: date_cls | None = None) -> dict:
    """Returns every active habit with whether it's done for the given
    date (defaults to today, UTC)."""
    from shared.db import get_client

    target_date = (on_date or datetime.now(UTC).date()).isoformat()
    habits = list_active_habits()

    completions = (
        get_client().table("personal_habit_completions").select("habit_id").eq("completed_date", target_date).execute()
    )
    done_ids = {row["habit_id"] for row in completions.data}

    habit_status = [{"id": h["id"], "name": h["name"], "done": h["id"] in done_ids} for h in habits]
    return {
        "date": target_date,
        "habits": habit_status,
        "completed_count": sum(1 for h in habit_status if h["done"]),
        "total_count": len(habit_status),
    }


def format_daily_checkin_message() -> str:
    status = get_today_status()
    if status["total_count"] == 0:
        return "[Habits] No active habits set up yet. Add one to get started."

    lines = [f"[Habits] {status['date']} -- {status['completed_count']}/{status['total_count']} done"]
    for i, h in enumerate(status["habits"], start=1):
        mark = "x" if h["done"] else " "
        lines.append(f"  [{mark}] {i}. {h['name']}")
    lines.append('\nReply "DONE <number or name>" to check one off.')
    return "\n".join(lines)


def resolve_habit_reference(reference: str) -> dict | None:
    """Matches a Telegram/voice reply against today's active habits --
    by position number (matches the numbered list in
    format_daily_checkin_message()) or by case-insensitive name
    substring. Returns None if nothing matches, rather than guessing."""
    status = get_today_status()
    reference = reference.strip()

    if reference.isdigit():
        idx = int(reference) - 1
        if 0 <= idx < len(status["habits"]):
            return status["habits"][idx]
        return None

    reference_lower = reference.lower()
    matches = [h for h in status["habits"] if reference_lower in h["name"].lower()]
    return matches[0] if len(matches) == 1 else None
