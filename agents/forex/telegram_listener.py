"""Telegram inbound listener -- Forex Division, CEO/Lead's on-demand
briefing trigger.

Per Mohamed's own request (2026-07-26): he wants to text the bot
whenever he wants a fresh market check, not just receive it on a fixed
schedule. This is the "on-demand" half of that -- the scheduled half
is run_daily_briefing_and_notify() called directly by n8n's cron.

Design: n8n has no shell-execution node (confirmed in an earlier
session -- it explicitly recommends HTTP Request instead), so rather
than build a whole new persistent Python process just for this, n8n's
existing Schedule Trigger polls a lightweight HTTP endpoint
(agents/forex/server.py's /check-telegram) every ~30 seconds, which
calls check_for_briefing_requests() below. All of the actual logic
(offset tracking, chat-id restriction, triggering the briefing) lives
here in testable Python, not in n8n workflow logic.

Polls CEO/Lead's OWN dedicated bot (TELEGRAM_CEO_BOT_TOKEN) --
deliberately separate from Entry & Exit's bot (TELEGRAM_BOT_TOKEN),
per Mohamed's explicit request (2026-07-26): routine on-demand market
checks belong in a different chat than real trade-execution alerts.

Security: only reacts to messages from Mohamed's own TELEGRAM_CHAT_ID
-- if anyone else ever messages this bot, their messages are still
consumed (to advance the offset and avoid reprocessing them forever)
but never trigger anything.

Known limitation, not hidden: the last-processed update_id is persisted
to a local JSON file, not Supabase -- fine for a single-machine, single-
user setup, but means a fresh machine or a deleted state file would
reprocess whatever's still in Telegram's update buffer once. Harmless
here since the only effect is re-sending a market briefing, not a
destructive action -- documented rather than engineered around for a
low-stakes case."""

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
    shouldn't break the polling heartbeat; returns a status dict
    instead, same fail-safe pattern used throughout this division."""
    token = os.environ.get("TELEGRAM_CEO_BOT_TOKEN")
    expected_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not expected_chat_id:
        return {"checked": False, "reason": "TELEGRAM_CEO_BOT_TOKEN/TELEGRAM_CHAT_ID not configured."}

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
        from agents.forex.ceo_lead import run_daily_briefing_and_notify

        result = run_daily_briefing_and_notify()
        return {"checked": True, "new_messages": len(updates), "triggered": True, "notify_result": result}

    return {"checked": True, "new_messages": len(updates), "triggered": False}
