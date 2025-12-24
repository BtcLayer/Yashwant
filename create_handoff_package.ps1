# MetaStackerBandit Release Packaging Script
# Creates clean handoff zip with code + logs up to Dec 19, 2025

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$dateStamp = Get-Date -Format "yyyy-MM-dd"
$zipName = "MetaStackerBandit_code_logs_emitters_$dateStamp.zip"
$tempDir = "MetaStackerBandit_package_temp"
$dec19Cutoff = Get-Date "2025-12-20"

Write-Host "================================================================"
Write-Host "MetaStackerBandit Release Packaging - Date: $dateStamp"
Write-Host "Including logs up to: 2025-12-19 23:59:59"
Write-Host "================================================================"
Write-Host ""

# Clean up any existing temp directory
if (Test-Path $tempDir) {
    Write-Host "Cleaning existing temp directory..."
    Remove-Item $tempDir -Recurse -Force
}

# Create temp directory
Write-Host "Creating temporary packaging directory..."
New-Item -ItemType Directory -Path $tempDir | Out-Null

# SECTION 1: CODE DIRECTORIES
Write-Host ""
Write-Host "--- COPYING CODE DIRECTORIES ---"

$codeDirectories = @(
    "backend",
    "core",
    "docs",
    "live_demo",
    "live_demo_12h",
    "live_demo_1h", 
    "live_demo_24h",
    "ops",
    "scripts",
    "tests",
    "tools"
)

foreach ($dir in $codeDirectories) {
    if (Test-Path $dir) {
        Write-Host "  [OK] $dir"
        
        $files = Get-ChildItem $dir -Recurse -File | Where-Object {
            $_.FullName -notmatch '\\__pycache__\\' -and
            $_.FullName -notmatch '\\.pyc$' -and
            $_.FullName -notmatch '\\.ruff_cache' -and
            $_.FullName -notmatch '\\.pytest_cache' -and
            $_.Extension -notmatch '^\.(joblib|pkl)$'
        }
        
        foreach ($file in $files) {
            $relativePath = $file.FullName.Substring((Get-Location).Path.Length + 1)
            $targetPath = Join-Path $tempDir $relativePath
            $targetDir = Split-Path $targetPath -Parent
            
            if (-not (Test-Path $targetDir)) {
                New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            }
            
            Copy-Item $file.FullName $targetPath -Force
        }
    }
}

# SECTION 2: ROOT CONFIG FILES
Write-Host ""
Write-Host "--- COPYING ROOT CONFIG FILES ---"

$rootFiles = @(
    "requirements.txt",
    "setup.py",
    "README.md",
    "run_5m_debug.py",
    "run_1h.py",
    "run_12h.py",
    "run_24h.py",
    "run_unified_bots.py",
    "evaluate_ensemble_1p0.py",
    "test_emitters.py",
    "test_startup.py",
    "observability_audit_dec18-19_2025.md"
)

foreach ($file in $rootFiles) {
    if (Test-Path $file) {
        Write-Host "  [OK] $file"
        Copy-Item $file (Join-Path $tempDir $file) -Force
    }
}

# SECTION 3: LOGS & EMITTERS (UP TO DEC 19 ONLY)
Write-Host ""
Write-Host "--- COPYING LOGS AND EMITTERS (UP TO DEC 19) ---"

$outputDir = Join-Path $tempDir "paper_trading_outputs"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$timeframes = @("5m", "1h", "12h", "24h")

foreach ($tf in $timeframes) {
    $tfPath = Join-Path "paper_trading_outputs" $tf
    
    if (Test-Path $tfPath) {
        Write-Host "  Processing $tf logs..."
        
        $files = Get-ChildItem $tfPath -Recurse -File -ErrorAction SilentlyContinue | 
            Where-Object { $_.LastWriteTime -lt $dec19Cutoff }
        
        $fileCount = $files.Count
        $sizeMB = [math]::Round(($files | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
        
        Write-Host "    [OK] $tf - $fileCount files, $sizeMB MB"
        
        foreach ($file in $files) {
            $relativePath = $file.FullName.Substring((Join-Path (Get-Location) "paper_trading_outputs").Length + 1)
            $targetPath = Join-Path $outputDir $relativePath
            $targetDir = Split-Path $targetPath -Parent
            
            if (-not (Test-Path $targetDir)) {
                New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            }
            
            Copy-Item $file.FullName $targetPath -Force
        }
    }
}

# Copy summary CSVs
$summaryFiles = @(
    "cohort_stats.csv",
    "equity.csv",
    "metrics.json",
    "signals.csv",
    "signals_with_cohorts.csv",
    "trade_log.csv"
)

foreach ($file in $summaryFiles) {
    $fullPath = Join-Path "paper_trading_outputs" $file
    if (Test-Path $fullPath) {
        $fileInfo = Get-Item $fullPath
        if ($fileInfo.LastWriteTime -lt $dec19Cutoff) {
            Write-Host "  [OK] $file"
            Copy-Item $fullPath (Join-Path $outputDir $file) -Force
        }
    }
}

# SECTION 4: CREATE ZIP FILE
Write-Host ""
Write-Host "--- CREATING ZIP FILE ---"

if (Test-Path $zipName) {
    Write-Host "  Removing existing zip..."
    Remove-Item $zipName -Force
}

Write-Host "  Compressing to $zipName..."
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipName -CompressionLevel Optimal

# SECTION 5: VERIFICATION
Write-Host ""
Write-Host "--- VERIFICATION ---"

$zipInfo = Get-Item $zipName
$zipSizeMB = [math]::Round($zipInfo.Length / 1MB, 2)

Write-Host "  [OK] Zip created: $zipName"
Write-Host "  [OK] Size: $zipSizeMB MB"
Write-Host "  [OK] Date: $($zipInfo.LastWriteTime)"

Write-Host ""
Write-Host "  Testing zip integrity..."
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path $zipName).Path)
    $entryCount = $zip.Entries.Count
    $zip.Dispose()
    Write-Host "  [OK] Zip is valid: $entryCount entries"
} catch {
    Write-Host "  [ERROR] Zip validation failed: $_"
}

# SECTION 6: SUMMARY REPORT
Write-Host ""
Write-Host "================================================================"
Write-Host "PACKAGING SUMMARY"
Write-Host "================================================================"

Write-Host ""
Write-Host "INCLUDED:"
Write-Host "  - Code directories: backend, core, docs, live_demo, live_demo_12h, live_demo_1h, live_demo_24h, ops, scripts, tests, tools"
Write-Host "  - Config files: requirements.txt, setup.py, README.md, run_*.py"
Write-Host "  - Logs: paper_trading_outputs (5m, 1h, 12h, 24h) up to Dec 19"
Write-Host "  - Audit report: observability_audit_dec18-19_2025.md"

Write-Host ""
Write-Host "EXCLUDED:"
Write-Host "  - .venv/ (virtual environment)"
Write-Host "  - __pycache__/ (Python bytecode)"
Write-Host "  - .git/ (version control)"
Write-Host "  - *.joblib, *.pkl (large model files: ~142 MB excluded)"
Write-Host "  - Dec 20 logs (only 5m ran, excluded per requirement)"
Write-Host "  - frontend/ (259 MB, not essential for handoff)"
Write-Host "  - live_core/ (empty)"

Write-Host ""
Write-Host "FILE DETAILS:"
Write-Host "  - Zip name: $zipName"
Write-Host "  - Zip size: $zipSizeMB MB"
Write-Host "  - Location: $(Get-Location)\$zipName"

Write-Host ""
Write-Host "--- CLEANUP ---"
Write-Host "  Removing temporary directory..."
Remove-Item $tempDir -Recurse -Force
Write-Host "  [OK] Cleanup complete"

Write-Host ""
Write-Host "================================================================"
Write-Host "PACKAGING COMPLETE"
Write-Host "================================================================"
Write-Host ""
