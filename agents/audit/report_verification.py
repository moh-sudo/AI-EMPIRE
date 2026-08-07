"""Report Verification -- Audit & Verification Division.

Checks n8n's own real execution history (its SQLite database) for
whether each scheduled report/briefing workflow actually ran
successfully today -- not by re-calling the underlying function
(which would just prove the function works, not that the real
scheduled automation fired) but by reading n8n's own record of what
actually happened. Fully deterministic, no LLM needed. Read-only
connection to n8n's database -- never writes to it.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

N8N_DB_PATH = Path.home() / ".n8n" / "database.sqlite"

# Workflow IDs that are expected to run on their own daily schedule --
# matches the IDs assigned when each workflow JSON was created (see
# infrastructure/n8n/*.json). If a new scheduled workflow gets added,
# it needs to be added here too, deliberately not auto-discovered, so
# a typo'd workflow ID can't silently exempt itself from checking.
SCHEDULED_WORKFLOWS = {
    "F1x3r4Ce0Br13f1ngSchd": "Fixera CEO/Lead daily briefing",
    "F0r3xCe0Br13f1ngSchd": "Forex CEO/Lead daily briefing",
    "P3rs0n4lBr13fSchd": "Personal Morning Brief",
    "R5voBrUzux5k2yJN": "Audit Agent daily sweep",
}


def check_scheduled_reports_ran_today() -> dict:
    """Real read-only query against n8n's own execution history.
    Never raises -- if n8n's DB isn't reachable (e.g. n8n isn't
    running, or a lock conflict), reports that honestly rather than
    silently passing."""
    if not N8N_DB_PATH.exists():
        return {"ok": False, "reason": f"n8n database not found at {N8N_DB_PATH}"}

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    try:
        conn = sqlite3.connect(f"file:{N8N_DB_PATH}?mode=ro", uri=True, timeout=10)
        cur = conn.cursor()
        results = {}
        for workflow_id, name in SCHEDULED_WORKFLOWS.items():
            cur.execute(
                """
                SELECT status, startedAt FROM execution_entity
                WHERE workflowId = ? AND startedAt >= ?
                ORDER BY startedAt DESC
                """,
                (workflow_id, today_start),
            )
            rows = cur.fetchall()
            succeeded = any(r[0] == "success" for r in rows)
            results[name] = {"workflow_id": workflow_id, "executions_today": len(rows), "succeeded": succeeded}
        conn.close()
    except sqlite3.Error as e:
        return {"ok": False, "reason": str(e)}

    missing = [name for name, r in results.items() if not r["succeeded"]]
    return {"ok": True, "results": results, "missing_today": missing}
