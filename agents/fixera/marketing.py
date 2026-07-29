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

import os

import requests

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


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
        return {"posted": False, "reason": "confirmed=True was not passed -- this agent never posts to the real Facebook Page without an explicit human go-ahead."}

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
