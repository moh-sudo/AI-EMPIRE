"""Reliability & Monitoring Agent -- Systems & Automation Division.

Implements shared/prompts/systems_reliability-monitor_v1.json and the
Operational Efficiency Standard's "Circuit Breakers & Self-Healing"
section (CONTEXT.md): real health checks against every service this
project actually depends on, writing real state to the
circuit_breakers table that has existed since Phase 1 but was never
used until now.

Deliberately does NOT monitor apps/api_gateway (the Hybrid Router) --
confirmed live 2026-08-06 that it isn't currently running as a
persistent service on this machine, so there is nothing real to check
yet. Only real, currently-running services are covered: n8n, Ollama,
Supabase, and each division's own FastAPI server.

State machine per service (matches the 5 states the circuit_breakers
table's CHECK constraint already allows):
  healthy -> warning (1 failure) -> open_circuit (2+ consecutive
  failures). From open_circuit: if auto_restart_permitted, one restart
  attempt is made (state -> recovery_test) and re-checked; success
  returns to healthy, failure moves to fallback (auto-restart is not
  retried again until the service is next observed healthy, to avoid
  a restart-thrash loop). If auto_restart_permitted is false (Ollama,
  Supabase), open_circuit goes straight to fallback -- alert only,
  per the Operational Efficiency Standard's explicit rule that
  Supabase is never auto-restarted (mid-transaction restart risk).
"""

import os
import socket
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"

DIVISION_PORTS = {
    "audit": 8001,
    "forex": 8002,
    "fixera": 8003,
    "personal": 8004,
    "learning": 8005,
    "rii": 8006,
}

N8N_PORT = 5678
FAILURES_FOR_OPEN_CIRCUIT = 2


# ---------------------------------------------------------------------
# Health checks -- each returns True (healthy) / False (unhealthy),
# never raises.
# ---------------------------------------------------------------------


def _tcp_reachable(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 5.0) -> bool:
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code < 500
    except requests.RequestException:
        return False


def check_n8n() -> bool:
    return _tcp_reachable("127.0.0.1", N8N_PORT)


def check_ollama() -> bool:
    base = os.environ.get("OLLAMA_BASE_URL", "")
    if not base:
        return False
    return _http_ok(f"{base}/api/tags")


def check_supabase() -> bool:
    """Uses this agent's own scoped connector (shared/systems_db_connector.py) --
    a custom JWT carrying an 'app_role': 'systems_agent' claim, gated by
    RLS policies on circuit_breakers/audit_vault
    (infrastructure/database/migrations/0010_systems_agent_rls_jwt.sql).
    Real database-level enforcement via Supabase's REST API, not
    shared/db.py's blanket service-role client -- see that module's
    docstring for why this replaced the earlier Postgres-role approach
    (0009), which is real but blocked by an unrelated Supavisor pooler
    issue."""
    try:
        from shared.systems_db_connector import get_circuit_breaker

        get_circuit_breaker("__health_check_probe__")
        return True
    except Exception:
        return False


def _check_division_server(division: str) -> bool:
    port = DIVISION_PORTS[division]
    return _http_ok(f"http://127.0.0.1:{port}/openapi.json")


# ---------------------------------------------------------------------
# Restart actions -- Windows-specific (this project runs on Windows).
# Only stateless local processes are ever restarted: n8n and each
# division's own FastAPI server. Never Ollama (remote Mac, no access
# from here) or Supabase (explicit rule, data-corruption risk).
# ---------------------------------------------------------------------


def _find_pid_on_port(port: int) -> int | None:
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.SubprocessError:
        return None
    for line in result.stdout.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            parts = line.split()
            try:
                return int(parts[-1])
            except (ValueError, IndexError):
                continue
    return None


def _kill_pid(pid: int) -> None:
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=15)


def _spawn_detached(args: list[str], cwd: Path) -> None:
    subprocess.Popen(
        args,
        cwd=str(cwd),
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def restart_n8n() -> dict:
    pid = _find_pid_on_port(N8N_PORT)
    if pid:
        _kill_pid(pid)
    _spawn_detached(["n8n", "start"], cwd=REPO_ROOT)
    return {"restarted": True, "killed_pid": pid}


def restart_division_server(division: str) -> dict:
    port = DIVISION_PORTS[division]
    pid = _find_pid_on_port(port)
    if pid:
        _kill_pid(pid)
    _spawn_detached(
        [str(VENV_PYTHON), "-m", "uvicorn", f"agents.{division}.server:app", "--port", str(port), "--host", "0.0.0.0"],
        cwd=REPO_ROOT,
    )
    return {"restarted": True, "killed_pid": pid}


# ---------------------------------------------------------------------
# Service registry: name -> (check_fn, auto_restart_permitted, restart_fn)
# ---------------------------------------------------------------------


def _service_registry() -> dict[str, tuple[Callable[[], bool], bool, Callable[[], dict] | None]]:
    services: dict[str, tuple[Callable[[], bool], bool, Callable[[], dict] | None]] = {
        "n8n": (check_n8n, True, restart_n8n),
        "ollama": (check_ollama, False, None),
        "supabase": (check_supabase, False, None),
    }
    for division in DIVISION_PORTS:
        services[f"{division}_server"] = (
            lambda d=division: _check_division_server(d),
            True,
            lambda d=division: restart_division_server(d),
        )
    return services


# ---------------------------------------------------------------------
# Circuit breaker state transitions
# ---------------------------------------------------------------------


def _get_or_create_row(service_name: str, auto_restart_permitted: bool) -> dict:
    from shared.systems_db_connector import create_circuit_breaker, get_circuit_breaker

    row = get_circuit_breaker(service_name)
    if row:
        return row
    return create_circuit_breaker(service_name, auto_restart_permitted)


def _write_row(service_name: str, updates: dict) -> None:
    from shared.systems_db_connector import update_circuit_breaker

    update_circuit_breaker(service_name, updates)


def _log_state_change(service_name: str, old_state: str, new_state: str, division: str = "systems") -> None:
    from shared.systems_db_connector import write_audit_vault

    write_audit_vault(
        agent_id="systems-reliability-monitor-v0.1",
        division=division,
        action="health_check_state_change",
        outcome=new_state,
        data_classification="INTERNAL",
        law_reference="Operational Efficiency Standard -- Circuit Breakers & Self-Healing",
        metadata={"service": service_name, "old_state": old_state, "new_state": new_state},
    )


def check_and_update(service_name: str) -> dict:
    """Runs one service's health check and updates its circuit_breakers
    row, restarting it if the state machine calls for it. Genuinely
    never raises -- every step that can fail (the health check itself,
    reading/writing circuit_breakers, the restart attempt, the
    audit_vault log) is individually caught, so one service's transient
    DB or network hiccup can never abort the sweep for every other
    service. A failure in the database layer is reported back in the
    returned dict's "error" key rather than silently vanishing."""
    try:
        check_fn, auto_restart_permitted, restart_fn = _service_registry()[service_name]
    except KeyError:
        return {"service": service_name, "error": "unknown service"}

    now = datetime.now(UTC).isoformat()

    try:
        row = _get_or_create_row(service_name, auto_restart_permitted)
    except Exception as e:
        return {"service": service_name, "error": f"could not read/create circuit_breakers row: {e}"}
    old_state = row["state"]

    try:
        ok = check_fn()
    except Exception:
        ok = False

    if ok:
        new_state = "healthy"
        updates = {
            "state": new_state,
            "failure_count": 0,
            "last_success_at": now,
            "opened_at": None,
            "metadata": {},
        }
        alert = old_state != "healthy"
    else:
        failure_count = row["failure_count"] + 1
        updates = {"failure_count": failure_count, "last_failure_at": now}
        alert = False

        if failure_count == 1:
            new_state = "warning"
            alert = old_state != "warning"
        elif old_state in ("healthy", "warning"):
            new_state = "open_circuit"
            updates["opened_at"] = now
            alert = True
        elif old_state == "open_circuit" and auto_restart_permitted and restart_fn is not None:
            try:
                restart_fn()
            except Exception as e:
                updates["metadata"] = {**(row.get("metadata") or {}), "restart_error": str(e)}
            new_state = "recovery_test"
            alert = True
        else:
            # Either a restart was already attempted this incident and
            # still failing (recovery_test -> fallback), or this
            # service is never auto-restarted (open_circuit -> fallback
            # directly) -- either way, give up auto-recovery for now
            # and hold until it's next observed healthy.
            new_state = "fallback"
            alert = old_state != "fallback"

        updates["state"] = new_state

    write_error = None
    try:
        _write_row(service_name, updates)
    except Exception as e:
        write_error = str(e)

    if alert:
        try:
            _log_state_change(service_name, old_state, new_state)
        except Exception:
            pass

    result = {"service": service_name, "old_state": old_state, "new_state": new_state, "alert": alert}
    if write_error:
        result["error"] = f"state computed but could not be written: {write_error}"
    return result


def run_health_check_sweep(notify: bool = True) -> dict:
    """Live entry point -- checks every known service, updates
    circuit_breakers, and sends one Telegram message summarizing any
    state changes AND any service that couldn't be checked/recorded at
    all (never one message per service -- avoids alert spam when
    several services flip at once, e.g. after a machine reboot). A
    database-layer error on one service is surfaced here, not just
    left in the JSON response -- this is what a sweep actually running
    but silently failing to record something would look like, and it
    should never go unnoticed."""
    results = [check_and_update(name) for name in _service_registry()]
    changed = [r for r in results if r.get("alert")]
    errored = [r for r in results if r.get("error")]

    if notify and (changed or errored):
        from agents.systems._telegram import send_telegram

        lines = ["[Systems & Automation -- circuit breaker state change]"]
        for r in changed:
            lines.append(f"{r['service']}: {r['old_state']} -> {r['new_state']}")
        if errored:
            lines.append("")
            lines.append("Could not fully check/record (needs a look):")
            for r in errored:
                lines.append(f"{r['service']}: {r['error']}")
        send_telegram("\n".join(lines), token_env="TELEGRAM_SYSTEMS_BOT_TOKEN")

    return {"checked": len(results), "changed": changed, "errored": errored}
