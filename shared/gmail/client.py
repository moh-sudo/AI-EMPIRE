"""Gmail read-only client -- generic shared infra, not division-specific.

Uses a stored refresh token (obtained once via
agents/personal/gmail_oauth_setup.py's interactive consent flow, never
re-run automatically) to get fresh access tokens on every call --
this is what makes it work unattended, no browser interaction needed
after the one-time setup.

Scope is read-only (gmail.readonly) by design -- this client can only
ever read; there is no send/modify/delete method here at all, not just
an unused one. Least privilege, matching every other real-world
integration in this project.

Fail-safe like every other external call in this project: never
raises, always returns a dict with "ok".
"""


def _get_service():
    from googleapiclient.discovery import build

    from shared.google_oauth import get_credentials

    return build("gmail", "v1", credentials=get_credentials())


def get_unread_summary(max_results: int = 5) -> dict:
    """Returns an approximate unread count (Gmail's own
    resultSizeEstimate -- exact counting would need paging through
    every result, overkill for a morning summary) plus subject/sender
    for the most recent few unread messages."""
    from shared.google_oauth import check_required_env

    missing = check_required_env()
    if missing:
        return {"ok": False, "reason": f"Missing env vars: {', '.join(missing)}"}

    try:
        service = _get_service()
        result = service.users().messages().list(userId="me", q="is:unread", maxResults=max_results).execute()
    except Exception as e:
        return {"ok": False, "reason": str(e)}

    unread_count = result.get("resultSizeEstimate", 0)
    message_ids = [m["id"] for m in result.get("messages", [])]

    previews = []
    try:
        for msg_id in message_ids:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="metadata", metadataHeaders=["From", "Subject"])
                .execute()
            )
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            previews.append({"from": headers.get("From", "?"), "subject": headers.get("Subject", "(no subject)")})
    except Exception as e:
        return {"ok": True, "unread_count": unread_count, "previews": [], "preview_error": str(e)}

    return {"ok": True, "unread_count": unread_count, "previews": previews}
