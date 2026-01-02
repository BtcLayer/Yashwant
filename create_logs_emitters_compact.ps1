# Script to create a compact logs and emitters archive (under 30MB)
# Date: 2026-01-02
# Focus: Essential logs and recent data only

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$zipName = "MetaStackerBandit_logs_emitters_compact_$timestamp.zip"
$tempDir = "temp_logs_compact"

Write-Host "Creating compact logs and emitters archive (target: <30MB)..." -ForegroundColor Green
Write-Host ""

# Create temporary directory
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Create subdirectories
New-Item -ItemType Directory -Path "$tempDir\logs" -Force | Out-Null
New-Item -ItemType Directory -Path "$tempDir\paper_trading_outputs\5m" -Force | Out-Null
New-Item -ItemType Directory -Path "$tempDir\emitters_code" -Force | Out-Null

Write-Host "Strategy: Include only essential and recent data" -ForegroundColor Yellow
Write-Host "  - System logs (small files)" -ForegroundColor Gray
Write-Host "  - 5m trading data (most recent, excluding large files)" -ForegroundColor Gray
Write-Host "  - Emitter source code" -ForegroundColor Gray
Write-Host "  - Exclude: Large CSV files, old timeframes, compressed archives" -ForegroundColor Gray
Write-Host ""

# Files to EXCLUDE (too large or unnecessary)
$excludeFiles = @(
    "hyperliquid_sheet.csv",
    "hyperliquid_sheet_*.csv",
    "*.jsonl.gz",
    "*.jsonl",
    "funding_debug.json"
)

# Copy system logs (small files)
Write-Host "Copying system logs..." -ForegroundColor Cyan
if (Test-Path "logs") {
    Get-ChildItem -Path "logs" -File | ForEach-Object {
        Copy-Item $_.FullName -Destination "$tempDir\logs" -Force
        $sizeKB = [math]::Round($_.Length/1KB, 2)
        Write-Host "  Copied: $($_.Name) ($sizeKB KB)" -ForegroundColor DarkGray
    }
}

# Copy root level log files (excluding very large ones)
Get-ChildItem -Path . -File -Include *.log | Where-Object {
    $_.Length -lt 10MB
} | ForEach-Object {
    Copy-Item $_.FullName -Destination "$tempDir\logs" -Force
    $sizeKB = [math]::Round($_.Length/1KB, 2)
    Write-Host "  Copied: $($_.Name) ($sizeKB KB)" -ForegroundColor DarkGray
}

# Copy 5m paper trading outputs (selective)
Write-Host ""
Write-Host "Copying 5m trading data (selective)..." -ForegroundColor Cyan

$importantFiles = @(
    "signals.csv",
    "equity.csv",
    "bandit.csv",
    "mood_debug.csv",
    "executions_paper.csv",
    "decisions.csv",
    "*.json"
)

if (Test-Path "paper_trading_outputs\5m") {
    foreach ($pattern in $importantFiles) {
        Get-ChildItem -Path "paper_trading_outputs\5m" -File -Filter $pattern -Recurse | Where-Object {
            $exclude = $false
            foreach ($excludePattern in $excludeFiles) {
                if ($_.Name -like $excludePattern) {
                    $exclude = $true
                    break
                }
            }
            -not $exclude -and $_.Length -lt 5MB
        } | ForEach-Object {
            $relativePath = $_.FullName.Substring((Get-Location).Path.Length + 1)
            $destPath = Join-Path $tempDir $relativePath
            $destFolder = Split-Path $destPath -Parent
            
            if (-not (Test-Path $destFolder)) {
                New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
            }
            
            Copy-Item $_.FullName -Destination $destPath -Force
            $sizeKB = [math]::Round($_.Length/1KB, 2)
            Write-Host "  Copied: $($_.Name) ($sizeKB KB)" -ForegroundColor DarkGray
        }
    }
}

# Copy emitter source code
Write-Host ""
Write-Host "Copying emitter source code..." -ForegroundColor Cyan

$emitterDirs = @(
    @{Path="live_demo\emitters"; Name="live_demo"},
    @{Path="live_demo_1h\emitters"; Name="live_demo_1h"},
    @{Path="live_demo_12h\emitters"; Name="live_demo_12h"},
    @{Path="live_demo_24h\emitters"; Name="live_demo_24h"}
)

foreach ($emitter in $emitterDirs) {
    if (Test-Path $emitter.Path) {
        $destPath = Join-Path "$tempDir\emitters_code" $emitter.Name
        New-Item -ItemType Directory -Path $destPath -Force | Out-Null
        
        Get-ChildItem -Path $emitter.Path -File -Include *.py | ForEach-Object {
            Copy-Item $_.FullName -Destination $destPath -Force
            Write-Host "  Copied: $($emitter.Name)/$($_.Name)" -ForegroundColor DarkGray
        }
    }
}

# Copy recent unified runner logs
Write-Host ""
Write-Host "Copying unified runner logs..." -ForegroundColor Cyan
if (Test-Path "paper_trading_outputs") {
    Get-ChildItem -Path "paper_trading_outputs" -File -Filter "unified_runner_*.log" | ForEach-Object {
        Copy-Item $_.FullName -Destination "$tempDir\paper_trading_outputs" -Force
        $sizeKB = [math]::Round($_.Length/1KB, 2)
        Write-Host "  Copied: $($_.Name) ($sizeKB KB)" -ForegroundColor DarkGray
    }
}

# Create summary file
$summaryContent = @"
# MetaStackerBandit Compact Logs & Emitters Archive
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

## Archive Strategy

This is a compact version designed to be under 30MB, containing only essential data.

### Included
- System logs (all timeframes)
- 5m trading data (selective - most important files only)
- Emitter source code (all timeframes)
- Unified runner logs

### Excluded (to reduce size)
- hyperliquid_sheet.csv (26+ MB)
- Compressed archives (*.jsonl.gz)
- Large JSON logs (*.jsonl)
- funding_debug.json (6+ MB)
- 1h, 12h, 24h trading data
- Files over 5MB

## Contents

### logs/
System logs from all timeframes

### paper_trading_outputs/5m/
Most Recent Trading Data (Jan 2, 2026)
- signals.csv
- equity.csv
- bandit.csv
- mood_debug.csv
- executions_paper.csv
- decisions.csv
- JSON files

### emitters_code/
Source code for data emitters from all timeframes

## Data Freshness

5m Bot Status: ACTIVE
- Latest data: Jan 2, 2026
- Currently running and trading
"@

Set-Content -Path "$tempDir\COMPACT_ARCHIVE_INFO.md" -Value $summaryContent

# Calculate current size
$currentSize = (Get-ChildItem -Path $tempDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ""
Write-Host "Current uncompressed size: $([math]::Round($currentSize, 2)) MB" -ForegroundColor Yellow

Write-Host ""
Write-Host "Creating zip archive: $zipName" -ForegroundColor Green

# Create zip file
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipName -Force

# Clean up temp directory
Remove-Item -Recurse -Force $tempDir

# Get file size
$zipSize = (Get-Item $zipName).Length / 1MB

Write-Host ""
if ($zipSize -lt 30) {
    Write-Host "Success! Archive is under 30MB" -ForegroundColor Green
} else {
    Write-Host "Warning: Archive is $([math]::Round($zipSize, 2)) MB" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Archive created: $zipName" -ForegroundColor White
Write-Host "Final size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor White
Write-Host ""
Write-Host "Archive contains:" -ForegroundColor Yellow
Write-Host "  - System logs" -ForegroundColor Gray
Write-Host "  - 5m trading data (essential files)" -ForegroundColor Gray
Write-Host "  - Emitter source code" -ForegroundColor Gray
Write-Host "  - Documentation" -ForegroundColor Gray
