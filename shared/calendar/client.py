"""Google Calendar read-only client -- generic shared infra, not
division-specific.

Uses the same stored refresh token as shared/gmail/client.py (one
combined token covering both gmail.readonly and calendar.readonly,
obtained via agents/personal/gmail_oauth_setup.py's consent flow --
re-run 2026-08-02 to add this scope on top of the original Gmail-only
token) via shared/google_oauth.py.

Scope is read-only (calendar.readonly) by design -- no create/update/
delete method exists here at all, not just unused. Fail-safe like
every other external call in this project: never raises, always
returns a dict with "ok".
"""

from datetime import UTC, datetime


def _get_service():
    from googleapiclient.discovery import build

    from shared.google_oauth import get_credentials

    return build("calendar", "v3", credentials=get_credentials())


def get_upcoming_events(max_results: int = 10) -> dict:
    """Returns today's/upcoming events on the primary calendar, from
    now onward, soonest first."""
    from shared.google_oauth import check_required_env

    missing = check_required_env()
    if missing:
        return {"ok": False, "reason": f"Missing env vars: {', '.join(missing)}"}

    try:
        service = _get_service()
        now = datetime.now(UTC).isoformat()
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as e:
        return {"ok": False, "reason": str(e)}

    events = []
    for item in result.get("items", []):
        start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
        events.append({"summary": item.get("summary", "(no title)"), "start": start})

    return {"ok": True, "events": events}
