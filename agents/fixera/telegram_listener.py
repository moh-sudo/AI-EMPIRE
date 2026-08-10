"""Telegram inbound listener -- Fixera Division, CEO/Lead's on-demand
briefing trigger + free-form chat Q&A.

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

Routing: the literal word "briefing" still triggers the full 8-agent
daily briefing (run_daily_briefing_and_notify(), unchanged). "APPROVE
<id>" / "REJECT <id>" (added 2026-08-01) act on a pending Marketing
Agent draft via agents.fixera.marketing.handle_approval_reply(). "GENERATE
<topic>" (added 2026-08-01) runs the content-generation pipeline
(agents.fixera.marketing_content.generate_and_review_draft()) -- today
this always replies with an honest "not connected yet" since the real
model isn't wired in (architecture-only per Mohamed's 2026-07-31
instruction), but the remote trigger itself is real and ready for when
it is. All three of these are checked before the chat fallback, in
that order, so a command is never accidentally answered by the LLM
instead of actually being acted on. Any other message is treated as a
free-form question -- answered by a local Ollama model
(shared/models/ollama_client.py, currently Mohamed's M1 MacBook over
LAN) grounded with the same day's briefing summary as context, so
answers reflect real Fixera data rather than a blind guess.

Known limitation, not hidden: the last-processed update_id is persisted
to a local JSON file, not Supabase -- fine for a single-machine, single-
user setup. Harmless here since the only effect of ever reprocessing an
old message is re-sending a business briefing or re-answering a
question, not a destructive action.
"""

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
    "You are the Fixera CEO/Lead assistant, answering Mohamed's questions "
    "about his Fixera home-services platform over Telegram. Use the "
    "briefing data below as your source of truth about current business "
    "state -- if the answer isn't in it, say so plainly rather than "
    "guessing. Keep replies short and direct, suitable for a chat message."
)


def answer_question(text: str) -> dict:
    """Answers a free-form question via the local Ollama model, grounded
    with today's briefing summary as context. Never raises -- mirrors
    the fail-safe pattern of every other external call in this project.
    Pure -- no Telegram side effect -- so it's reusable by other
    interfaces (added 2026-08-01: the local voice session,
    shared/voice/, calls this directly for Fixera questions)."""
    from agents.fixera.ceo_lead import run_daily_briefing
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
    from agents.fixera._telegram import send_telegram

    result = answer_question(text)
    send_result = send_telegram(result["reply"], token_env="TELEGRAM_FIXERA_BOT_TOKEN")
    result["telegram_sent"] = send_result.get("sent", False)
    return result


def check_for_briefing_requests() -> dict:
    """Polls Telegram's getUpdates once, advances the offset past every
    update seen (whether or not it triggers anything). For any new
    message from Mohamed's own chat_id: the literal word "briefing"
    triggers run_daily_briefing_and_notify(); anything else is routed
    to _answer_question() (local Ollama chat, grounded with the
    briefing). Never raises -- a Telegram/network hiccup here shouldn't
    break the polling heartbeat."""
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

    highest_update_id = last_update_id or 0
    briefing_triggered = False
    question_results = []
    approval_results = []
    generation_results = []

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
            continue

        from agents.fixera._telegram import send_telegram
        from agents.fixera.marketing import handle_approval_reply

        approval = handle_approval_reply(text) if text else None
        if approval is not None:
            approval_results.append(approval)
            send_telegram(approval["reply"], token_env="TELEGRAM_FIXERA_BOT_TOKEN")
        elif text.upper().startswith("GENERATE "):
            from agents.fixera.marketing_content import generate_and_review_draft

            topic = text[len("GENERATE ") :].strip()
            gen_result = generate_and_review_draft(topic)
            generation_results.append(gen_result)
            if gen_result.get("staged"):
                reply = "Draft generated and staged for approval (see previous message)."
            else:
                reply = f'Couldn\'t generate a draft for "{topic}": {gen_result.get("reason")}'
            send_telegram(reply, token_env="TELEGRAM_FIXERA_BOT_TOKEN")
        elif text:
            question_results.append(_answer_question(text))

    _save_last_update_id(highest_update_id)

    result = {
        "checked": True,
        "new_messages": len(updates),
        "triggered": briefing_triggered or bool(question_results) or bool(approval_results) or bool(generation_results),
    }
    if briefing_triggered:
        from agents.fixera.ceo_lead import run_daily_briefing_and_notify

        result["notify_result"] = run_daily_briefing_and_notify()
    if question_results:
        result["question_results"] = question_results
    if approval_results:
        result["approval_results"] = approval_results
    if generation_results:
        result["generation_results"] = generation_results
    return result
