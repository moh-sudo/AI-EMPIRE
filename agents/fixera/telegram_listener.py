"""Telegram inbound listener -- Fixera Division, CEO/Lead's on-demand
briefing trigger.

Mirrors agents/forex/telegram_listener.py exactly (same reasoning: no
persistent Python process, n8n polls a lightweight HTTP endpoint every
~30s since this n8n install has no shell-execution node). Kept as a
separate copy rather than a cross-import, same division-separation
principle as _telegram.py.

Polls Fixera's OWN dedicated bot (TELEGRAM_FIXERA_BOT_TOKEN) --
deliberately separate from both Forex bots, per Mohamed's explicit
choice (2026-07-27).

Security: only reacts to messages from Mohamed's own TELEGRAM_CHAT_ID
-- if anyone else ever messages this bot, their messages are still
consumed (to advance the offset and avoid reprocessing them forever)
but never trigger anything.

Known limitation, not hidden: the last-processed update_id is persisted
to a local JSON file, not Supabase -- fine for a single-machine, single-
user setup. Harmless here since the only effect of ever reprocessing an
old message is re-sending a business briefing, not a destructive action.
"""

import json
import os
from pathlib import Path
from typing import Optional

import requests

STATE_FILE = Path(__file__).resolve().parent / ".telegram_offset.json"


def _read_last_update_id() -> Optional[int]:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text()).get("last_update_id")
    except (json.JSONDecodeError, OSError):
        return None


def _save_last_update_id(update_id: int) -> None:
    STATE_FILE.write_text(json.dumps({"last_update_id": update_id}))


def check_for_briefing_requests() -> dict:
    """Polls Telegram's getUpdates once, advances the offset past every
    update seen (whether or not it triggers anything), and triggers
    run_daily_briefing_and_notify() for any new message from Mohamed's
    own chat_id. Never raises -- a Telegram/network hiccup here
    shouldn't break the polling heartbeat."""
    token = os.environ.get("TELEGRAM_FIXERA_BOT_TOKEN")
    expected_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not expected_chat_id:
        return {"checked": False, "reason": "TELEGRAM_FIXERA_BOT_TOKEN/TELEGRAM_CHAT_ID not configured."}

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

    triggered = False
    highest_update_id = last_update_id or 0

    for update in updates:
        highest_update_id = max(highest_update_id, update["update_id"])
        msg = update.get("message")
        if not msg:
            continue
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != str(expected_chat_id):
            continue  # not Mohamed -- consume (offset still advances) but never act
        triggered = True

    _save_last_update_id(highest_update_id)

    if triggered:
        from agents.fixera.ceo_lead import run_daily_briefing_and_notify

        result = run_daily_briefing_and_notify()
        return {"checked": True, "new_messages": len(updates), "triggered": True, "notify_result": result}

    return {"checked": True, "new_messages": len(updates), "triggered": False}
