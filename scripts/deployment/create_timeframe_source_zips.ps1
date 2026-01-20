# Script to create separate source code zips for each timeframe
# Date: 2026-01-07

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"

Write-Host "========================================" -ForegroundColor Green
Write-Host "Creating Timeframe Source Code Archives" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Define timeframes with their directories
$timeframes = @(
    @{Name="5m"; Dir="live_demo"; DisplayName="5 Minute"},
    @{Name="1h"; Dir="live_demo_1h"; DisplayName="1 Hour"},
    @{Name="12h"; Dir="live_demo_12h"; DisplayName="12 Hour"},
    @{Name="24h"; Dir="live_demo_24h"; DisplayName="24 Hour"}
)

# File extensions to include (source code only)
$sourceExtensions = @('.py', '.json', '.sh', '.bat', '.md', '.txt', '.yml', '.yaml')

# Specific files to EXCLUDE
$excludeFiles = @(
    "metastackerbandit1-478b6face97d.json"
)

# Directories to EXCLUDE within each timeframe
$excludeDirs = @(
    "emitters",
    "logs",
    "paper_trading_outputs",
    "__pycache__",
    ".pytest_cache",
    "models",
    "models_backup"
)

# Function to check if directory should be excluded
function Should-ExcludeDir {
    param($path)
    foreach ($excludeDir in $excludeDirs) {
        if ($path -like "*\$excludeDir" -or $path -like "*\$excludeDir\*") {
            return $true
        }
    }
    return $false
}

# Function to check if file should be excluded
function Should-ExcludeFile {
    param($fileName)
    $name = Split-Path $fileName -Leaf
    foreach ($excludeFile in $excludeFiles) {
        if ($name -eq $excludeFile) {
            return $true
        }
    }
    # Exclude files larger than 500KB
    if ((Get-Item $fileName -ErrorAction SilentlyContinue).Length -gt 500KB) {
        return $true
    }
    return $false
}

$allZips = @()

foreach ($timeframe in $timeframes) {
    $tfName = $timeframe.Name
    $tfDir = $timeframe.Dir
    $tfDisplay = $timeframe.DisplayName
    
    Write-Host "Processing: $tfDisplay ($tfName)" -ForegroundColor Cyan
    Write-Host "Directory: $tfDir" -ForegroundColor Gray
    
    if (-not (Test-Path $tfDir)) {
        Write-Host "  WARNING: Directory not found, skipping...`n" -ForegroundColor Yellow
        continue
    }
    
    $zipName = "MetaStackerBandit_${tfName}_source_$timestamp.zip"
    $tempDir = "temp_${tfName}_source"
    
    # Clean up temp directory if exists
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    
    # Create timeframe directory in temp
    $tfTempDir = Join-Path $tempDir $tfDir
    New-Item -ItemType Directory -Path $tfTempDir | Out-Null
    
    # Copy source files
    $fileCount = 0
    $totalSize = 0
    
    Get-ChildItem -Path $tfDir -Recurse -File | Where-Object {
        $dirPath = Split-Path $_.FullName -Parent
        
        # Check if file should be included
        (-not (Should-ExcludeDir $dirPath)) -and
        (-not (Should-ExcludeFile $_.FullName)) -and
        ($_.Extension -in $sourceExtensions)
    } | ForEach-Object {
        $relativePath = $_.FullName.Substring((Get-Location).Path.Length + 1)
        $destPath = Join-Path $tempDir $relativePath
        $destFolder = Split-Path $destPath -Parent
        
        if (-not (Test-Path $destFolder)) {
            New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
        }
        
        Copy-Item $_.FullName -Destination $destPath
        $fileCount++
        $totalSize += $_.Length
    }
    
    # Add a README for this timeframe
    $readmeContent = @"
# MetaStackerBandit - $tfDisplay Timeframe Source Code

**Timeframe:** $tfDisplay ($tfName)
**Directory:** $tfDir
**Exported:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Contents

This archive contains the source code for the $tfDisplay timeframe trading bot.

### Key Files:
- ``main.py`` - Main entry point for the bot
- ``decision.py`` - Trading decision logic
- ``features.py`` - Feature engineering
- ``model_runtime.py`` - Model loading and inference
- ``risk_and_exec.py`` - Risk management and execution
- ``config.json`` - Configuration settings
- ``config_overlay.json`` - Overlay configuration

### Excluded:
- Emitters (log outputs)
- Models (binary files)
- Large data files (>500KB)
- Cache directories

## Usage

1. Install dependencies: ``pip install -r requirements.txt`` (from root)
2. Configure ``.env`` file with API keys
3. Run: ``python $tfDir\main.py``

For more information, see the main project README.
"@
    
    $readmePath = Join-Path $tfTempDir "README_${tfName}.md"
    Set-Content -Path $readmePath -Value $readmeContent
    $fileCount++
    
    Write-Host "  Files copied: $fileCount" -ForegroundColor Gray
    Write-Host "  Total size: $([math]::Round($totalSize/1KB, 2)) KB" -ForegroundColor Gray
    
    # Create zip file
    Write-Host "  Creating: $zipName" -ForegroundColor Gray
    Compress-Archive -Path "$tempDir\*" -DestinationPath $zipName -Force
    
    # Clean up temp directory
    Remove-Item -Recurse -Force $tempDir
    
    # Get zip size
    $zipSize = (Get-Item $zipName).Length / 1KB
    Write-Host "  Compressed: $([math]::Round($zipSize, 2)) KB" -ForegroundColor Green
    Write-Host ""
    
    $allZips += @{
        Name = $zipName
        Timeframe = $tfDisplay
        Files = $fileCount
        UncompressedKB = [math]::Round($totalSize/1KB, 2)
        CompressedKB = [math]::Round($zipSize, 2)
    }
}

# Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "SUMMARY - All Timeframe Archives Created" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

foreach ($zip in $allZips) {
    Write-Host "$($zip.Timeframe) Timeframe:" -ForegroundColor Cyan
    Write-Host "  File: $($zip.Name)" -ForegroundColor White
    Write-Host "  Source Files: $($zip.Files)" -ForegroundColor Gray
    Write-Host "  Uncompressed: $($zip.UncompressedKB) KB" -ForegroundColor Gray
    Write-Host "  Compressed: $($zip.CompressedKB) KB" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "All archives created successfully!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green
