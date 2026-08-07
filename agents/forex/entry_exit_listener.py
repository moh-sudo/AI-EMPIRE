"""Telegram inbound listener -- Forex Division, Entry & Exit's trade
approval flow.

Deliberately a SEPARATE listener/state file from
agents/forex/telegram_listener.py (CEO/Lead's briefing + chat), even
though both live in the same division -- they poll two different,
deliberately separate bots (TELEGRAM_BOT_TOKEN here vs
TELEGRAM_CEO_BOT_TOKEN there), per Mohamed's explicit request
(2026-07-26): a real trade-execution proposal needing his confirmation
should never get buried under a routine market update in the same
chat. This listener only ever does one thing -- route "APPROVE <id>" /
"REJECT <id>" replies to agents.forex.entry_exit.handle_trade_approval_reply().
No briefing, no free-form chat here; that's CEO/Lead's job in the
other bot.

Security: only reacts to messages from Mohamed's own TELEGRAM_CHAT_ID
-- if anyone else ever messages this bot, their messages are still
consumed (to advance the offset and avoid reprocessing them forever)
but never trigger anything.

Known limitation, not hidden: same as every other listener in this
project -- the last-processed update_id is persisted to a local JSON
file, not Supabase. Harmless here for the same reason as elsewhere
(reprocessing an old update just re-runs the same approval lookup,
which is idempotent since handle_trade_approval_reply() checks
entry["status"] before acting).
"""

import json
import os
from pathlib import Path

import requests

STATE_FILE = Path(__file__).resolve().parent / ".entry_exit_telegram_offset.json"


def _read_last_update_id() -> int | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text()).get("last_update_id")
    except (json.JSONDecodeError, OSError):
        return None


def _save_last_update_id(update_id: int) -> None:
    STATE_FILE.write_text(json.dumps({"last_update_id": update_id}))


def check_for_trade_approvals() -> dict:
    """Polls Telegram's getUpdates once, advances the offset past every
    update seen, and routes any new message from Mohamed's own chat_id
    through handle_trade_approval_reply(). Never raises -- same
    fail-safe pattern as every other listener in this project."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    expected_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not expected_chat_id:
        return {"checked": False, "reason": "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured."}

    last_update_id = _read_last_update_id()
    params = {"timeout": 0}
    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"checked": False, "reason": str(e)}

    if not data.get("ok"):
        return {"checked": False, "reason": data.get("description", "unknown Telegram API error")}

    updates = data.get("result", [])
    if not updates:
        return {"checked": True, "new_messages": 0, "triggered": False}

    from agents.forex._telegram import send_telegram
    from agents.forex.entry_exit import handle_trade_approval_reply

    highest_update_id = last_update_id or 0
    approval_results = []

    for update in updates:
        highest_update_id = max(highest_update_id, update["update_id"])
        msg = update.get("message")
        if not msg:
            continue
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != str(expected_chat_id):
            continue  # not Mohamed -- consume (offset still advances) but never act
        text = (msg.get("text") or "").strip()
        if not text:
            continue

        approval = handle_trade_approval_reply(text)
        if approval is not None:
            approval_results.append(approval)
            send_telegram(approval["reply"], token_env="TELEGRAM_BOT_TOKEN")

    _save_last_update_id(highest_update_id)

    result = {"checked": True, "new_messages": len(updates), "triggered": bool(approval_results)}
    if approval_results:
        result["approval_results"] = approval_results
    return result
