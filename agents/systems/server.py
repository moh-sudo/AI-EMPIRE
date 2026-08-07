"""Minimal HTTP wrapper around the Reliability & Monitoring Agent so
n8n's HTTP Request node can trigger it (this n8n installation has no
shell/command-execution node available -- it explicitly points to
HTTP Request instead).
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from agents.systems.reliability_monitor import run_health_check_sweep
from agents.systems.telegram_listener import check_for_systems_requests

app = FastAPI(title="Systems & Automation Division")


@app.post("/health-check")
def health_check():
    return run_health_check_sweep(notify=True)


@app.post("/check-telegram")
def check_telegram():
    return check_for_systems_requests()
