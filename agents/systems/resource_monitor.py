"""Resource Monitoring Agent -- Systems & Automation, Security &
Performance pillar.

Scoped in governance/policies/systems_automation_governance.md's
"Resource Monitoring Pillar" section (2026-08-18) BEFORE this file was
written, per Rule 10. Fills the "Performance" half of Security &
Performance's own name -- Reliability & Monitoring only checks
liveness, never resource pressure (a service can be "healthy" and
responding while quietly leaking memory or pegging CPU).

v0.1 tracks exactly two processes (n8n, the systems server) by port --
not every division server, keeping this to what's actually running
continuously today -- plus disk free space on C:\\. Detect and alert
only, same as every other agent in this division: nothing here kills
or restarts a process for high resource use, that stays a human call.

Thresholds (memory 1GB n8n / 500MB systems server, CPU 80%, disk
<10GB free) were chosen from real current usage checked live before
picking numbers, not guessed -- see the governance section for the
reasoning, including why they don't need retuning on a hardware
upgrade (memory thresholds are about catching software leaks, not
hardware capacity; psutil's CPU percentage is already per-core
normalized; the disk floor is a flat safety margin, not a percentage).
"""

import shutil

import psutil

N8N_PORT = 5678
SYSTEMS_SERVER_PORT = 8007

MEMORY_THRESHOLDS_MB = {
    "n8n": 1024,
    "systems_server": 500,
}
CPU_THRESHOLD_PERCENT = 80.0
DISK_FREE_THRESHOLD_GB = 10.0
DISK_PATH = "C:\\"


def _find_pid_on_port(port: int) -> int | None:
    """Same technique as reliability_monitor.py's own helper --
    duplicated deliberately rather than imported, matching this
    project's convention of not cross-importing small, division-
    adjacent helpers between agent modules."""
    for conn in psutil.net_connections(kind="tcp"):
        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            return conn.pid
    return None


def check_process_resources(name: str, port: int) -> dict:
    """Honest 'not running' rather than an error if the process isn't
    up right now -- matches every other agent's tool-availability
    pattern in this division."""
    pid = _find_pid_on_port(port)
    if pid is None:
        return {"ok": False, "reason": f"{name} is not running (nothing listening on port {port})."}

    try:
        proc = psutil.Process(pid)
        memory_mb = proc.memory_info().rss / (1024 * 1024)
        cpu_percent = proc.cpu_percent(interval=1.0)
    except psutil.NoSuchProcess:
        return {"ok": False, "reason": f"{name}'s process (pid {pid}) disappeared mid-check."}

    return {
        "ok": True,
        "name": name,
        "pid": pid,
        "memory_mb": round(memory_mb, 1),
        "cpu_percent": cpu_percent,
    }


def check_disk_free(path: str = DISK_PATH) -> dict:
    usage = shutil.disk_usage(path)
    return {
        "ok": True,
        "path": path,
        "free_gb": round(usage.free / (1024**3), 1),
        "total_gb": round(usage.total / (1024**3), 1),
    }


def _evaluate_process(result: dict) -> str:
    """Pure classification, no I/O -- 'not_running' is its own state
    (not folded into 'warning') so a genuinely stopped service reads
    differently from a running-but-over-threshold one."""
    if not result.get("ok"):
        return "not_running"
    threshold_mb = MEMORY_THRESHOLDS_MB.get(result["name"], float("inf"))
    if result["memory_mb"] > threshold_mb or result["cpu_percent"] > CPU_THRESHOLD_PERCENT:
        return "warning"
    return "ok"


def _evaluate_disk(result: dict) -> str:
    if result["free_gb"] < DISK_FREE_THRESHOLD_GB:
        return "warning"
    return "ok"


def _get_last_known_states() -> dict:
    """Reuses ci_health_monitor.py's exact trick: compare against the
    last logged audit_vault row for this action -- no new table.
    Empty dict means this is the very first check ever (or the row's
    shape predates this field), treated as establishing a baseline,
    not a state change worth alerting on."""
    from shared.db import get_client

    result = (
        get_client()
        .table("audit_vault")
        .select("metadata")
        .eq("action", "resource_check")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return {}
    return result.data[0]["metadata"].get("states", {})


def run_resource_check() -> dict:
    """Full pipeline: check n8n, systems server, disk -> classify each
    -> compare against last known states -> alert + log only on a
    real change (or silently establish the first-ever baseline).
    Never raises; alert/log failures are non-blocking, same fail-safe
    pattern as every other agent's sweep in this division."""
    n8n = check_process_resources("n8n", N8N_PORT)
    systems_server = check_process_resources("systems_server", SYSTEMS_SERVER_PORT)
    disk = check_disk_free()

    current_states = {
        "n8n": _evaluate_process(n8n),
        "systems_server": _evaluate_process(systems_server),
        "disk": _evaluate_disk(disk),
    }

    last_states = _get_last_known_states()
    is_first_check = not last_states
    changed = {} if is_first_check else {k: v for k, v in current_states.items() if last_states.get(k) != v}

    if changed:
        lines = ["Resource Monitoring -- state change"]
        for name, new_state in changed.items():
            lines.append(f"{name}: {last_states.get(name)} -> {new_state}")
        lines.append("")
        lines.append(f"n8n: {n8n}")
        lines.append(f"systems_server: {systems_server}")
        lines.append(f"disk: {disk}")
        message = "\n".join(lines)

        try:
            from agents.systems._telegram import send_telegram

            send_telegram(message, token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")
        except Exception:
            pass  # alert failure never blocks the audit_vault log below

    if is_first_check or changed:
        try:
            from shared.systems_db_connector import write_audit_vault

            write_audit_vault(
                agent_id="systems-resource-monitor-v0.1",
                division="systems",
                action="resource_check",
                outcome="checked",
                data_classification="INTERNAL",
                law_reference="Systems & Automation Governance -- Resource Monitoring Pillar",
                metadata={
                    "states": current_states,
                    "n8n": n8n,
                    "systems_server": systems_server,
                    "disk": disk,
                },
            )
        except Exception:
            pass  # DB log failure never blocks reporting the real result below

    return {
        "ok": True,
        "states": current_states,
        "changed": changed,
        "n8n": n8n,
        "systems_server": systems_server,
        "disk": disk,
    }
