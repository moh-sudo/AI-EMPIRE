"""Minimal HTTP wrapper around Fixera Division's CEO/Lead briefing
delivery, same pattern as agents/audit/server.py and
agents/forex/server.py -- n8n has no shell/command-execution node on
this installation, so n8n's HTTP Request node triggers these endpoints
instead of running Python directly.
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from agents.fixera.ceo_lead import run_daily_briefing_and_notify
from agents.fixera.marketplace_price_regulation import run_new_listings_sweep
from agents.fixera.telegram_listener import check_for_briefing_requests

app = FastAPI(title="Fixera Division -- CEO/Lead Briefing")


@app.post("/run-briefing")
def run_briefing():
    """Scheduled push -- n8n's cron (once daily, morning) hits this."""
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


@app.post("/check-new-listings")
def check_new_listings():
    """On-demand trigger -- n8n polls this every ~2 min (tighter than the
    30s Telegram poll is overkill here; new listings don't need that,
    but this is still far closer to real-time than the once-daily
    briefing). Alerts on any new/price-changed vendor_products not
    already notified -- see agents/fixera/marketplace_price_regulation.py."""
    return run_new_listings_sweep()
