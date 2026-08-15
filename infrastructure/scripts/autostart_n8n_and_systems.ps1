# Auto-starts n8n and the Systems & Automation server on login.
# Registered as a per-user Scheduled Task ("At log on" trigger) --
# see infrastructure/scripts/register_autostart.ps1. Addresses the
# "nothing persists across a machine restart" gap noted in
# ARCHITECTURE.md's Known Gaps, for these two services specifically
# (n8n, so scheduled workflows like systems-host-security-scan-scheduled
# can actually fire; the Systems & Automation server, so n8n's HTTP
# Request nodes have something to hit).

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
