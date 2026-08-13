# Registers the AI_EMPIRE_AutoStart Scheduled Task (per-user, "At log
# on" trigger). NOT the mechanism actually in use -- found live
# 2026-08-13 that Register-ScheduledTask returns "Access is denied"
# in this environment (no admin rights available). The real, working
# autostart mechanism is a per-user Startup-folder entry instead:
# %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ai_empire_autostart.vbs
# (a silent VBScript launcher, no admin rights needed), which is what
# actually runs autostart_n8n_and_systems.ps1 on login today. This
# script is kept for later, IF Mohamed ever runs it himself from an
# elevated/admin PowerShell session -- Task Scheduler is the more
# robust mechanism (survives Startup-folder cleanup tools, shows up
# in Task Scheduler's own UI) but needs that elevation this session
# didn't have. To remove the task if it's ever registered:
#   Unregister-ScheduledTask -TaskName "AI_EMPIRE_AutoStart" -Confirm:$false

$scriptPath = "C:\moh-sudo\infrastructure\scripts\autostart_n8n_and_systems.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask -TaskName "AI_EMPIRE_AutoStart" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Starts n8n and the Systems & Automation server (port 8007) on login for AI_EMPIRE." `
    -Force

Write-Output "Registered. Verify with: Get-ScheduledTask -TaskName 'AI_EMPIRE_AutoStart'"
