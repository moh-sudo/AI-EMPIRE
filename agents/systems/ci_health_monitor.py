"""CI Health Monitoring Agent -- Systems & Automation, Software
Development pillar.

Scoped in governance/policies/systems_automation_governance.md's "CI
Health Monitoring Pillar" section (2026-08-15) BEFORE this file was
written, per Rule 10. First real slice of a much larger vision
(governance/policies/software_development_vision.md) -- v0.1 does
exactly one thing: detect whether the latest GitHub Actions run on
`master` is passing or failing, and alert on a state change. Pure
observability -- there is nothing here to auto-fix, so unlike every
other agent in this division there is no "propose vs. auto-apply"
axis at all; this only ever detects and reports.

Uses GitHub's REST API directly via requests, not the `gh` CLI --
the CLI's auth is tied to Mohamed's own interactive login, which
isn't reliable for something that has to run unattended via a
scheduled sweep. Needs a GITHUB_TOKEN in .env (fine-grained PAT,
Actions: Read-only + Contents: Read-only on moh-sudo/AI-EMPIRE) --
Mohamed sets this up himself, same boundary as every other credential
in this project.

State tracking reuses audit_vault (its own most recent
'ci_health_check' row) rather than a new database table -- same
trick host_security_scan.py uses. Alerts only on a real state change
(CI just broke, or CI just recovered), never repeats the same alert
for a run that's still broken, matching Reliability & Monitoring's
Rule 5/6 precedent (log state changes, not every poll).
"""

import os

import requests

GITHUB_OWNER = "moh-sudo"
GITHUB_REPO = "AI-EMPIRE"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
_TIMEOUT = 15


def _headers() -> dict | None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def fetch_latest_master_run() -> dict:
    """Honest 'not available' if GITHUB_TOKEN isn't configured, same
    principle as every other agent's tool-availability check in this
    division. Only ever reads -- never triggers, cancels, or retries
    a run."""
    headers = _headers()
    if headers is None:
        return {
            "ok": False,
            "reason": (
                "GITHUB_TOKEN not configured in .env -- see systems_automation_governance.md's "
                "CI Health Monitoring Pillar for the exact token scope needed."
            ),
        }

    try:
        resp = requests.get(
            f"{GITHUB_API_BASE}/actions/runs",
            headers=headers,
            params={"branch": "master", "per_page": 1},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"ok": False, "reason": str(e)}

    runs = resp.json().get("workflow_runs", [])
    if not runs:
        return {"ok": False, "reason": "No CI runs found on master."}

    run = runs[0]
    if run.get("status") != "completed":
        return {
            "ok": False,
            "reason": f"Latest run (id {run['id']}) is still {run.get('status')} -- check again later.",
        }

    return {
        "ok": True,
        "run_id": run["id"],
        "conclusion": run["conclusion"],
        "head_sha": run["head_sha"],
        "commit_message": (run.get("head_commit") or {}).get("message") or "",
        "html_url": run["html_url"],
    }


def fetch_failed_steps(run_id: int) -> list[str]:
    """Only meaningful when a run's conclusion is 'failure' -- names
    the specific step(s) that broke (e.g. 'lint-and-test / pytest')
    rather than just reporting 'CI failed'. Fails soft (empty list)
    on any API error -- the alert still fires with the run URL even
    if step-level detail can't be fetched."""
    headers = _headers()
    if headers is None:
        return []

    try:
        resp = requests.get(f"{GITHUB_API_BASE}/actions/runs/{run_id}/jobs", headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    failed = []
    for job in resp.json().get("jobs", []):
        for step in job.get("steps", []):
            if step.get("conclusion") == "failure":
                failed.append(f"{job['name']} / {step['name']}")
    return failed


def _get_last_known_conclusion() -> str | None:
    """None means this is the very first check ever run -- no prior
    state to compare against, so run_ci_health_sweep() treats that as
    establishing a baseline, not a state change worth alerting on."""
    from shared.db import get_client

    result = (
        get_client()
        .table("audit_vault")
        .select("metadata")
        .eq("action", "ci_health_check")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]["metadata"].get("conclusion")


def run_ci_health_sweep() -> dict:
    """Full pipeline: fetch latest master run -> compare against last
    known state -> alert + log only on a real change (or silently
    establish the first-ever baseline). Never raises; alert/log
    failures are non-blocking, same fail-safe pattern as every other
    agent's sweep in this division."""
    run = fetch_latest_master_run()
    if not run.get("ok"):
        return {"ok": False, "stage": "fetch", "reason": run.get("reason")}

    last_conclusion = _get_last_known_conclusion()
    current_conclusion = run["conclusion"]
    is_first_check = last_conclusion is None

    if not is_first_check and last_conclusion == current_conclusion:
        return {"ok": True, "state_changed": False, "conclusion": current_conclusion}

    failed_steps = fetch_failed_steps(run["run_id"]) if current_conclusion == "failure" else []

    if not is_first_check:
        commit_summary = run["commit_message"].splitlines()[0] if run["commit_message"] else run["head_sha"][:7]
        if current_conclusion == "failure":
            steps_text = ", ".join(failed_steps) if failed_steps else "unknown step (couldn't fetch job details)"
            message = f"CI is now FAILING on master.\n\nCommit: {commit_summary}\nFailed step(s): {steps_text}\n\n{run['html_url']}"
        else:
            message = f"CI has RECOVERED on master (now {current_conclusion}).\n\nCommit: {commit_summary}\n\n{run['html_url']}"

        try:
            from agents.systems._telegram import send_telegram

            send_telegram(message, token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")
        except Exception:
            pass  # alert failure never blocks the audit_vault log below

    try:
        from shared.systems_db_connector import write_audit_vault

        write_audit_vault(
            agent_id="systems-ci-health-monitor-v0.1",
            division="systems",
            action="ci_health_check",
            outcome=current_conclusion,
            data_classification="INTERNAL",
            law_reference="Systems & Automation Governance -- CI Health Monitoring Pillar",
            metadata={
                "run_id": run["run_id"],
                "conclusion": current_conclusion,
                "failed_steps": failed_steps,
                "html_url": run["html_url"],
            },
        )
    except Exception:
        pass  # DB log failure never blocks reporting the real result below

    return {
        "ok": True,
        "state_changed": not is_first_check,
        "conclusion": current_conclusion,
        "failed_steps": failed_steps,
    }
