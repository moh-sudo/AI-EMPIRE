"""Architecture & Platform Assurance Agent -- Systems & Automation,
System Architecture pillar.

Scoped in governance/policies/systems_automation_governance.md's
"Architecture & Platform Assurance Pillar" section (2026-08-15)
BEFORE this file was written, per Rule 10. Implements exactly that
v0.1 scope, nothing more: n8n workflow drift only -- the full 24-section
vision (governance/policies/architecture_assurance_vision.md) is real
future work, not attempted here.

Directly motivated by a real incident the same day it was scoped: a
workflow looked "active" in n8n's UI but genuinely wasn't, discovered
only by reading n8n's own restart log two days later. This agent
answers that exact question mechanically: for every workflow this repo
declares (infrastructure/n8n/*.json), does n8n's own database agree
about whether it's active?

Read-only by construction, not just by convention: the SQLite
connection to n8n's database opens in URI mode=ro, which SQLite
itself enforces at the engine level (verified live -- a write attempt
raises OperationalError, not just "we promise not to write"). This
agent never modifies a workflow file or n8n's database in any way.
"""

import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
N8N_WORKFLOWS_DIR = REPO_ROOT / "infrastructure" / "n8n"
N8N_SQLITE_PATH = Path.home() / ".n8n" / "database.sqlite"


def _read_declared_workflows(workflows_dir: Path = N8N_WORKFLOWS_DIR) -> dict:
    """The repo's declared source of truth: each infrastructure/n8n/*.json
    file's name + intended active state. A file that fails to parse is
    skipped, not fatal -- one bad file shouldn't block checking every
    other one."""
    declared = {}
    for f in sorted(workflows_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        name = data.get("name")
        if name:
            declared[name] = {"active": bool(data.get("active", False)), "file": f.name}
    return declared


def _read_real_workflows(db_path: Path = N8N_SQLITE_PATH) -> dict | None:
    """Read-only query against n8n's own SQLite database. Filters out
    archived rows (isArchived = 1) -- found live 2026-08-15 that n8n
    keeps an old archived copy under the same name when a workflow is
    replaced (e.g. 'audit-agent-daily' has two rows, one archived from
    its original 2026-07-22 creation, one live from 2026-07-26); only
    the non-archived row reflects what's actually running. Returns
    None (not an error) if the database file doesn't exist -- n8n
    installed but never run is a real, distinct state from a query
    failure."""
    if not db_path.exists():
        return None

    uri = db_path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name, active FROM workflow_entity WHERE isArchived = 0")
        rows = cur.fetchall()
    finally:
        conn.close()

    real: dict[str, bool] = {}
    duplicates: set[str] = set()
    for name, active in rows:
        if name in real:
            duplicates.add(name)
        real[name] = bool(active)
    return {"workflows": real, "duplicate_active_names": sorted(duplicates)}


def detect_workflow_drift() -> dict:
    """Pure comparison logic, testable without touching real files/DB.
    Reports every mismatch found -- never guesses *why* a mismatch
    exists (Intentional vs. Undocumented vs. Violation needs more
    signal than a single boolean comparison provides; that's real
    future work per the vision document, not v0.1)."""
    declared = _read_declared_workflows()
    real_result = _read_real_workflows()
    if real_result is None:
        return {
            "ok": False,
            "reason": f"n8n's SQLite database not found at {N8N_SQLITE_PATH} -- is n8n installed and has it ever run?",
        }

    real = real_result["workflows"]
    findings = []

    for name in real_result["duplicate_active_names"]:
        findings.append(
            {
                "type": "duplicate_active_workflow_name",
                "workflow": name,
                "detail": "more than one non-archived n8n workflow shares this name -- real anomaly, not filtered by archival status",
            }
        )

    for name, decl in declared.items():
        if name not in real:
            findings.append(
                {
                    "type": "not_imported",
                    "workflow": name,
                    "detail": f"declared in {decl['file']} but no matching non-archived workflow found in n8n",
                }
            )
        elif decl["active"] != real[name]:
            findings.append(
                {
                    "type": "active_state_mismatch",
                    "workflow": name,
                    "declared_active": decl["active"],
                    "real_active": real[name],
                    "detail": f"{decl['file']} declares active={decl['active']}, n8n's real state is active={real[name]}",
                }
            )

    for name in real:
        if name not in declared:
            findings.append(
                {
                    "type": "undocumented_workflow",
                    "workflow": name,
                    "detail": "running in n8n with no matching infrastructure/n8n/*.json file",
                }
            )

    return {"ok": True, "findings": findings}


def run_architecture_drift_sweep() -> dict:
    """Full pipeline: detect -> alert -> log. Never raises; every step
    that can fail is isolated, same fail-safe pattern as
    dependency_remediation.py and host_security_scan.py's sweeps.
    Silent (no alert, no audit_vault write) when nothing is found --
    matches Dependency Remediation's precedent of not spamming a clean
    result."""
    drift = detect_workflow_drift()
    if not drift.get("ok"):
        return {"ok": False, "stage": "detect", "reason": drift.get("reason")}

    findings = drift["findings"]
    if not findings:
        return {"ok": True, "findings_count": 0, "findings": []}

    lines = [f"Architecture Drift Detected: {len(findings)} n8n workflow finding(s)."]
    for f in findings:
        lines.append(f"- [{f['type']}] {f['workflow']}: {f['detail']}")
    lines.append("Nothing has been changed -- this is a report only, review and correct manually.")
    message = "\n".join(lines)

    try:
        from agents.systems._telegram import send_telegram

        send_telegram(message, token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")
    except Exception:
        pass  # alert failure never blocks the audit_vault log below

    try:
        from shared.systems_db_connector import write_audit_vault

        write_audit_vault(
            agent_id="systems-architecture-assurance-v0.1",
            division="systems",
            action="architecture_drift_scan",
            outcome="drift_found",
            data_classification="INTERNAL",
            law_reference="Systems & Automation Governance -- Architecture & Platform Assurance Pillar",
            metadata={"findings": findings},
        )
    except Exception:
        pass  # DB log failure never blocks reporting the real result below

    return {"ok": True, "findings_count": len(findings), "findings": findings}
