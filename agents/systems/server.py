"""Minimal HTTP wrapper around the Reliability & Monitoring Agent so
n8n's HTTP Request node can trigger it (this n8n installation has no
shell/command-execution node available -- it explicitly points to
HTTP Request instead).
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from agents.systems.ci_health_monitor import run_ci_health_sweep
from agents.systems.host_security_scan import run_host_security_sweep
from agents.systems.reliability_monitor import run_health_check_sweep
from agents.systems.resource_monitor import run_resource_check
from agents.systems.telegram_listener import check_for_systems_requests

app = FastAPI(title="Systems & Automation Division")


@app.post("/health-check")
def health_check():
    return run_health_check_sweep(notify=True)


@app.post("/check-telegram")
def check_telegram():
    return check_for_systems_requests()


@app.post("/host-security-scan")
def host_security_scan():
    """Triggered once per login by infrastructure/scripts/autostart_n8n_and_systems.ps1
    -- NOT an n8n schedule. Found live 2026-08-18 that the original
    daily 06:00 EAT n8n trigger had never once fired automatically in
    3 real days (confirmed via n8n's own execution_entity table: zero
    mode='trigger' rows), because this laptop isn't reliably on and
    logged in at that exact hour and n8n doesn't catch up on missed
    schedules. Firing once per login is deterministic instead of
    probabilistic. Port scan (nmap) only -- no malware_scan_path. A
    live test found clamscan over the real Downloads folder via
    WSL2's /mnt/c/ bridge doesn't finish within the 600s subprocess
    timeout (a known WSL2 slow-filesystem-bridge characteristic, not
    a bug); Mohamed's call was to keep this to the fast,
    proven-reliable port scan and run clamscan on-demand for a
    specific path when wanted, rather than guess a timeout long
    enough to cover an unknown real duration."""
    return run_host_security_sweep()


@app.post("/ci-health-check")
def ci_health_check():
    """5-minute scheduled trigger (infrastructure/n8n/systems-ci-health-check-scheduled.json),
    matching Reliability & Monitoring's own cadence -- a lightweight
    GitHub API poll, not a heavy scan like host-security-scan, so the
    same "cheap health check" interval applies."""
    return run_ci_health_sweep()


@app.post("/resource-check")
def resource_check():
    """5-minute scheduled trigger (infrastructure/n8n/systems-resource-check-scheduled.json),
    same cadence class as ci-health-check -- a few psutil calls plus
    one disk_usage() call, cheap enough to run this often."""
    return run_resource_check()
