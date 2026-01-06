# Model Rollback Script
# Reverts to the model from Jan 3, 13:25 (before the bad retraining on Jan 5)

Write-Host "=" * 80
Write-Host "MODEL ROLLBACK TO JAN 3, 13:25 (BEFORE BAD RETRAINING)"
Write-Host "=" * 80

# Stop the bot first
Write-Host "`nStep 1: Checking if bot is running..."
$botProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*live_demo.main*"}
if ($botProcess) {
    Write-Host "WARNING: Bot is still running! Please stop it first (Ctrl+C in the terminal)"
    Write-Host "Press Enter when bot is stopped..."
    Read-Host
}

# Backup current (bad) model
Write-Host "`nStep 2: Backing up current model..."
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "live_demo\models\backup\backup_$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Copy-Item "live_demo\models\LATEST.json" "$backupDir\LATEST.json"
Write-Host "  Backed up current LATEST.json to $backupDir"

# Create new LATEST.json pointing to Jan 3 model
Write-Host "`nStep 3: Creating new LATEST.json for Jan 3, 13:25 model..."

$newManifest = @{
    meta_classifier = "meta_classifier_20260103_132516_d7a9e9fb3a42.joblib"
    calibrator = "calibrator_20260103_132516_d7a9e9fb3a42.joblib"
    feature_columns = "feature_columns_20260103_132516_d7a9e9fb3a42.json"
    training_meta = "training_meta_20260103_132516_d7a9e9fb3a42.json"
}

$newManifest | ConvertTo-Json | Set-Content "live_demo\models\LATEST.json"
Write-Host "  Created new LATEST.json"

# Verify files exist
Write-Host "`nStep 4: Verifying model files exist..."
$allFilesExist = $true
foreach ($file in $newManifest.Values) {
    $path = "live_demo\models\$file"
    if (Test-Path $path) {
        $size = (Get-Item $path).Length / 1MB
        Write-Host "  [OK] $file ($([math]::Round($size, 2)) MB)"
    } else {
        Write-Host "  [ERROR] $file NOT FOUND!"
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host "`nERROR: Some model files are missing! Rollback aborted."
    exit 1
}

# Clear stale cache
Write-Host "`nStep 5: Clearing stale cache..."
$cacheFiles = Get-ChildItem "paper_trading_outputs\cache\BTCUSDT_5m_*.csv" -ErrorAction SilentlyContinue
if ($cacheFiles) {
    foreach ($file in $cacheFiles) {
        Remove-Item $file.FullName
        Write-Host "  Deleted $($file.Name)"
    }
} else {
    Write-Host "  No cache files to clear"
}

Write-Host "`n" + "=" * 80
Write-Host "ROLLBACK COMPLETE!"
Write-Host "=" * 80

Write-Host "`nModel reverted to: Jan 3, 13:25 (20260103_132516)"
Write-Host "Old (bad) model backed up to: $backupDir"
Write-Host "`nNext steps:"
Write-Host "  1. Restart the bot: .\.venv\Scripts\python.exe -m live_demo.main"
Write-Host "  2. Monitor for 30 minutes"
Write-Host "  3. Check for balanced BUY/SELL trades"
Write-Host "`n" + "=" * 80
