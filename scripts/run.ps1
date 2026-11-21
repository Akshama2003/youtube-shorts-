# Usage examples:
#   .\scripts\run.ps1                       -> 1 video, auto publish (if QA passes)
#   .\scripts\run.ps1 -Count 3              -> 3 videos
#   .\scripts\run.ps1 -NoPublish            -> make + QA only
#   .\scripts\run.ps1 -Topic "Why is the sky blue"
param(
    [int]$Count = 1,
    [string]$Topic = "",
    [switch]$NoPublish
)
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".\.venv\Scripts\python.exe"
$cliArgs = @("main.py", "run", "--count", $Count)
if ($Topic) { $cliArgs += @("--topic", $Topic) }
if ($NoPublish) { $cliArgs += "--no-publish" }
& $py @cliArgs
