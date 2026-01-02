# Script to create logs and emitters archive
# Date: 2026-01-02

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$zipName = "MetaStackerBandit_logs_emitters_$timestamp.zip"
$tempDir = "temp_logs_export"

Write-Host "Creating logs and emitters archive..." -ForegroundColor Green
Write-Host ""

# Create temporary directory
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Create subdirectories
New-Item -ItemType Directory -Path "$tempDir\logs" -Force | Out-Null
New-Item -ItemType Directory -Path "$tempDir\paper_trading_outputs" -Force | Out-Null
New-Item -ItemType Directory -Path "$tempDir\emitters_code" -Force | Out-Null

Write-Host "Analyzing data dates..." -ForegroundColor Yellow

# Function to get date range from CSV files
function Get-DateRange {
    param($path)
    
    if (Test-Path $path) {
        $files = Get-ChildItem -Path $path -File -Recurse -Include *.csv,*.json,*.jsonl,*.log
        if ($files.Count -gt 0) {
            $oldest = ($files | Sort-Object LastWriteTime | Select-Object -First 1).LastWriteTime
            $newest = ($files | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
            return @{
                Oldest = $oldest
                Newest = $newest
                Count = $files.Count
            }
        }
    }
    return $null
}

# Analyze each timeframe
Write-Host ""
Write-Host "Data Summary:" -ForegroundColor Cyan
Write-Host "=============" -ForegroundColor Cyan

$timeframes = @("5m", "1h", "12h", "24h")
foreach ($tf in $timeframes) {
    $path = "paper_trading_outputs\$tf"
    $info = Get-DateRange $path
    if ($info) {
        Write-Host "$tf Timeframe:" -ForegroundColor White
        Write-Host "  Files: $($info.Count)" -ForegroundColor Gray
        Write-Host "  Oldest: $($info.Oldest.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
        Write-Host "  Newest: $($info.Newest.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
    } else {
        Write-Host "$tf Timeframe: No data" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "Copying files..." -ForegroundColor Yellow

# Copy logs directory
Write-Host "  Copying logs..." -ForegroundColor Cyan
if (Test-Path "logs") {
    Copy-Item -Path "logs\*" -Destination "$tempDir\logs" -Recurse -Force
    $logCount = (Get-ChildItem "$tempDir\logs" -File -Recurse).Count
    Write-Host "    Copied $logCount log files" -ForegroundColor Gray
}

# Copy paper_trading_outputs
Write-Host "  Copying paper trading outputs..." -ForegroundColor Cyan
if (Test-Path "paper_trading_outputs") {
    # Copy all subdirectories and files
    Get-ChildItem -Path "paper_trading_outputs" -Directory | ForEach-Object {
        $destPath = Join-Path "$tempDir\paper_trading_outputs" $_.Name
        New-Item -ItemType Directory -Path $destPath -Force | Out-Null
        Copy-Item -Path "$($_.FullName)\*" -Destination $destPath -Recurse -Force -ErrorAction SilentlyContinue
        
        $fileCount = (Get-ChildItem $destPath -File -Recurse).Count
        Write-Host "    Copied $fileCount files from $($_.Name)" -ForegroundColor Gray
    }
    
    # Copy root level files
    Get-ChildItem -Path "paper_trading_outputs" -File | ForEach-Object {
        Copy-Item $_.FullName -Destination "$tempDir\paper_trading_outputs" -Force
    }
}

# Copy emitter source code from each timeframe
Write-Host "  Copying emitter source code..." -ForegroundColor Cyan
$emitterDirs = @(
    "live_demo\emitters",
    "live_demo_1h\emitters",
    "live_demo_12h\emitters",
    "live_demo_24h\emitters"
)

foreach ($emitterDir in $emitterDirs) {
    if (Test-Path $emitterDir) {
        $tfName = Split-Path (Split-Path $emitterDir -Parent) -Leaf
        $destPath = Join-Path "$tempDir\emitters_code" $tfName
        New-Item -ItemType Directory -Path $destPath -Force | Out-Null
        
        Get-ChildItem -Path $emitterDir -File -Include *.py | ForEach-Object {
            Copy-Item $_.FullName -Destination $destPath -Force
            Write-Host "    Copied $tfName/$($_.Name)" -ForegroundColor DarkGray
        }
    }
}

# Copy root level log files
Write-Host "  Copying root level logs..." -ForegroundColor Cyan
Get-ChildItem -Path . -File -Include *.log | ForEach-Object {
    Copy-Item $_.FullName -Destination "$tempDir\logs" -Force
    Write-Host "    Copied $($_.Name)" -ForegroundColor DarkGray
}

# Create a summary file
$summaryContent = @"
# MetaStackerBandit Logs and Emitters Archive
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

## Data Date Ranges

"@

foreach ($tf in $timeframes) {
    $path = "paper_trading_outputs\$tf"
    $info = Get-DateRange $path
    if ($info) {
        $summaryContent += @"

### $tf Timeframe
- Files: $($info.Count)
- Date Range: $($info.Oldest.ToString('yyyy-MM-dd')) to $($info.Newest.ToString('yyyy-MM-dd'))
- Latest Update: $($info.Newest.ToString('yyyy-MM-dd HH:mm:ss'))
"@
    }
}

$summaryContent += @"


## Contents

### logs/
System logs from all timeframes including:
- 5m.log, 1h.log, 12h.log, 24h.log
- Error logs (*_err.log)
- Output logs (*_out.log)
- Startup logs

### paper_trading_outputs/
Trading data organized by timeframe:
- 5m/ - 5-minute timeframe data (MOST RECENT: Jan 2, 2026)
- 1h/ - 1-hour timeframe data (Last: Dec 30, 2025)
- 12h/ - 12-hour timeframe data (Last: Dec 29, 2025)
- 24h/ - 24-hour timeframe data (Last: Dec 23, 2025)

Each timeframe contains:
- signals.csv - Trading signals
- equity.csv - Equity tracking
- bandit.csv - Bandit algorithm data
- hyperliquid_sheet.csv - Exchange data
- mood_debug.csv - Market mood analysis
- And other CSV/JSON files

### emitters_code/
Source code for data emitters from each timeframe:
- live_demo/ - 5m emitters
- live_demo_1h/ - 1h emitters
- live_demo_12h/ - 12h emitters
- live_demo_24h/ - 24h emitters

## Notes

- The 5m timeframe has the most recent data (Jan 2, 2026 14:05)
- This indicates the 5m bot is currently running
- Other timeframes have older data suggesting they may not be actively running
- All emitter source code is included for reference
"@

Set-Content -Path "$tempDir\ARCHIVE_INFO.md" -Value $summaryContent

Write-Host ""
Write-Host "Creating zip archive: $zipName" -ForegroundColor Green

# Create zip file
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipName -Force

# Clean up temp directory
Remove-Item -Recurse -Force $tempDir

# Get file size
$zipSize = (Get-Item $zipName).Length / 1MB

Write-Host ""
Write-Host "Success!" -ForegroundColor Green
Write-Host "Archive created: $zipName" -ForegroundColor White
Write-Host "Size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor White
Write-Host ""
Write-Host "Archive contains:" -ForegroundColor Yellow
Write-Host "  - System logs" -ForegroundColor Gray
Write-Host "  - Paper trading outputs (all timeframes)" -ForegroundColor Gray
Write-Host "  - Emitter source code" -ForegroundColor Gray
Write-Host "  - Data summary (ARCHIVE_INFO.md)" -ForegroundColor Gray
