# Script to create logs and emitted data archive (under 30MB)
# Date: 2026-01-02
# Focus: System logs + emitted trading data (CSV/JSON) from all timeframes

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$zipName = "MetaStackerBandit_logs_data_$timestamp.zip"
$tempDir = "temp_logs_data"

Write-Host "Creating logs and emitted data archive (target: <30MB)..." -ForegroundColor Green
Write-Host ""

# Create temporary directory
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null
New-Item -ItemType Directory -Path "$tempDir\logs" -Force | Out-Null
New-Item -ItemType Directory -Path "$tempDir\emitted_data" -Force | Out-Null

Write-Host "Strategy: Logs + Essential emitted data from all timeframes" -ForegroundColor Yellow
Write-Host "  Include: System logs, trading CSVs, small JSON files" -ForegroundColor Gray
Write-Host "  Exclude: Large files (>5MB), compressed archives" -ForegroundColor Gray
Write-Host ""

# Files to EXCLUDE (too large)
$excludePatterns = @(
    "hyperliquid_sheet*.csv",
    "*.jsonl.gz",
    "*.jsonl",
    "funding_debug.json"
)

function Should-Exclude {
    param($fileName)
    foreach ($pattern in $excludePatterns) {
        if ($fileName -like $pattern) {
            return $true
        }
    }
    return $false
}

# 1. Copy system logs
Write-Host "1. Copying system logs..." -ForegroundColor Cyan
if (Test-Path "logs") {
    Get-ChildItem -Path "logs" -File | ForEach-Object {
        Copy-Item $_.FullName -Destination "$tempDir\logs" -Force
        $sizeKB = [math]::Round($_.Length/1KB, 2)
        Write-Host "  $($_.Name) ($sizeKB KB)" -ForegroundColor DarkGray
    }
}

# Copy root level log files
Get-ChildItem -Path . -File -Include *.log | Where-Object {
    $_.Length -lt 10MB
} | ForEach-Object {
    Copy-Item $_.FullName -Destination "$tempDir\logs" -Force
    $sizeKB = [math]::Round($_.Length/1KB, 2)
    Write-Host "  $($_.Name) ($sizeKB KB)" -ForegroundColor DarkGray
}

# 2. Copy emitted data from all timeframes
Write-Host ""
Write-Host "2. Copying emitted data from all timeframes..." -ForegroundColor Cyan

$timeframes = @("5m", "1h", "12h", "24h")

foreach ($tf in $timeframes) {
    $sourcePath = "paper_trading_outputs\$tf"
    
    if (Test-Path $sourcePath) {
        Write-Host ""
        Write-Host "  Processing $tf timeframe..." -ForegroundColor Yellow
        
        $destPath = Join-Path "$tempDir\emitted_data" $tf
        New-Item -ItemType Directory -Path $destPath -Force | Out-Null
        
        # Copy CSV and small JSON files
        Get-ChildItem -Path $sourcePath -File -Include *.csv,*.json -Recurse | Where-Object {
            -not (Should-Exclude $_.Name) -and $_.Length -lt 5MB
        } | ForEach-Object {
            $relativePath = $_.FullName.Substring((Get-Item $sourcePath).FullName.Length + 1)
            $targetPath = Join-Path $destPath $relativePath
            $targetDir = Split-Path $targetPath -Parent
            
            if (-not (Test-Path $targetDir)) {
                New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            }
            
            Copy-Item $_.FullName -Destination $targetPath -Force
            $sizeKB = [math]::Round($_.Length/1KB, 2)
            Write-Host "    $relativePath ($sizeKB KB)" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "  ${tf}: No data found" -ForegroundColor DarkGray
    }
}

# 3. Copy unified runner logs
Write-Host ""
Write-Host "3. Copying unified runner logs..." -ForegroundColor Cyan
if (Test-Path "paper_trading_outputs") {
    Get-ChildItem -Path "paper_trading_outputs" -File -Filter "*.log" | ForEach-Object {
        Copy-Item $_.FullName -Destination "$tempDir\logs" -Force
        $sizeKB = [math]::Round($_.Length/1KB, 2)
        Write-Host "  $($_.Name) ($sizeKB KB)" -ForegroundColor DarkGray
    }
    
    # Copy root level JSON files
    Get-ChildItem -Path "paper_trading_outputs" -File -Filter "*.json" | Where-Object {
        $_.Length -lt 1MB
    } | ForEach-Object {
        Copy-Item $_.FullName -Destination "$tempDir\emitted_data" -Force
        $sizeKB = [math]::Round($_.Length/1KB, 2)
        Write-Host "  $($_.Name) ($sizeKB KB)" -ForegroundColor DarkGray
    }
}

# Create summary
$summaryContent = @"
# MetaStackerBandit Logs & Emitted Data Archive
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

## Contents

### logs/
System logs from all timeframes:
- 5m.log, 1h.log, 12h.log, 24h.log
- Error logs (*_err.log)
- Output logs (*_out.log)
- Unified runner logs
- Startup logs

### emitted_data/
Trading data organized by timeframe:

#### 5m/
Latest trading data (most active)
- signals.csv - Trading signals
- equity.csv - Equity tracking
- bandit.csv - Bandit algorithm data
- mood_debug.csv - Market mood
- executions_paper.csv - Executed trades
- decisions.csv - Trading decisions
- Other CSV/JSON files

#### 1h/
1-hour timeframe data

#### 12h/
12-hour timeframe data

#### 24h/
24-hour timeframe data

## Excluded Files
To keep archive under 30MB:
- hyperliquid_sheet.csv (26+ MB raw exchange data)
- *.jsonl.gz (compressed archives)
- *.jsonl (large JSON logs)
- funding_debug.json (6+ MB)
- Files over 5MB

## Usage
- Review logs/ for system errors and debugging
- Analyze emitted_data/ for trading performance
- Focus on 5m/ for most recent activity
"@

Set-Content -Path "$tempDir\README.md" -Value $summaryContent

# Calculate size
$currentSize = (Get-ChildItem -Path $tempDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ""
Write-Host "Uncompressed size: $([math]::Round($currentSize, 2)) MB" -ForegroundColor Yellow

Write-Host ""
Write-Host "Creating zip archive..." -ForegroundColor Green

# Create zip
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipName -Force

# Cleanup
Remove-Item -Recurse -Force $tempDir

# Report
$zipSize = (Get-Item $zipName).Length / 1MB

Write-Host ""
if ($zipSize -lt 30) {
    Write-Host "SUCCESS! Archive is under 30MB" -ForegroundColor Green
} else {
    Write-Host "WARNING: Archive is $([math]::Round($zipSize, 2)) MB" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Archive: $zipName" -ForegroundColor White
Write-Host "Size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor White
Write-Host ""
Write-Host "Contains:" -ForegroundColor Cyan
Write-Host "  - System logs (all timeframes)" -ForegroundColor Gray
Write-Host "  - Emitted trading data (5m, 1h, 12h, 24h)" -ForegroundColor Gray
Write-Host "  - CSV files: signals, equity, bandit, etc." -ForegroundColor Gray
Write-Host "  - JSON config and summary files" -ForegroundColor Gray
