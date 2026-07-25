"""Shared Telegram send helper -- Forex Division.

Split out 2026-07-26 after Mohamed correctly pointed out that Entry &
Exit's trade-execution alerts and CEO/Lead's routine market briefings
were sharing one bot/chat -- a real trade proposal needing his
confirmation could get buried under a routine market update, or vice
versa. Each caller now supplies its own token env var name, so
different agents can use different bots while sharing one
implementation (message formatting, graceful-failure handling,
timeouts) instead of duplicating the request logic per agent.
"""

import os

import requests


def send_telegram(message: str, token_env: str, chat_id_env: str = "TELEGRAM_CHAT_ID") -> dict:
    """Sends a one-way Telegram message via the bot whose token lives
    in the env var named by token_env. Never raises on failure or
    missing config -- a notification failing shouldn't crash whatever
    pipeline called it; logs a failed-send experience row instead."""
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
        from agents.forex._memory_helpers import safe_add_experience

        safe_add_experience(
            division="forex", agent_id="forex-telegram", event_type="telegram_send_failed",
            context=message, outcome="failed", metadata={"error": str(e), "token_env": token_env},
        )
        return {"sent": False, "reason": str(e)}
