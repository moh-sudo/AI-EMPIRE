"""Telegram inbound listener -- Research & Innovation Division.

Own dedicated bot (TELEGRAM_RII_BOT_TOKEN), matching every other
division's pattern.

Commands:
- "RESEARCH <question>" -- real web search + Ollama-synthesized,
  cited answer via agents.rii.research.research_topic()
- "WATCH <topic>" -- adds a new watchtower
- "UNWATCH <topic>" -- deactivates one
- "WATCHES" -- lists active watchtowers
"""

import json
import os
from pathlib import Path

import requests

STATE_FILE = Path(__file__).resolve().parent / ".telegram_offset.json"


def _read_last_update_id() -> int | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text()).get("last_update_id")
    except (json.JSONDecodeError, OSError):
        return None


def _save_last_update_id(update_id: int) -> None:
    STATE_FILE.write_text(json.dumps({"last_update_id": update_id}))


def _handle_research(question: str) -> str:
    from agents.rii.research import research_topic

    result = research_topic(question)
    if not result.get("ok"):
        return f"Couldn't research that: {result.get('reason')}"
    return result["answer"]


def _handle_watch(topic: str) -> str:
    from agents.rii.watchtower import add_watchtower

    add_watchtower(topic)
    return f'Watchtower added for "{topic}" -- checked periodically, you\'ll be alerted on genuinely new results.'


def _handle_unwatch(topic: str) -> str:
    from agents.rii.watchtower import remove_watchtower

    result = remove_watchtower(topic)
    if not result.get("ok"):
        return result["reason"]
    return f'Removed watchtower for "{result["removed"]}".'


def _handle_watches() -> str:
    from agents.rii.watchtower import list_watchtowers

    watchtowers = list_watchtowers()
    if not watchtowers:
        return 'No active watchtowers. Add one with "WATCH <topic>".'
    lines = [f"  - {w['topic']}" for w in watchtowers]
    return "Active watchtowers:\n" + "\n".join(lines)


def _handle_text(text: str) -> str:
    text_stripped = text.strip()
    text_upper = text_stripped.upper()

    if text_upper == "WATCHES":
        return _handle_watches()
    if text_upper.startswith("RESEARCH "):
        return _handle_research(text_stripped[len("RESEARCH ") :].strip())
    if text_upper.startswith("WATCH "):
        return _handle_watch(text_stripped[len("WATCH ") :].strip())
    if text_upper.startswith("UNWATCH "):
        return _handle_unwatch(text_stripped[len("UNWATCH ") :].strip())

    return (
        'Reply "RESEARCH <question>" for a real, sourced answer on any topic, "WATCH <topic>" to '
        'monitor it for new results, "UNWATCH <topic>" to stop, or "WATCHES" to see what\'s active.'
    )


def check_for_rii_requests() -> dict:
    """Polls Telegram's getUpdates once, advances the offset past every
    update seen. Never raises -- same fail-safe pattern as every other
    listener in this project."""
    token = os.environ.get("TELEGRAM_RII_BOT_TOKEN")
    expected_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not expected_chat_id:
        return {"checked": False, "reason": "TELEGRAM_RII_BOT_TOKEN/TELEGRAM_CHAT_ID not configured."}

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

    from agents.rii._telegram import send_telegram

    highest_update_id = last_update_id or 0
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
        if not text:
            continue

        reply = _handle_text(text)
        send_telegram(reply, token_env="TELEGRAM_RII_BOT_TOKEN")
        action_results.append({"text": text, "reply": reply})

    _save_last_update_id(highest_update_id)

    result = {"checked": True, "new_messages": len(updates), "triggered": bool(action_results)}
    if action_results:
        result["action_results"] = action_results
    return result
