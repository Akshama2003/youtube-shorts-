# One-time setup for Windows PowerShell
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python 3.10+ not found. Install it with:  winget install Python.Python.3.12" -ForegroundColor Red
    Write-Host "Then close and reopen PowerShell and run this script again."
    exit 1
}

if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "Installing FFmpeg..." -ForegroundColor Yellow
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    Write-Host "FFmpeg installed. CLOSE and REOPEN PowerShell, then run setup.ps1 once more." -ForegroundColor Yellow
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env - open it with 'notepad .env' and add your API keys." -ForegroundColor Green
}

Write-Host "Setup finished. Next: notepad .env  then  .\.venv\Scripts\python.exe main.py doctor" -ForegroundColor Green
