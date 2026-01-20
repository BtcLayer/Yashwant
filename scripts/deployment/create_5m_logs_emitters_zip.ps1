# Script to create a zip of ONLY 5m bot (live_demo) logs and emitters
# Date: 2026-01-14

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$zipName = "5m_logs_emitters_$timestamp.zip"
$tempDir = "temp_5m_logs_emitters"

Write-Host "Creating 5m bot logs and emitters archive..." -ForegroundColor Green

# Clean up temp directory if exists
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Check if live_demo directory exists
if (-not (Test-Path "live_demo")) {
    Write-Host "ERROR: live_demo directory not found!" -ForegroundColor Red
    exit 1
}

# Create subdirectories in temp
$logsDir = Join-Path $tempDir "logs"
$emittersDir = Join-Path $tempDir "emitters"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
New-Item -ItemType Directory -Path $emittersDir -Force | Out-Null

Write-Host "`nCopying logs from live_demo/logs..." -ForegroundColor Yellow

# Copy logs directory if exists
if (Test-Path "live_demo\logs") {
    $logFiles = Get-ChildItem -Path "live_demo\logs" -File -Recurse
    $logCount = 0
    
    foreach ($file in $logFiles) {
        $relativePath = $file.FullName.Substring((Get-Item "live_demo\logs").FullName.Length + 1)
        $destPath = Join-Path $logsDir $relativePath
        $destFolder = Split-Path $destPath -Parent
        
        if (-not (Test-Path $destFolder)) {
            New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
        }
        
        Copy-Item $file.FullName -Destination $destPath
        Write-Host "  + logs\$relativePath" -ForegroundColor Gray
        $logCount++
    }
    
    Write-Host "Copied $logCount log files" -ForegroundColor Cyan
} else {
    Write-Host "  No logs directory found in live_demo" -ForegroundColor Yellow
}

Write-Host "`nCopying emitters from live_demo/emitters..." -ForegroundColor Yellow

# Copy emitters directory if exists
if (Test-Path "live_demo\emitters") {
    $emitterFiles = Get-ChildItem -Path "live_demo\emitters" -File -Recurse
    $emitterCount = 0
    
    foreach ($file in $emitterFiles) {
        $relativePath = $file.FullName.Substring((Get-Item "live_demo\emitters").FullName.Length + 1)
        $destPath = Join-Path $emittersDir $relativePath
        $destFolder = Split-Path $destPath -Parent
        
        if (-not (Test-Path $destFolder)) {
            New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
        }
        
        Copy-Item $file.FullName -Destination $destPath
        Write-Host "  + emitters\$relativePath" -ForegroundColor Gray
        $emitterCount++
    }
    
    Write-Host "Copied $emitterCount emitter files" -ForegroundColor Cyan
} else {
    Write-Host "  No emitters directory found in live_demo" -ForegroundColor Yellow
}

Write-Host "`nCreating zip archive: $zipName" -ForegroundColor Green

# Create zip file
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipName -Force

# Clean up temp directory
Remove-Item -Recurse -Force $tempDir

# Get file size
$zipSize = (Get-Item $zipName).Length
$zipSizeKB = [math]::Round($zipSize / 1KB, 2)
$zipSizeMB = [math]::Round($zipSize / 1MB, 2)

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "SUCCESS!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Archive: $zipName" -ForegroundColor White

if ($zipSizeMB -gt 1) {
    Write-Host "Size: $zipSizeMB MB" -ForegroundColor White
} else {
    Write-Host "Size: $zipSizeKB KB" -ForegroundColor White
}

Write-Host "`nContents:" -ForegroundColor Yellow
Write-Host "  + logs/ - All log files from live_demo/logs" -ForegroundColor Gray
Write-Host "  + emitters/ - All emitter files from live_demo/emitters" -ForegroundColor Gray
Write-Host "`nThis archive contains ONLY 5m bot (live_demo) logs and emitters" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Green
