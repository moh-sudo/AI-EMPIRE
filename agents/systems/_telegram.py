"""Shared Telegram send helper -- Systems & Automation Division.

Deliberately a duplicate of every other division's _telegram.py, not a
cross-import.
"""

import os

import requests


def send_telegram(message: str, token_env: str, chat_id_env: str = "TELEGRAM_CHAT_ID") -> dict:
    token = os.environ.get(token_env)
    chat_id = os.environ.get(chat_id_env)
    if not token or not chat_id:
        return {"sent": False, "reason": f"{token_env}/{chat_id_env} not configured in .env yet."}

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        resp.raise_for_status()
        return {"sent": True, "response": resp.json()}
    except requests.RequestException as e:
        from agents.systems._memory_helpers import safe_add_experience

        safe_add_experience(
            division="systems",
            agent_id="systems-telegram",
            event_type="telegram_send_failed",
            context=message,
            outcome="failed",
            metadata={"error": str(e), "token_env": token_env},
        )
        return {"sent": False, "reason": str(e)}
