"""Telegram inbound listener -- Forex Division, CEO/Lead's on-demand
briefing trigger + free-form chat Q&A.

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

Routing (added 2026-07-30, mirrors the same day's Fixera change): the
literal word "briefing" still triggers the full run_daily_briefing_and_notify().
Any other message is treated as a free-form question -- answered by a
local Ollama model (shared/models/ollama_client.py, Mohamed's M1
MacBook over LAN) grounded with the same day's briefing summary as
context, so answers reflect real Forex division state rather than a
blind guess.

Known limitation, not hidden: the last-processed update_id is persisted
to a local JSON file, not Supabase -- fine for a single-machine, single-
user setup, but means a fresh machine or a deleted state file would
reprocess whatever's still in Telegram's update buffer once. Harmless
here since the only effect is re-sending a market briefing or
re-answering a question, not a destructive action -- documented rather
than engineered around for a low-stakes case."""

import json
import os
from pathlib import Path

import requests

STATE_FILE = Path(__file__).resolve().parent / ".telegram_offset.json"
DOWNLOADS_DIR = Path(__file__).resolve().parent / ".downloads"


def _read_last_update_id() -> int | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text()).get("last_update_id")
    except (json.JSONDecodeError, OSError):
        return None


def _save_last_update_id(update_id: int) -> None:
    STATE_FILE.write_text(json.dumps({"last_update_id": update_id}))


CHAT_SYSTEM_PROMPT = (
    "You are the Forex CEO/Lead assistant, answering Mohamed's questions "
    "about his forex trading system over Telegram. Use the briefing data "
    "below as your source of truth about current division state -- if the "
    "answer isn't in it, say so plainly rather than guessing. Never "
    "suggest or confirm a real trade -- Entry & Exit's own execution gate "
    "handles that separately, this is informational only. Keep replies "
    "short and direct, suitable for a chat message."
)


def answer_question(text: str) -> dict:
    """Answers a free-form question via the local Ollama model, grounded
    with today's briefing summary as context. Never raises -- mirrors
    the fail-safe pattern of every other external call in this project.
    Pure -- no Telegram side effect -- so it's reusable by other
    interfaces (added 2026-08-01: the local voice session,
    shared/voice/, calls this directly for Forex questions)."""
    from agents.forex.ceo_lead import run_daily_briefing
    from shared.models.ollama_client import chat as ollama_chat

    try:
        briefing = run_daily_briefing()
        context = briefing["summary"]
    except Exception as e:
        context = f"(briefing data unavailable right now: {e})"

    prompt = f"BRIEFING DATA:\n{context}\n\nQUESTION: {text}"
    result = ollama_chat(prompt, system=CHAT_SYSTEM_PROMPT)

    if not result.get("ok"):
        reply_text = f"Couldn't reach the local model to answer that: {result.get('reason')}"
    else:
        reply_text = result["reply"]

    return {"question": text, "ollama_result": result, "reply": reply_text}


def _answer_question(text: str) -> dict:
    """Telegram-specific wrapper around answer_question() -- sends the
    reply via Telegram, matching the original behavior. Kept as a
    separate function so the routing loop below doesn't change."""
    from agents.forex._telegram import send_telegram

    result = answer_question(text)
    send_result = send_telegram(result["reply"], token_env="TELEGRAM_CEO_BOT_TOKEN")
    result["telegram_sent"] = send_result.get("sent", False)
    return result


def check_for_briefing_requests() -> dict:
    """Polls Telegram's getUpdates once, advances the offset past every
    update seen (whether or not it triggers anything). For any new
    message from Mohamed's own chat_id: the literal word "briefing"
    triggers run_daily_briefing_and_notify(); anything else is routed
    to _answer_question() (local Ollama chat, grounded with the
    briefing). Never raises -- a Telegram/network hiccup here shouldn't
    break the polling heartbeat; returns a status dict instead, same
    fail-safe pattern used throughout this division."""
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

    highest_update_id = last_update_id or 0
    briefing_triggered = False
    question_results = []

    for update in updates:
        highest_update_id = max(highest_update_id, update["update_id"])
        msg = update.get("message")
        if not msg:
            continue
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != str(expected_chat_id):
            continue  # not Mohamed -- consume (offset still advances) but never act
        text = (msg.get("text") or "").strip()
        voice = msg.get("voice")
        if not text and voice:
            from shared.telegram_files import download_telegram_file
            from shared.voice.speech_to_text import transcribe

            local_path = download_telegram_file(token, voice["file_id"], ".ogg", DOWNLOADS_DIR)
            if local_path:
                transcription = transcribe(local_path)
                if transcription.get("ok"):
                    text = transcription["text"].strip()
        if text.lower() == "briefing":
            briefing_triggered = True
        elif text:
            question_results.append(_answer_question(text))

    _save_last_update_id(highest_update_id)

    result = {"checked": True, "new_messages": len(updates), "triggered": briefing_triggered or bool(question_results)}
    if briefing_triggered:
        from agents.forex.ceo_lead import run_daily_briefing_and_notify

        result["notify_result"] = run_daily_briefing_and_notify()
    if question_results:
        result["question_results"] = question_results
    return result
