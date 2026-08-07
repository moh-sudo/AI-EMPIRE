"""Marketing Agent v0.1 -- Fixera Division.

Publishes content to Fixera's Meta (Facebook Page) presence. Per
Mohamed's explicit design (2026-07-27/28): a multi-stage pipeline --
this agent prepares content, the CEO/Lead agent reviews it for quality
before it reaches Mohamed, and Mohamed gives the final go-ahead before
anything actually posts. AI-generated content and the CEO's rules-
based quality check both depend on real vision/language-model judgment
(catching whether generated video/images look genuinely realistic,
not just mechanically valid), which is blocked on OpenAI billing not
being set up yet (2026-07-27).

This first version deliberately builds and verifies the ONE piece that
isn't blocked by that dependency: the actual Meta Graph API posting
mechanism. Content generation and the CEO quality gate are deferred,
not skipped -- see shared/prompts/fixera_marketing_v1.json boundaries
for the full intended pipeline.

Instagram publishing is not yet available -- the Instagram Business
Account link (fixera_homeservices -> the Fixeraservices Facebook Page)
hit a real obstacle during setup (Meta's classic Page-Instagram link
never completed even though Meta's own "Linked accounts" UI confirmed
the connection) and needs proper research into Meta's current API
requirements before retrying, rather than more UI trial-and-error.
Facebook Page posting is fully working and live-verified.

Hard rule enforced in code, matching every other real-world-action
agent in this system (Entry & Exit's confirmed=True gate): publish_post()
refuses to post anything without an explicit confirmed=True from the
caller -- never auto-posts to Fixera's real, public Facebook Page.
"""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

import requests

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

PENDING_POSTS_FILE = Path(__file__).resolve().parent / ".marketing_pending_posts.json"
_APPROVAL_PATTERN = re.compile(r"^(APPROVE|REJECT)\s+(\S+)$", re.IGNORECASE)


def post_text_to_facebook_page(message: str) -> dict:
    """The actual Graph API call -- POST /{page-id}/feed. Never call
    this directly from outside publish_post(); it has no confirmation
    gate of its own, that's publish_post()'s job. Returns {"posted":
    False, "reason": ...} on any failure rather than raising, matching
    the fail-safe pattern used throughout this codebase."""
    token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    page_id = os.environ.get("META_PAGE_ID")
    if not token or not page_id:
        return {"posted": False, "reason": "META_PAGE_ACCESS_TOKEN/META_PAGE_ID not configured in .env yet."}

    try:
        resp = requests.post(
            f"{GRAPH_API_BASE}/{page_id}/feed",
            data={"message": message, "access_token": token},
            timeout=15,
        )
        data = resp.json()
    except requests.RequestException as e:
        return {"posted": False, "reason": str(e)}

    if resp.status_code == 200 and "id" in data:
        return {"posted": True, "post_id": data["id"]}
    return {"posted": False, "reason": data.get("error", {}).get("message", str(data)), "raw_error": data}


def publish_post(message: str, confirmed: bool) -> dict:
    """The only function that actually publishes to Fixera's real,
    public Facebook Page. Hard-gated: refuses unless confirmed=True is
    passed explicitly by the caller -- Mohamed's own go-ahead, never
    inferred from content having been "generated" or "reviewed." There
    is no code path from content-ready straight to published without
    this explicit flag, same principle as Entry & Exit's execute_order().
    Every attempt (successful or not) is logged to memory_experience so
    there's a real record of what was published and when."""
    if not confirmed:
        return {
            "posted": False,
            "reason": "confirmed=True was not passed -- this agent never posts to the real Facebook Page without an explicit human go-ahead.",
        }

    result = post_text_to_facebook_page(message)

    from agents.fixera._memory_helpers import safe_add_experience

    safe_add_experience(
        division="fixera",
        agent_id="fixera-marketing-v0.1",
        event_type="facebook_post_published" if result.get("posted") else "facebook_post_failed",
        context=message,
        outcome="posted" if result.get("posted") else "failed",
        metadata={k: v for k, v in result.items() if k != "raw_error"},
    )
    return result


# ---------------------------------------------------------------------------
# Approval-flow plumbing (added 2026-08-01). Lets Mohamed approve/reject a
# draft from his phone via Telegram, without needing to be at this machine.
# Deliberately NOT content generation -- that's still deferred per his
# architecture-first instruction (2026-07-31); a draft's message text today
# comes from whoever calls stage_post() (a Claude Code session, on his
# behalf), not from the agent generating it itself. Once real content
# generation exists, it would call stage_post() the same way this does.
# ---------------------------------------------------------------------------


def _read_pending() -> dict:
    if not PENDING_POSTS_FILE.exists():
        return {}
    try:
        return json.loads(PENDING_POSTS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_pending(data: dict) -> None:
    PENDING_POSTS_FILE.write_text(json.dumps(data, indent=2))


def stage_post(message: str) -> dict:
    """Stages a draft and sends it to Mohamed on Telegram for approval.
    Does NOT publish anything -- only publish_post(confirmed=True),
    triggered by his own "APPROVE <id>" reply via handle_approval_reply()
    below, can do that."""
    from agents.fixera._telegram import send_telegram

    pending = _read_pending()
    next_id = str(max([int(k) for k in pending.keys()] + [0]) + 1)
    pending[next_id] = {
        "message": message,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
    }
    _save_pending(pending)

    telegram_text = (
        f"[Marketing] Draft post #{next_id} awaiting your approval:\n\n"
        f"{message}\n\n"
        f'Reply "APPROVE {next_id}" to publish, or "REJECT {next_id}" to discard.'
    )
    send_result = send_telegram(telegram_text, token_env="TELEGRAM_FIXERA_BOT_TOKEN")
    return {"draft_id": next_id, "telegram_sent": send_result.get("sent", False)}


def handle_approval_reply(text: str) -> dict | None:
    """If text matches "APPROVE <id>" or "REJECT <id>" (case-insensitive),
    acts on the matching pending draft and returns a result dict with a
    "reply" message for telegram_listener.py to send back. Returns None
    for any other text, signalling "not an approval command, treat this
    as a normal question instead" to the caller."""
    match = _APPROVAL_PATTERN.match(text.strip())
    if not match:
        return None

    action, draft_id = match.group(1).upper(), match.group(2)
    pending = _read_pending()
    draft = pending.get(draft_id)
    if not draft:
        return {"handled": True, "reply": f"No pending draft #{draft_id} found."}
    if draft["status"] != "pending":
        return {"handled": True, "reply": f"Draft #{draft_id} was already {draft['status']}."}

    if action == "REJECT":
        draft["status"] = "rejected"
        _save_pending(pending)
        return {"handled": True, "reply": f"Draft #{draft_id} rejected -- not published."}

    result = publish_post(draft["message"], confirmed=True)
    draft["status"] = "approved" if result.get("posted") else "approve_failed"
    _save_pending(pending)
    if result.get("posted"):
        return {"handled": True, "reply": f"Draft #{draft_id} published! Post ID: {result.get('post_id')}"}
    return {"handled": True, "reply": f"Draft #{draft_id} approved but publishing failed: {result.get('reason')}"}
