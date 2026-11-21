# Creates a Windows Scheduled Task that runs the studio every day.
#   .\scripts\schedule.ps1 -Time "18:00" -Count 1
# Remove later with:  Unregister-ScheduledTask -TaskName YTShortsStudio -Confirm:$false
param(
    [string]$Time = "18:00",
    [int]$Count = 1
)
$root = Split-Path $PSScriptRoot -Parent
$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$root\scripts\run.ps1`" -Count $Count"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
Register-ScheduledTask -TaskName "YTShortsStudio" -Action $action -Trigger $trigger -Description "Daily AI Shorts studio" -Force
Write-Host "Scheduled daily at $Time ($Count video/day). The PC must be on and you must be logged in." -ForegroundColor Green
