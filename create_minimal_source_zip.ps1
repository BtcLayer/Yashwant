# Script to create a minimal source code zip - ONLY essential source files
# Date: 2026-01-07

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$zipName = "MetaStackerBandit_minimal_source_$timestamp.zip"
$tempDir = "temp_minimal_source"

Write-Host "Creating minimal source code archive (source code only)..." -ForegroundColor Green

# Clean up temp directory if exists
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Define ONLY the essential files and directories to include
$essentialFiles = @(
    # Core Python files (root level - only essential ones)
    "backtest_engine.py",
    "run_unified_bots.py",
    "run_shadow_overlays.py",
    "train_model.py",
    
    # Configuration and setup
    "requirements.txt",
    ".env.example",
    ".gitignore",
    "setup.py",
    "nginx.conf",
    
    # Documentation
    "README.md",
    "PROJECT_HANDOFF_DOCUMENTATION.md",
    "ALL_TIMEFRAMES_STATUS.md",
    "BACKTEST_README.md"
)

# Essential directories with source code only
$essentialDirs = @(
    "live_demo",
    "live_demo_1h",
    "live_demo_12h",
    "live_demo_24h",
    "backend",
    "frontend\src",
    "frontend\public",
    "core",
    "scripts",
    "tools",
    "ops"
)

# File extensions to include (source code only)
$sourceExtensions = @('.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.sh', '.bat', '.json', '.md', '.txt', '.yml', '.yaml', '.conf')

# Specific large files to EXCLUDE
$excludeSpecificFiles = @(
    "metastackerbandit1-478b6face97d.json",
    "package-lock.json",
    "api_response_meta.json",
    "api_sample_allMids.json",
    "api_sample_meta.json",
    "api_sample_metaAndAssetCtxs.json"
)

# Directories to EXCLUDE
$excludeDirs = @(
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    ".venv_old",
    ".git",
    "logs",
    "paper_trading_outputs",
    "emitters",
    "models",
    "models_backup",
    "models_new",
    "AUDIT_EXTRACT_TEMP",
    "BotV2-LSTM",
    "live_core",
    "hyperliquid_data",
    "test_models"
)

Write-Host "Copying essential root files..." -ForegroundColor Yellow

# Copy essential root files
foreach ($file in $essentialFiles) {
    if (Test-Path $file) {
        Copy-Item $file -Destination $tempDir
        Write-Host "  + $file" -ForegroundColor Gray
    }
}

# Copy package.json if exists (but not package-lock.json)
if (Test-Path "frontend\package.json") {
    $frontendDir = Join-Path $tempDir "frontend"
    New-Item -ItemType Directory -Path $frontendDir -Force | Out-Null
    Copy-Item "frontend\package.json" -Destination $frontendDir
    Write-Host "  + frontend\package.json" -ForegroundColor Gray
}

# Function to check if directory should be excluded
function Should-ExcludeDir {
    param($path)
    foreach ($excludeDir in $excludeDirs) {
        if ($path -like "*\$excludeDir\*" -or $path -like "*\$excludeDir") {
            return $true
        }
    }
    return $false
}

# Function to check if file should be excluded
function Should-ExcludeFile {
    param($fileName)
    foreach ($excludeFile in $excludeSpecificFiles) {
        if ($fileName -eq $excludeFile) {
            return $true
        }
    }
    # Exclude files larger than 1MB
    if ((Get-Item $fileName -ErrorAction SilentlyContinue).Length -gt 1MB) {
        return $true
    }
    return $false
}

Write-Host "`nCopying essential directories..." -ForegroundColor Yellow

# Copy essential directories
foreach ($dir in $essentialDirs) {
    if (Test-Path $dir) {
        Write-Host "`n  Processing: $dir" -ForegroundColor Cyan
        
        # Get all source files recursively
        Get-ChildItem -Path $dir -Recurse -File | Where-Object {
            $relativePath = $_.FullName.Substring((Get-Location).Path.Length + 1)
            $dirPath = Split-Path $_.FullName -Parent
            
            # Check if file should be included
            (-not (Should-ExcludeDir $dirPath)) -and
            (-not (Should-ExcludeFile $_.FullName)) -and
            ($_.Extension -in $sourceExtensions -or $_.Name -in @('.gitignore', 'Dockerfile'))
        } | ForEach-Object {
            $relativePath = $_.FullName.Substring((Get-Location).Path.Length + 1)
            $destPath = Join-Path $tempDir $relativePath
            $destFolder = Split-Path $destPath -Parent
            
            if (-not (Test-Path $destFolder)) {
                New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
            }
            
            Copy-Item $_.FullName -Destination $destPath
            Write-Host "    + $relativePath" -ForegroundColor DarkGray
        }
    }
}

Write-Host "`nCreating zip archive: $zipName" -ForegroundColor Green

# Create zip file
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipName -Force

# Clean up temp directory
Remove-Item -Recurse -Force $tempDir

# Get file size
$zipSize = (Get-Item $zipName).Length / 1KB

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "SUCCESS!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Archive: $zipName" -ForegroundColor White
Write-Host "Size: $([math]::Round($zipSize, 2)) KB" -ForegroundColor White
Write-Host "`nThis archive contains ONLY:" -ForegroundColor Yellow
Write-Host "  + Python source code (.py)" -ForegroundColor Gray
Write-Host "  + JavaScript/React code (.js, .jsx, .css)" -ForegroundColor Gray
Write-Host "  + Configuration files (small .json, .yml)" -ForegroundColor Gray
Write-Host "  + Documentation (.md)" -ForegroundColor Gray
Write-Host "  + Scripts (.sh, .bat, .ps1)" -ForegroundColor Gray
Write-Host "`nEXCLUDED:" -ForegroundColor Yellow
Write-Host "  - Dependencies (node_modules, .venv)" -ForegroundColor Gray
Write-Host "  - Large data files (>1MB)" -ForegroundColor Gray
Write-Host "  - Logs and outputs" -ForegroundColor Gray
Write-Host "  - Model files" -ForegroundColor Gray
Write-Host "  - Build artifacts" -ForegroundColor Gray
Write-Host "  - Git history" -ForegroundColor Gray
Write-Host "========================================`n" -ForegroundColor Green
