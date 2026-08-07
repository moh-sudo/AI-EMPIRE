"""Audit Agent v0.1 — CONTEXT.md Phase 3 / Roadmap 3.1.

Runs the 4 anomaly checks, produces a Red/Amber/Green report, saves it
immutably to audit_vault, and emails Mohamed if the result is Amber/Red.
Intentionally rule-based (no LLM) for v0.1 — all 4 checks are
deterministic SQL/threshold checks; the roadmap's completion criteria
don't require an LLM in the loop.
"""

import argparse
import sys
import uuid
from datetime import UTC, datetime

from dotenv import load_dotenv

load_dotenv()

from agents.audit.checks import SEVERITY_CRITICAL, Finding, run_all_checks
from shared.audit.incidents import log_incident
from shared.db import get_client
from shared.notifications.resend_client import send_email

MOHAMED_EMAIL = "mohamed2002shukri@gmail.com"
AGENT_ID = "audit-agent-v0.1"
DIVISION = "audit"


def classify_report(findings: list[Finding]) -> str:
    if any(f.triggered and f.severity == SEVERITY_CRITICAL for f in findings):
        return "Red"
    if any(f.triggered for f in findings):
        return "Amber"
    return "Green"


def build_report(findings: list[Finding]) -> dict:
    return {
        "report_id": str(uuid.uuid4()),
        "generated_at": datetime.now(UTC).isoformat(),
        "status": classify_report(findings),
        "findings": [
            {
                "check": f.check,
                "severity": f.severity,
                "triggered": f.triggered,
                "count": f.count,
                "details": f.details,
            }
            for f in findings
        ],
    }


def save_report(report: dict) -> dict:
    result = (
        get_client()
        .table("audit_vault")
        .insert(
            {
                "agent_id": AGENT_ID,
                "division": DIVISION,
                "action": "daily_audit_sweep",
                "outcome": report["status"],
                "data_classification": "INTERNAL",
                "metadata": report,
            }
        )
        .execute()
    )
    return result.data[0]


def email_report(report: dict) -> None:
    triggered = [f for f in report["findings"] if f["triggered"]]
    rows = "".join(f"<li><b>{f['check']}</b> ({f['severity']}) — {f['count']} finding(s)</li>" for f in triggered)
    html = f"""
    <h2>Audit Report — {report["status"]}</h2>
    <p>Generated: {report["generated_at"]}</p>
    <ul>{rows}</ul>
    <p>Report ID: {report["report_id"]}</p>
    """
    send_email(
        to=MOHAMED_EMAIL,
        subject=f"[AI_EMPIRE Audit] {report['status']} report — {len(triggered)} finding(s)",
        html=html,
    )


def run(*, send_email_on_alert: bool = True) -> dict:
    findings = run_all_checks()
    report = build_report(findings)
    saved = save_report(report)

    if report["status"] in ("Amber", "Red"):
        if send_email_on_alert:
            try:
                email_report(report)
            except Exception as e:
                log_incident(
                    agent_id=AGENT_ID,
                    division=DIVISION,
                    action="email_report",
                    outcome="failed",
                    severity=2,
                    reason=f"Audit report email failed to send: {e}",
                )

    return {"report": report, "audit_vault_row": saved}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Audit Agent v0.1 sweep")
    parser.add_argument("--no-email", action="store_true", help="Skip sending the alert email even on Amber/Red")
    args = parser.parse_args()

    result = run(send_email_on_alert=not args.no_email)
    report = result["report"]
    print(f"Audit sweep complete: {report['status']} (report_id={report['report_id']})")
    for f in report["findings"]:
        marker = "TRIGGERED" if f["triggered"] else "clear"
        print(f"  - {f['check']} [{f['severity']}]: {marker} (count={f['count']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
