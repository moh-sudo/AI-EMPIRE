"""Minimal HTTP wrapper around the Reliability & Monitoring Agent so
n8n's HTTP Request node can trigger it (this n8n installation has no
shell/command-execution node available -- it explicitly points to
HTTP Request instead).
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agents.systems.ci_health_monitor import run_ci_health_sweep
from agents.systems.host_security_scan import run_host_security_sweep
from agents.systems.reliability_monitor import run_health_check_sweep
from agents.systems.resource_monitor import run_resource_check
from agents.systems.telegram_listener import check_for_systems_requests
from shared.systems_db_connector import get_empire_status

app = FastAPI(title="Systems & Automation Division")

WEB_DIR = Path(__file__).resolve().parent.parent.parent / "interfaces" / "web"

# Serves the Empire Brain's ES module tree (BrainFormationEngine,
# NeuralParticleSystem, etc.) at /web/js/*.js -- the page's own
# <script type="module"> imports resolve against this same origin, so no
# CORS is needed here either, matching /brain and /empire-status below.
app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")


@app.middleware("http")
async def no_cache_for_brain_assets(request, call_next):
    """Real bug found live: a browser can keep serving a STALE cached copy
    of an ES module (e.g. EmpireBrain.js) even after a hard reload of the
    /brain page itself, because the module is fetched by its own fixed
    URL and browsers cache module scripts aggressively -- confirmed
    directly (window.empireBrain was missing a field just added to the
    source, on a freshly-created tab hitting a cache-busted /brain URL).
    Query-string cache-busting on the PAGE doesn't help because the
    <script type="module" src="..."> import specifiers inside it are
    plain fixed paths. This forces revalidation on every request under
    /brain and /web/ instead, so both this session's testing and
    Mohamed's own reloads always see current code -- fine to pay the
    cost of skipping the disk cache for a low-traffic personal tool."""
    response = await call_next(request)
    if request.url.path in ("/brain", "/brain-anatomy") or request.url.path.startswith("/web/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/brain")
def brain_page():
    """Serves the Empire Brain idle-state display -- the first real
    slice of AI_EMPIRE's visual presence, decided 2026-08-22. Same-origin
    with /empire-status below on purpose (no CORS needed): open
    http://127.0.0.1:8007/brain in a browser tab and it's a genuinely
    persistent local page, not a one-off artifact link."""
    return FileResponse(WEB_DIR / "empire_brain_idle.html")


@app.get("/brain-anatomy")
def brain_anatomy_page():
    """Milestone 1 of the Empire Brain rebuild (2026-08-25): validates
    the real anatomical base mesh (NIH 3D / UCSF-UCSD glassbrain public
    domain hemisphere data, see interfaces/web/assets/brain/) alone,
    with nothing else -- no particles, color, pedestal, or dashboard UI.
    Deliberately a separate page from /brain, not a replacement, until
    Mohamed approves this foundation."""
    return FileResponse(WEB_DIR / "brain_anatomy.html")


@app.get("/empire-status")
def empire_status():
    """Real, live data for the Empire Brain display -- see
    shared/systems_db_connector.get_empire_status() for exactly what's
    real vs. not yet wired."""
    return get_empire_status()


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
