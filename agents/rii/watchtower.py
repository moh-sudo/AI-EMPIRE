"""Watchtowers -- Research & Innovation Division.

A watchtower is a topic Mohamed wants continuously monitored -- new
real search results for it get flagged when they first appear, not
re-flagged every check. Uses the same real web_search() as the
Research Agent, no separate search mechanism.

Fully deterministic except the final alert message, which is plain
text (no LLM needed to just list new results) -- unlike research
synthesis, "here are N new results since last check" doesn't need
model interpretation.
"""

from datetime import UTC, datetime


def add_watchtower(topic: str) -> dict:
    from shared.scoped_db import get_scoped_client

    result = get_scoped_client("rii_agent").table("rii_watchtowers").insert({"topic": topic}).execute()
    return result.data[0]


def list_watchtowers() -> list[dict]:
    from shared.scoped_db import get_scoped_client

    result = (
        get_scoped_client("rii_agent")
        .table("rii_watchtowers")
        .select("*")
        .eq("active", True)
        .order("created_at")
        .execute()
    )
    return result.data


def remove_watchtower(topic: str) -> dict:
    """Matches by case-insensitive topic text (not id) -- simpler for
    a Telegram command than requiring the user to know a UUID."""
    from shared.scoped_db import get_scoped_client

    client = get_scoped_client("rii_agent")
    matches = client.table("rii_watchtowers").select("id,topic").eq("active", True).execute().data
    match = next((m for m in matches if m["topic"].strip().lower() == topic.strip().lower()), None)
    if not match:
        return {"ok": False, "reason": f'No active watchtower found for "{topic}".'}

    client.table("rii_watchtowers").update({"active": False}).eq("id", match["id"]).execute()
    return {"ok": True, "removed": match["topic"]}


def check_one_watchtower(watchtower: dict, max_results: int = 5) -> dict:
    """Re-searches a single watchtower's topic, compares against
    seen_urls, and returns any genuinely new results. Never raises."""
    from agents.rii.research import web_search

    search = web_search(watchtower["topic"], max_results=max_results)
    if not search.get("ok"):
        return {"ok": False, "reason": search["reason"]}

    seen = set(watchtower.get("seen_urls") or [])
    new_results = [r for r in search["results"] if r["url"] not in seen]

    from shared.scoped_db import get_scoped_client

    updated_seen = list(seen | {r["url"] for r in search["results"]})
    get_scoped_client("rii_agent").table("rii_watchtowers").update(
        {
            "seen_urls": updated_seen,
            "last_checked_at": datetime.now(UTC).isoformat(),
        }
    ).eq("id", watchtower["id"]).execute()

    return {"ok": True, "new_results": new_results}


def check_all_watchtowers() -> dict:
    """Live entry point -- checks every active watchtower, sends one
    Telegram alert per watchtower with new results (skips ones with
    nothing new, doesn't spam). Each watchtower isolated in its own
    try/except -- one failing can't block the others."""
    from agents.rii._telegram import send_telegram

    watchtowers = list_watchtowers()
    alerts_sent = 0
    checked = 0

    for wt in watchtowers:
        try:
            result = check_one_watchtower(wt)
        except Exception:
            continue
        checked += 1
        if not result.get("ok") or not result.get("new_results"):
            continue

        lines = [f"[Watchtower: {wt['topic']}] {len(result['new_results'])} new result(s):"]
        for r in result["new_results"]:
            lines.append(f"  - {r['title']} ({r['url']})")
        send_telegram("\n".join(lines), token_env="TELEGRAM_RII_BOT_TOKEN")
        alerts_sent += 1

    return {"checked": checked, "alerts_sent": alerts_sent}
