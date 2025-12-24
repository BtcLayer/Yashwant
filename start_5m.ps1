$ErrorActionPreference = "Stop"
Set-Location C:\Users\yashw\MetaStackerBandit
& .\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "C:\Users\yashw\MetaStackerBandit"
Write-Host "Starting 5m bot..." -ForegroundColor Cyan
& python live_demo\main.py
