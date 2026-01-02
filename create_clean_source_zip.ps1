# Script to create a clean source code zip without dependencies and unnecessary files
# Date: 2026-01-02

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$zipName = "MetaStackerBandit_source_$timestamp.zip"
$tempDir = "temp_source_export"

Write-Host "Creating clean source code archive..." -ForegroundColor Green

# Create temporary directory
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Define patterns to EXCLUDE
$excludePatterns = @(
    ".venv",
    ".venv_old",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".git",
    "*.csv",
    "*.rar",
    "*.bundle",
    "*.log",
    "*.jsonl",
    "*.jsonl.gz",
    "logs",
    "paper_trading_outputs",
    "emitters",
    "*.zip",
    "temp_*",
    "AUDIT_EXTRACT_TEMP",
    "BotV2-LSTM",
    "live_core",
    "models_backup_*",
    "models_new",
    "*.pem"
)

# Important JSON files to include
$importantJsonFiles = @(
    "config.json",
    "config_overlay.json",
    "logging_config.json",
    "runtime_bandit.json",
    "vm_ip.json",
    "package.json",
    "package-lock.json"
)

# Important directories to include
$importantDirs = @(
    "live_demo",
    "live_demo_1h",
    "live_demo_12h",
    "live_demo_24h",
    "backend",
    "frontend",
    "core",
    "scripts",
    "tools",
    "ops",
    "notebooks",
    "tests",
    "docs",
    "plans"
)

Write-Host "Copying source files..." -ForegroundColor Yellow

# Function to check if path should be excluded
function Should-Exclude {
    param($path)
    
    foreach ($pattern in $excludePatterns) {
        if ($path -like "*$pattern*") {
            return $true
        }
    }
    return $false
}

# Copy root level Python files and scripts
Get-ChildItem -Path . -File | Where-Object {
    ($_.Extension -in @('.py', '.sh', '.bat', '.ps1', '.md', '.txt', '.conf')) -and
    (-not (Should-Exclude $_.FullName))
} | ForEach-Object {
    Copy-Item $_.FullName -Destination $tempDir
    Write-Host "  Copied: $($_.Name)" -ForegroundColor Gray
}

# Copy important JSON files from root
foreach ($jsonFile in $importantJsonFiles) {
    if (Test-Path $jsonFile) {
        Copy-Item $jsonFile -Destination $tempDir
        Write-Host "  Copied: $jsonFile" -ForegroundColor Gray
    }
}

# Copy .env.example and .gitignore
if (Test-Path ".env.example") {
    Copy-Item ".env.example" -Destination $tempDir
    Write-Host "  Copied: .env.example" -ForegroundColor Gray
}
if (Test-Path ".gitignore") {
    Copy-Item ".gitignore" -Destination $tempDir
    Write-Host "  Copied: .gitignore" -ForegroundColor Gray
}

# Copy requirements.txt
if (Test-Path "requirements.txt") {
    Copy-Item "requirements.txt" -Destination $tempDir
    Write-Host "  Copied: requirements.txt" -ForegroundColor Gray
}

# Copy important directories
foreach ($dir in $importantDirs) {
    if (Test-Path $dir) {
        Write-Host "  Processing directory: $dir" -ForegroundColor Cyan
        
        # Create directory structure
        $destDir = Join-Path $tempDir $dir
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        
        # Copy files recursively, excluding unwanted patterns
        Get-ChildItem -Path $dir -Recurse -File | Where-Object {
            $relativePath = $_.FullName.Substring((Get-Location).Path.Length)
            -not (Should-Exclude $relativePath) -and
            (
                $_.Extension -in @('.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.html', '.css', '.sh', '.bat', '.ps1', '.md', '.txt', '.conf', '.yml', '.yaml', '.toml') -or
                $_.Name -in @('.gitignore', '.env.example', 'Dockerfile', 'nginx.conf')
            )
        } | ForEach-Object {
            $relativePath = $_.FullName.Substring((Get-Location).Path.Length + 1)
            $destPath = Join-Path $tempDir $relativePath
            $destFolder = Split-Path $destPath -Parent
            
            if (-not (Test-Path $destFolder)) {
                New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
            }
            
            Copy-Item $_.FullName -Destination $destPath
            Write-Host "    Copied: $relativePath" -ForegroundColor DarkGray
        }
    }
}

# Copy .github directory if exists
if (Test-Path ".github") {
    Write-Host "  Processing directory: .github" -ForegroundColor Cyan
    Copy-Item -Path ".github" -Destination (Join-Path $tempDir ".github") -Recurse -Force
}

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
Write-Host "This archive contains only source code files, excluding:" -ForegroundColor Yellow
Write-Host "  - Dependencies" -ForegroundColor Gray
Write-Host "  - Large data files" -ForegroundColor Gray
Write-Host "  - Logs and outputs" -ForegroundColor Gray
Write-Host "  - Git history" -ForegroundColor Gray
Write-Host "  - Previous archives" -ForegroundColor Gray
Write-Host "  - Temporary files" -ForegroundColor Gray
