"""Minimal HTTP wrapper around Forex Division's CEO/Lead briefing
delivery, same pattern as agents/audit/server.py -- n8n has no shell/
command-execution node on this installation, so n8n's HTTP Request node
triggers these endpoints instead of running Python directly.
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from agents.forex.ceo_lead import run_daily_briefing_and_notify
from agents.forex.entry_exit_listener import check_for_trade_approvals
from agents.forex.telegram_listener import check_for_briefing_requests

app = FastAPI(title="Forex Division -- CEO/Lead Briefing")


@app.post("/run-briefing")
def run_briefing():
    """Scheduled push -- n8n's cron (2 AM / 8 AM NY time) hits this."""
    result = run_daily_briefing_and_notify()
    return {
        "telegram_messages_sent": result["telegram_messages_sent"],
        "telegram_messages_total": result["telegram_messages_total"],
    }


@app.post("/check-telegram")
def check_telegram():
    """On-demand trigger -- n8n polls this every ~30s; only actually
    runs the briefing if Mohamed sent a new message since last check."""
    return check_for_briefing_requests()


@app.post("/check-entry-exit-telegram")
def check_entry_exit_telegram():
    """On-demand trigger -- n8n polls this every ~30s; routes any new
    APPROVE/REJECT reply on Entry & Exit's own bot to
    agents.forex.entry_exit.handle_trade_approval_reply()."""
    return check_for_trade_approvals()
