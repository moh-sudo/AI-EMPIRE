"""Telegram inbound listener -- Systems & Automation Division.

Commands:
- "STATUS" -- on-demand snapshot of every service's current
  circuit_breakers state, without waiting for the next scheduled
  health check.
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


def _handle_status() -> str:
    """Never raises -- a DB failure here must produce a real reply (so
    the Telegram offset always advances and this doesn't get
    re-attempted, and re-fail, every 30s forever), not an uncaught
    exception."""
    try:
        from shared.systems_db_connector import get_client

        rows = (
            get_client()
            .table("circuit_breakers")
            .select("service_name,state,failure_count,last_success_at")
            .order("service_name")
            .execute()
            .data
        )
    except Exception as e:
        return f"[Systems & Automation] Could not read circuit_breakers: {e}"

    if not rows:
        return "[Systems & Automation] No circuit_breakers rows yet -- health check sweep hasn't run."

    lines = ["[Systems & Automation -- current status]"]
    for r in rows:
        lines.append(f"{r['service_name']}: {r['state']} (failures: {r['failure_count']})")
    return "\n".join(lines)


def _handle_text(text: str) -> str:
    if text.strip().upper() == "STATUS":
        return _handle_status()
    return 'Reply "STATUS" for the current health of every monitored service.'


def check_for_systems_requests() -> dict:
    token = os.environ.get("TELEGRAM_SYSTEMS_BOT_TOKEN")
    expected_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not expected_chat_id:
        return {"checked": False, "reason": "TELEGRAM_SYSTEMS_BOT_TOKEN/TELEGRAM_CHAT_ID not configured."}

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

    from agents.systems._telegram import send_telegram

    highest_update_id = last_update_id or 0
    action_results = []

    for update in updates:
        highest_update_id = max(highest_update_id, update.get("update_id", highest_update_id))
        try:
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

            reply = _handle_text(text)
            send_telegram(reply, token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")
            action_results.append({"text": text, "reply": reply})
        except Exception as e:
            # One malformed/unexpected update must never block the rest of
            # this batch, and must never stop the offset below from
            # advancing -- that would mean this exact update gets
            # re-fetched and re-fail every 30s forever.
            action_results.append({"update_id": update.get("update_id"), "error": str(e)})

    _save_last_update_id(highest_update_id)

    result = {"checked": True, "new_messages": len(updates), "triggered": bool(action_results)}
    if action_results:
        result["action_results"] = action_results
    return result
