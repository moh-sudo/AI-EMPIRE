"""Minimal HTTP wrapper around the Audit Agent so n8n's HTTP Request node
can trigger it (this n8n installation has no shell/command-execution
node available — it explicitly points to HTTP Request instead).
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from agents.audit.audit_agent import run
from agents.audit.telegram_listener import check_for_audit_requests

app = FastAPI(title="Audit Agent")


@app.post("/run")
def run_audit_sweep():
    result = run(send_email_on_alert=True)
    return {
        "status": result["report"]["status"],
        "report_id": result["report"]["report_id"],
    }


@app.post("/check-telegram")
def check_telegram():
    """On-demand trigger -- n8n polls this every ~30s; handles
    STATUS/PROPOSAL ACK commands."""
    return check_for_audit_requests()


@app.post("/run-full-buildout-sweep")
def run_full_buildout_sweep():
    """Scheduled trigger -- n8n's cron hits this periodically to run
    Security, Financial, Performance, Reports, and Bug Detection
    together (the 2026-08-03 full buildout, separate from the
    original 4 email-alerted governance checks above)."""
    from agents.audit.bug_detection import run_bug_detection_sweep
    from agents.audit.financial_verification import run_financial_verification
    from agents.audit.performance_monitor import run_performance_check
    from agents.audit.report_verification import check_scheduled_reports_ran_today
    from agents.audit.security_audit import run_security_audit

    return {
        "security": run_security_audit(),
        "financial": run_financial_verification(),
        "performance": run_performance_check(),
        "reports": check_scheduled_reports_ran_today(),
        "bug_detection": run_bug_detection_sweep(),
    }
