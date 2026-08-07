"""Minimal HTTP wrapper around Personal Division, same pattern as every
other division's server.py -- n8n has no shell/command-execution node
on this installation, so n8n's HTTP Request node triggers these
endpoints instead of running Python directly.
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from agents.personal.morning_brief import build_morning_brief
from agents.personal.telegram_listener import check_for_personal_requests

app = FastAPI(title="Personal Division")


@app.post("/run-morning-brief")
def run_morning_brief():
    """Scheduled push -- n8n's cron (Mohamed's chosen morning time)
    hits this."""
    from agents.personal._telegram import send_telegram

    brief = build_morning_brief()
    send_result = send_telegram(brief["summary"], token_env="TELEGRAM_PERSONAL_BOT_TOKEN")
    return {"telegram_sent": send_result.get("sent", False)}


@app.post("/check-telegram")
def check_telegram():
    """On-demand trigger -- n8n polls this every ~30s; handles habit
    check-offs and on-demand brief requests."""
    return check_for_personal_requests()
