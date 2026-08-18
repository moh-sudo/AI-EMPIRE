# Auto-starts n8n and the Systems & Automation server on login, and
# triggers one host-security-scan per real login session. Registered
# as a per-user Scheduled Task ("At log on" trigger) -- see
# infrastructure/scripts/register_autostart.ps1. Addresses the
# "nothing persists across a machine restart" gap noted in
# ARCHITECTURE.md's Known Gaps, for these services specifically (n8n,
# for its own scheduled workflows like systems-ci-health-check-scheduled;
# the Systems & Automation server, so n8n's HTTP Request nodes have
# something to hit; host-security-scan, triggered directly here rather
# than via an n8n daily schedule -- see the login-trigger block below
# for why).

$repoRoot = "C:\moh-sudo"
$logDir = "$env:TEMP\ai_empire_autostart"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# Found live 2026-08-15: a Startup-folder script can fire before the
# user profile / filesystem is fully settled right after login --
# n8n crashed with "Cannot find module ...\n8n\bin\n8n" (MODULE_NOT_FOUND)
# at login, even though the exact same command, run moments later by
# hand, worked correctly and the file was genuinely present the whole
# time. A short delay up front, plus one retry specifically for n8n if
# that exact failure signature shows up, works around the race without
# masking a real, persistent failure -- matches this division's "one
# remediation attempt" precedent (e.g. host_security_scan.py's WSL2
# retry, Rule 4's "one restart attempt per incident").
Start-Sleep -Seconds 15

# Calls node.exe directly on n8n's actual entry script rather than the
# n8n.cmd shim -- the shim nests through cmd.exe (title/PATHEXT setup)
# before reaching node, which was found live 2026-08-13 to silently
# break Start-Process's stdout/stderr redirection under -WindowStyle
# Hidden (node processes did spawn, confirmed via Get-Process, but
# produced zero bytes in the redirected log files every time).
$n8nExe = "C:\Program Files\nodejs\node.exe"
$n8nScript = "$env:APPDATA\npm\node_modules\n8n\bin\n8n"
$n8nOutLog = "$logDir\n8n.log"
$n8nErrLog = "$logDir\n8n_err.log"

function Start-N8nProcess {
    Remove-Item -Force -ErrorAction SilentlyContinue $n8nOutLog, $n8nErrLog
    Start-Process -FilePath $n8nExe `
        -ArgumentList "`"$n8nScript`"", "start" `
        -WindowStyle Hidden `
        -RedirectStandardOutput $n8nOutLog `
        -RedirectStandardError $n8nErrLog
}

Start-N8nProcess
Start-Sleep -Seconds 5
if ((Test-Path $n8nErrLog) -and (Select-String -Path $n8nErrLog -Pattern "MODULE_NOT_FOUND" -Quiet)) {
    Start-Sleep -Seconds 10
    Start-N8nProcess
}

Start-Process -FilePath "$repoRoot\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "agents.systems.server:app", "--port", "8007", "--host", "127.0.0.1" `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput "$logDir\systems_server.log" `
    -RedirectStandardError "$logDir\systems_server_err.log"

# Trigger one host-security-scan per real login session, instead of a
# fixed n8n daily clock-time schedule. Found live 2026-08-18, checking
# n8n's own execution_entity table: the daily 06:00 EAT trigger had
# NEVER once fired automatically across 3 days (zero mode='trigger'
# rows for that workflow, only our own manual test runs) -- n8n only
# fires a scheduled trigger if it's actually running at that exact
# moment, it doesn't catch up on missed ones, and this laptop simply
# isn't reliably on and logged in at 6am. Firing once per login is
# deterministic instead of probabilistic. Replaces
# infrastructure/n8n/systems-host-security-scan-scheduled.json, which
# Mohamed removed from n8n -- the file is deleted from the repo too,
# so Architecture Assurance's drift detector has nothing stale to flag.
Start-Sleep -Seconds 10
try {
    $scanResult = Invoke-RestMethod -Uri "http://127.0.0.1:8007/host-security-scan" -Method Post -TimeoutSec 60
    $scanResult | ConvertTo-Json -Compress | Out-File -FilePath "$logDir\host_security_scan_login_trigger.log" -Encoding utf8
} catch {
    "Failed to trigger host-security-scan at login: $_" | Out-File -FilePath "$logDir\host_security_scan_login_trigger.log" -Encoding utf8
}
