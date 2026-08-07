"""Minimal HTTP wrapper around Learning Division, same pattern as every
other division's server.py -- n8n has no shell/command-execution node
on this installation, so n8n's HTTP Request node triggers this
endpoint instead of running Python directly.
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from agents.learning.telegram_listener import check_for_learning_requests

app = FastAPI(title="Learning Division")


@app.post("/check-telegram")
def check_telegram():
    """On-demand trigger -- n8n polls this every ~30s; handles review
    sessions and all content-ingestion sources."""
    return check_for_learning_requests()
