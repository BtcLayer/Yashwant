# Script to create a clean code zip - ONLY essential source code
# Excludes: markdown files, text files, PowerShell scripts, notebooks, heavy files, dependencies
# Date: 2026-01-14

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$zipName = "MetaStackerBandit_clean_code_$timestamp.zip"
$tempDir = "temp_clean_code"

Write-Host "Creating clean code archive (essential source code only)..." -ForegroundColor Green

# Clean up temp directory if exists
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# ONLY include these specific essential files from root
$essentialRootFiles = @(
    "requirements.txt",
    ".env.example",
    ".gitignore"
)

# Essential directories with source code
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
    "ops",
    "schemas"
)

# ONLY these file extensions (NO .md, .txt, .ps1, .ipynb)
$sourceExtensions = @(
    '.py',      # Python
    '.js',      # JavaScript
    '.jsx',     # React
    '.ts',      # TypeScript
    '.tsx',     # TypeScript React
    '.html',    # HTML
    '.css',     # CSS
    '.sh',      # Shell scripts
    '.bat',     # Batch files
    '.json',    # JSON configs (will filter large ones)
    '.yml',     # YAML
    '.yaml',    # YAML
    '.conf'     # Config files
)

# Specific files to EXCLUDE
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
    ".github",
    "logs",
    "logs_emitters_jan6-8",
    "paper_trading_outputs",
    "emitters",
    "models",
    "models_backup",
    "models_new",
    "AUDIT_EXTRACT_TEMP",
    "BotV2-LSTM",
    "live_core",
    "hyperliquid_data",
    "test_models",
    "notebooks",
    "snapshots",
    "plans",
    "docs",
    "tests",
    "-p",
    "temp_clean_package"
)

Write-Host "Copying essential root files..." -ForegroundColor Yellow

# Copy essential root files
foreach ($file in $essentialRootFiles) {
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
    param($fileName, $fileObj)
    
    # Exclude specific files
    foreach ($excludeFile in $excludeSpecificFiles) {
        if ($fileObj.Name -eq $excludeFile) {
            return $true
        }
    }
    
    # Exclude files larger than 500KB (to avoid large data files)
    if ($fileObj.Length -gt 500KB) {
        return $true
    }
    
    return $false
}

Write-Host "`nCopying essential directories..." -ForegroundColor Yellow

$fileCount = 0

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
            (-not (Should-ExcludeFile $_.FullName $_)) -and
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
            $fileCount++
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
Write-Host "Files: $fileCount" -ForegroundColor White
Write-Host "`nThis archive contains ONLY:" -ForegroundColor Yellow
Write-Host "  + Python source code (.py)" -ForegroundColor Gray
Write-Host "  + JavaScript/React code (.js, .jsx, .ts, .tsx)" -ForegroundColor Gray
Write-Host "  + HTML/CSS files" -ForegroundColor Gray
Write-Host "  + Small config files (.json < 500KB, .yml)" -ForegroundColor Gray
Write-Host "  + Shell/batch scripts (.sh, .bat)" -ForegroundColor Gray
Write-Host "`nEXCLUDED:" -ForegroundColor Yellow
Write-Host "  - Markdown files (.md)" -ForegroundColor Gray
Write-Host "  - Text files (.txt)" -ForegroundColor Gray
Write-Host "  - PowerShell scripts (.ps1)" -ForegroundColor Gray
Write-Host "  - Notebooks (.ipynb)" -ForegroundColor Gray
Write-Host "  - Dependencies (node_modules, .venv)" -ForegroundColor Gray
Write-Host "  - Large data files (>500KB)" -ForegroundColor Gray
Write-Host "  - Logs and outputs" -ForegroundColor Gray
Write-Host "  - Model files" -ForegroundColor Gray
Write-Host "  - Build artifacts" -ForegroundColor Gray
Write-Host "  - Git history" -ForegroundColor Gray
Write-Host "========================================`n" -ForegroundColor Green
