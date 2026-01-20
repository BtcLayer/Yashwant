# Script to create a zip of logs and emitters for each model/timeframe
# Date: 2026-01-07

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$zipName = "MetaStackerBandit_logs_emitters_$timestamp.zip"
$tempDir = "temp_logs_emitters"

Write-Host "Creating logs and emitters archive..." -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Clean up temp directory if exists
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Define the timeframe directories
$timeframeDirs = @(
    "live_demo",      # 5m
    "live_demo_1h",   # 1h
    "live_demo_12h",  # 12h
    "live_demo_24h"   # 24h
)

$totalFiles = 0
$totalSize = 0

# Copy emitters from each timeframe directory
Write-Host "Copying emitters from each timeframe..." -ForegroundColor Yellow
foreach ($dir in $timeframeDirs) {
    if (Test-Path $dir) {
        $emittersPath = Join-Path $dir "emitters"
        if (Test-Path $emittersPath) {
            $destPath = Join-Path $tempDir "$dir\emitters"
            New-Item -ItemType Directory -Path $destPath -Force | Out-Null
            
            $files = Get-ChildItem -Path $emittersPath -File -Recurse
            $fileCount = $files.Count
            $dirSize = ($files | Measure-Object -Property Length -Sum).Sum
            
            if ($fileCount -gt 0) {
                Copy-Item -Path "$emittersPath\*" -Destination $destPath -Recurse -Force
                Write-Host "  + $dir\emitters" -ForegroundColor Gray
                Write-Host "    Files: $fileCount | Size: $([math]::Round($dirSize/1KB, 2)) KB" -ForegroundColor DarkGray
                
                $totalFiles += $fileCount
                $totalSize += $dirSize
            } else {
                Write-Host "  - $dir\emitters (empty)" -ForegroundColor DarkGray
            }
        } else {
            Write-Host "  - $dir\emitters (not found)" -ForegroundColor DarkGray
        }
    }
}

# Copy main logs directory
Write-Host "`nCopying main logs directory..." -ForegroundColor Yellow
if (Test-Path "logs") {
    $logsDestPath = Join-Path $tempDir "logs"
    New-Item -ItemType Directory -Path $logsDestPath -Force | Out-Null
    
    $logFiles = Get-ChildItem -Path "logs" -File -Recurse
    $logCount = $logFiles.Count
    $logSize = ($logFiles | Measure-Object -Property Length -Sum).Sum
    
    if ($logCount -gt 0) {
        Copy-Item -Path "logs\*" -Destination $logsDestPath -Recurse -Force
        Write-Host "  + logs" -ForegroundColor Gray
        Write-Host "    Files: $logCount | Size: $([math]::Round($logSize/1KB, 2)) KB" -ForegroundColor DarkGray
        
        $totalFiles += $logCount
        $totalSize += $logSize
    } else {
        Write-Host "  - logs (empty)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "  - logs (not found)" -ForegroundColor DarkGray
}

# Copy paper_trading_outputs if exists
Write-Host "`nCopying paper trading outputs..." -ForegroundColor Yellow
if (Test-Path "paper_trading_outputs") {
    $paperDestPath = Join-Path $tempDir "paper_trading_outputs"
    New-Item -ItemType Directory -Path $paperDestPath -Force | Out-Null
    
    # Only copy CSV and JSON files, not large data files
    $paperFiles = Get-ChildItem -Path "paper_trading_outputs" -Include "*.csv","*.json","*.jsonl" -Recurse
    $paperCount = $paperFiles.Count
    
    if ($paperCount -gt 0) {
        foreach ($file in $paperFiles) {
            $relativePath = $file.FullName.Substring((Get-Location).Path.Length + 1)
            $destFile = Join-Path $tempDir $relativePath
            $destFolder = Split-Path $destFile -Parent
            
            if (-not (Test-Path $destFolder)) {
                New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
            }
            
            Copy-Item $file.FullName -Destination $destFile -Force
        }
        
        $paperSize = ($paperFiles | Measure-Object -Property Length -Sum).Sum
        Write-Host "  + paper_trading_outputs" -ForegroundColor Gray
        Write-Host "    Files: $paperCount | Size: $([math]::Round($paperSize/1KB, 2)) KB" -ForegroundColor DarkGray
        
        $totalFiles += $paperCount
        $totalSize += $paperSize
    } else {
        Write-Host "  - paper_trading_outputs (no CSV/JSON files)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "  - paper_trading_outputs (not found)" -ForegroundColor DarkGray
}

# Copy root-level log files
Write-Host "`nCopying root-level log files..." -ForegroundColor Yellow
$rootLogs = Get-ChildItem -Path . -Filter "*.log" -File
if ($rootLogs.Count -gt 0) {
    foreach ($logFile in $rootLogs) {
        Copy-Item $logFile.FullName -Destination $tempDir -Force
        Write-Host "  + $($logFile.Name)" -ForegroundColor Gray
    }
    $rootLogSize = ($rootLogs | Measure-Object -Property Length -Sum).Sum
    Write-Host "    Files: $($rootLogs.Count) | Size: $([math]::Round($rootLogSize/1KB, 2)) KB" -ForegroundColor DarkGray
    
    $totalFiles += $rootLogs.Count
    $totalSize += $rootLogSize
} else {
    Write-Host "  - No root-level log files found" -ForegroundColor DarkGray
}

Write-Host "`nCreating zip archive: $zipName" -ForegroundColor Green

# Create zip file
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipName -Force

# Clean up temp directory
Remove-Item -Recurse -Force $tempDir

# Get final zip size
$zipSize = (Get-Item $zipName).Length / 1KB

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "SUCCESS!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Archive: $zipName" -ForegroundColor White
Write-Host "Total Files: $totalFiles" -ForegroundColor White
Write-Host "Uncompressed Size: $([math]::Round($totalSize/1KB, 2)) KB" -ForegroundColor White
Write-Host "Compressed Size: $([math]::Round($zipSize, 2)) KB" -ForegroundColor White
Write-Host "`nContents:" -ForegroundColor Yellow
Write-Host "  + Emitters from all timeframes (5m, 1h, 12h, 24h)" -ForegroundColor Gray
Write-Host "  + Main logs directory" -ForegroundColor Gray
Write-Host "  + Paper trading outputs (CSV/JSON only)" -ForegroundColor Gray
Write-Host "  + Root-level log files" -ForegroundColor Gray
Write-Host "========================================`n" -ForegroundColor Green
