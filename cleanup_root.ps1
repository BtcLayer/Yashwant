# TASK-10: Root Directory Cleanup Script
# Organizes 430+ files into logical folders

Write-Host "Starting root directory cleanup..." -ForegroundColor Cyan

# Move markdown reports to archive/reports
Write-Host "`nMoving markdown reports..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "*.md" -File | Where-Object { 
    $_.Name -notmatch "^README" 
} | ForEach-Object {
    Move-Item $_.FullName -Destination "archive\reports\" -Force
    Write-Host "  Moved: $($_.Name)"
}

# Move log files to archive/logs
Write-Host "`nMoving log files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "*.log" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "archive\logs\" -Force
    Write-Host "  Moved: $($_.Name)"
}

# Move zip/tar/rar files to archive/zips
Write-Host "`nMoving archive files..." -ForegroundColor Yellow
Get-ChildItem -Path . -File | Where-Object { 
    $_.Extension -match "\.(zip|tar|gz|rar|bundle)$" 
} | ForEach-Object {
    Move-Item $_.FullName -Destination "archive\zips\" -Force
    Write-Host "  Moved: $($_.Name)"
}

# Move analysis scripts
Write-Host "`nMoving analysis scripts..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "analyze_*.py" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\analysis\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "investigate_*.py" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\analysis\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "diagnose_*.py" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\analysis\" -Force
    Write-Host "  Moved: $($_.Name)"
}

# Move monitoring scripts
Write-Host "`nMoving monitoring scripts..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "monitor_*.py" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\monitoring\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "check_*.py" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\monitoring\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "status_*.py" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\monitoring\" -Force
    Write-Host "  Moved: $($_.Name)"
}

# Move verification scripts
Write-Host "`nMoving verification scripts..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "verify_*.py" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\verification\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "validate_*.py" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\verification\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "test_*.py" -File | Where-Object {
    $_.Name -notmatch "^test_models"
} | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\verification\" -Force
    Write-Host "  Moved: $($_.Name)"
}

# Move deployment scripts
Write-Host "`nMoving deployment scripts..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "deploy_*.ps1" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\deployment\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "deploy_*.sh" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\deployment\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "vm_*.sh" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\deployment\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "create_*.ps1" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "scripts\deployment\" -Force
    Write-Host "  Moved: $($_.Name)"
}

# Move txt output files to archive/logs
Write-Host "`nMoving text output files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "*_output.txt" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "archive\logs\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "*_report.txt" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "archive\logs\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "*_results.txt" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "archive\logs\" -Force
    Write-Host "  Moved: $($_.Name)"
}

# Move JSON result files to archive/logs
Write-Host "`nMoving JSON result files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Filter "*_results.json" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "archive\logs\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Get-ChildItem -Path . -Filter "*_analysis.json" -File | ForEach-Object {
    Move-Item $_.FullName -Destination "archive\logs\" -Force
    Write-Host "  Moved: $($_.Name)"
}

Write-Host "`nCleanup complete!" -ForegroundColor Green
Write-Host "`nSummary:" -ForegroundColor Cyan
Write-Host "  Reports:      archive\reports\"
Write-Host "  Logs:         archive\logs\"
Write-Host "  Archives:     archive\zips\"
Write-Host "  Analysis:     scripts\analysis\"
Write-Host "  Monitoring:   scripts\monitoring\"
Write-Host "  Verification: scripts\verification\"
Write-Host "  Deployment:   scripts\deployment\"
