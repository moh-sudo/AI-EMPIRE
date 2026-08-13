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

# Calls node.exe directly on n8n's actual entry script rather than the
# n8n.cmd shim -- the shim nests through cmd.exe (title/PATHEXT setup)
# before reaching node, which was found live 2026-08-13 to silently
# break Start-Process's stdout/stderr redirection under -WindowStyle
# Hidden (node processes did spawn, confirmed via Get-Process, but
# produced zero bytes in the redirected log files every time).
Start-Process -FilePath "C:\Program Files\nodejs\node.exe" `
    -ArgumentList "`"$env:APPDATA\npm\node_modules\n8n\bin\n8n`"", "start" `
    -WindowStyle Hidden `
    -RedirectStandardOutput "$logDir\n8n.log" `
    -RedirectStandardError "$logDir\n8n_err.log"

Start-Process -FilePath "$repoRoot\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "agents.systems.server:app", "--port", "8007", "--host", "127.0.0.1" `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput "$logDir\systems_server.log" `
    -RedirectStandardError "$logDir\systems_server_err.log"
