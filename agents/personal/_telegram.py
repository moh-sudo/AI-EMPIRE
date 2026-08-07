"""Shared Telegram send helper -- Personal Division.

Deliberately a duplicate of agents/fixera/_telegram.py and
agents/forex/_telegram.py, not a cross-import -- this project keeps
every division's code fully separate, even for a generic 12-line
helper, so no division ever has to import from another's namespace.
"""

import os

import requests


def send_telegram(message: str, token_env: str, chat_id_env: str = "TELEGRAM_CHAT_ID") -> dict:
    """Sends a one-way Telegram message via the bot whose token lives
    in the env var named by token_env. Never raises on failure or
    missing config."""
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
        from agents.personal._memory_helpers import safe_add_experience

        safe_add_experience(
            division="personal",
            agent_id="personal-telegram",
            event_type="telegram_send_failed",
            context=message,
            outcome="failed",
            metadata={"error": str(e), "token_env": token_env},
        )
        return {"sent": False, "reason": str(e)}
