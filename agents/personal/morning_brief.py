"""Morning Executive Brief -- Personal Division.

Aggregates across divisions by design (unlike every other cross-
division boundary in this project, which deliberately duplicates
rather than imports) -- Mohamed explicitly asked for a Fixera+Forex
snapshot inside this brief so he doesn't have to check 3 chats
separately. Calls each division's own public run_daily_briefing()
entry point directly (not their internal _telegram/_memory_helpers,
which stay division-private) -- the closest honest implementation of
the "Master Orchestrator" concept from the original governance docs
until a real orchestrator module exists.

Condensing Fixera/Forex sections into one-liners is fully deterministic
-- each section already starts with a "TITLE (count): ..." or "TITLE:
message" first line (see agents/fixera/ceo_lead.py's _section()
helper), so just taking each section's first line needs no model at
all. Consistent with the architecture-first pattern: this genuinely
doesn't need an LLM, so nothing here is stubbed for that reason.

Email and Calendar are both real, added 2026-08-02 --
shared/gmail/client.py and shared/calendar/client.py, genuine Google
Cloud OAuth integrations (read-only scopes, Mohamed's own Google Cloud
project ai-empire-personal, one combined refresh token covering both,
obtained via agents/personal/gmail_oauth_setup.py's interactive
consent flow -- run once for Gmail, re-run the same day to add
Calendar on top). Both live-verified against his real account (Gmail:
201 unread at first test; Calendar: connects successfully, correctly
returns an empty list since he has no upcoming events, not an error).
Contacts explicitly NOT included yet -- Mohamed asked to leave that
for later.

Fetched concurrently, not sequentially (added 2026-08-02, same day as
Calendar) -- live-verified the sequential version took ~94s end to
end, mostly Fixera's own briefing (~36s, unrelated to this file --
it queries 8 live agents/the connector) and Forex's (~19s), not
anything new added today. Running all 5 sources in a thread pool cuts
real wall-clock time to roughly the slowest single source instead of
the sum of all five -- each source is independent I/O (a DB query or
an external API call), so this is safe, not a change in what data is
fetched or how any single source works.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime


def _condense_sections(sections: list[str]) -> list[str]:
    return [s.split("\n")[0] for s in sections]


def _fetch_habits() -> str:
    try:
        from agents.personal.habit_tracker import get_today_status

        status = get_today_status()
        if status["total_count"] == 0:
            return "HABITS: none set up yet."
        habit_lines = [f"  - {h['name']}: {'done' if h['done'] else 'not yet'}" for h in status["habits"]]
        return f"HABITS ({status['completed_count']}/{status['total_count']} done):\n" + "\n".join(habit_lines)
    except Exception as e:
        return f"HABITS: unavailable ({e})"


def _fetch_calendar() -> str:
    try:
        from shared.calendar.client import get_upcoming_events

        calendar = get_upcoming_events()
        if not calendar.get("ok"):
            return f"CALENDAR: unavailable ({calendar['reason']})"
        events = calendar.get("events", [])
        if not events:
            return "CALENDAR: no upcoming events."
        event_lines = [f"  - {ev['summary']} ({ev['start']})" for ev in events]
        return f"CALENDAR ({len(events)} upcoming):\n" + "\n".join(event_lines)
    except Exception as e:
        return f"CALENDAR: unavailable ({e})"


def _fetch_email() -> str:
    try:
        from shared.gmail.client import get_unread_summary

        email = get_unread_summary()
        if not email.get("ok"):
            return f"EMAIL: unavailable ({email['reason']})"
        preview_lines = [f"  - {p['subject']} (from {p['from']})" for p in email["previews"]]
        return f"EMAIL ({email['unread_count']} unread):\n" + "\n".join(preview_lines)
    except Exception as e:
        return f"EMAIL: unavailable ({e})"


def _fetch_fixera() -> str:
    try:
        from agents.fixera.ceo_lead import run_daily_briefing as fixera_briefing

        result = fixera_briefing()
        return "FIXERA:\n" + "\n".join(f"  - {line}" for line in _condense_sections(result["sections"]))
    except Exception as e:
        return f"FIXERA: unavailable ({e})"


def _fetch_forex() -> str:
    try:
        from agents.forex.ceo_lead import run_daily_briefing as forex_briefing

        result = forex_briefing()
        return "FOREX:\n" + "\n".join(f"  - {line}" for line in _condense_sections(result["sections"]))
    except Exception as e:
        return f"FOREX: unavailable ({e})"


def build_morning_brief() -> dict:
    """Live entry point -- pulls today's habit status, calendar events,
    email, and a condensed Fixera+Forex snapshot into one brief, all
    fetched concurrently. Each source is isolated in its own
    try/except (inside its _fetch_* function) -- one source failing
    can't take down the whole brief, and one source being slow can't
    block the others from finishing."""
    generated_at = datetime.now(UTC)
    fetchers = [_fetch_habits, _fetch_calendar, _fetch_email, _fetch_fixera, _fetch_forex]

    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        sections = list(executor.map(lambda fn: fn(), fetchers))

    summary = f"Morning Executive Brief\n{generated_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n" + "\n\n".join(sections)
    return {"summary": summary, "sections": sections, "generated_at": generated_at.isoformat()}
