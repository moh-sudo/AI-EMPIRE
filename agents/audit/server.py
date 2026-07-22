"""Minimal HTTP wrapper around the Audit Agent so n8n's HTTP Request node
can trigger it (this n8n installation has no shell/command-execution
node available — it explicitly points to HTTP Request instead).
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from agents.audit.audit_agent import run

app = FastAPI(title="Audit Agent")


@app.post("/run")
def run_audit_sweep():
    result = run(send_email_on_alert=True)
    return {
        "status": result["report"]["status"],
        "report_id": result["report"]["report_id"],
    }
