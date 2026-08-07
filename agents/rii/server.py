"""Minimal HTTP wrapper around Research & Innovation Division, same
pattern as every other division's server.py -- n8n has no shell/
command-execution node on this installation, so n8n's HTTP Request
node triggers these endpoints instead of running Python directly.
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from agents.rii.telegram_listener import check_for_rii_requests
from agents.rii.watchtower import check_all_watchtowers

app = FastAPI(title="Research & Innovation Division")


@app.post("/check-telegram")
def check_telegram():
    """On-demand trigger -- n8n polls this every ~30s; handles
    RESEARCH/WATCH/UNWATCH/WATCHES commands."""
    return check_for_rii_requests()


@app.post("/check-watchtowers")
def check_watchtowers():
    """Scheduled trigger -- n8n's cron hits this periodically to
    re-check every active watchtower for new results."""
    return check_all_watchtowers()
