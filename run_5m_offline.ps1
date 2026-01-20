# Run 5m bot in OFFLINE mode for testing/log generation
# This will generate logs and emitters without connecting to exchange

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Starting 5m Bot in OFFLINE Mode" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Set environment variables for offline mode
$env:LIVE_DEMO_OFFLINE = "1"
$env:LIVE_DEMO_ONE_SHOT = "1"  # Run once then exit

Write-Host "Environment:" -ForegroundColor Yellow
Write-Host "  OFFLINE MODE: Enabled" -ForegroundColor Cyan
Write-Host "  ONE SHOT: Enabled (will run once and exit)" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Run the 5m bot
Write-Host "`nStarting 5m bot..." -ForegroundColor Yellow
Write-Host "Location: live_demo/main.py" -ForegroundColor Gray
Write-Host "Config: live_demo/config.json`n" -ForegroundColor Gray

python -m live_demo.main

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "5m Bot Run Complete" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Check the following directories for outputs:" -ForegroundColor Yellow
Write-Host "  - live_demo/logs/ (if created)" -ForegroundColor Gray
Write-Host "  - live_demo/emitters/ (if created)" -ForegroundColor Gray
Write-Host "  - paper_trading_outputs/5m/logs/" -ForegroundColor Gray
Write-Host "  - paper_trading_outputs/5m/emitters/`n" -ForegroundColor Gray
