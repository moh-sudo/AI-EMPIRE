"""Telegram inbound listener -- Personal Division.

Own dedicated bot (TELEGRAM_PERSONAL_BOT_TOKEN), separate from every
other division's bot, matching the pattern established for Fixera/
Forex -- habit check-offs and morning briefs shouldn't mix into a
business or trading chat.

Routing: "brief" triggers an on-demand Morning Brief (in addition to
whatever scheduled push exists). "DONE <number or name>" marks a habit
complete for today via agents.personal.habit_tracker.resolve_habit_reference()
+ mark_habit_done(). Anything else gets a short usage hint rather than
silently doing nothing.
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


def _handle_done(reference: str) -> str:
    from agents.personal.habit_tracker import mark_habit_done, resolve_habit_reference

    habit = resolve_habit_reference(reference)
    if habit is None:
        return f'No habit matches "{reference}". Reply with the number shown in today\'s check-in, or a clearer name.'
    if habit["done"]:
        return f'"{habit["name"]}" is already marked done for today.'

    mark_habit_done(habit["id"])
    return f'Marked "{habit["name"]}" done for today.'


def check_for_personal_requests() -> dict:
    """Polls Telegram's getUpdates once, advances the offset past every
    update seen. For any new message from Mohamed's own chat_id: the
    literal word "brief" triggers an on-demand Morning Brief; "DONE
    <ref>" marks a habit done; anything else gets a short usage hint.
    Never raises -- same fail-safe pattern as every other listener."""
    token = os.environ.get("TELEGRAM_PERSONAL_BOT_TOKEN")
    expected_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not expected_chat_id:
        return {"checked": False, "reason": "TELEGRAM_PERSONAL_BOT_TOKEN/TELEGRAM_CHAT_ID not configured."}

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

    from agents.personal._telegram import send_telegram

    highest_update_id = last_update_id or 0
    brief_triggered = False
    action_results = []

    for update in updates:
        highest_update_id = max(highest_update_id, update["update_id"])
        msg = update.get("message")
        if not msg:
            continue
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != str(expected_chat_id):
            continue
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
        if not text:
            continue

        if text.lower() == "brief":
            brief_triggered = True
            continue

        if text.upper().startswith("DONE "):
            reply = _handle_done(text[len("DONE ") :].strip())
        else:
            reply = (
                'Reply "DONE <number or habit name>" to check off a habit, or "brief" for an on-demand Morning Brief.'
            )

        send_telegram(reply, token_env="TELEGRAM_PERSONAL_BOT_TOKEN")
        action_results.append({"text": text, "reply": reply})

    _save_last_update_id(highest_update_id)

    result = {"checked": True, "new_messages": len(updates), "triggered": brief_triggered or bool(action_results)}
    if brief_triggered:
        from agents.personal.morning_brief import build_morning_brief

        brief = build_morning_brief()
        send_telegram(brief["summary"], token_env="TELEGRAM_PERSONAL_BOT_TOKEN")
        result["brief_sent"] = True
    if action_results:
        result["action_results"] = action_results
    return result
