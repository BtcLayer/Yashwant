# MetaStackerBandit Monitoring Schedule
**Current Time**: 12:24 PM, December 23, 2025  
**Status**: All 4 bots restarted at 12:17 PM with Binance fix applied

---

## Bar Close Schedule & Verification Timing

### 5m Timeframe
- **Bar Close Times**: Every 5 minutes (XX:00, XX:05, XX:10, XX:15, XX:20, XX:25, XX:30, etc.)
- **Next Bar Close**: **12:25 PM** (1 minute away!)
- **Then**: 12:30, 12:35, 12:40, 12:45, 12:50, 12:55, 13:00
- **Wait Time**: 1 minute
- **Check After**: 12:26 PM

### 1h Timeframe
- **Bar Close Times**: Every hour on the hour (00:00, 01:00, 02:00, etc.)
- **Next Bar Close**: **13:00 PM** (1:00 PM)
- **Wait Time**: 36 minutes from now
- **Check After**: 13:01 PM

### 12h Timeframe
- **Bar Close Times**: 00:00 (midnight) and 12:00 (noon)
- **Last Bar Close**: 12:00 PM (24 minutes ago - **JUST MISSED IT!**)
- **Next Bar Close**: **00:00 AM** (midnight tonight)
- **Wait Time**: 11 hours 36 minutes
- **Check After**: 00:01 AM tomorrow

### 24h Timeframe
- **Bar Close Times**: 00:00 (midnight) daily
- **Next Bar Close**: **00:00 AM** (midnight tonight)
- **Wait Time**: 11 hours 36 minutes
- **Check After**: 00:01 AM tomorrow

---

## What Files to Monitor (For Each Timeframe)

### Critical Files That Must Exist
Each timeframe writes to its own directory:

#### 5m Bot (live_demo/)
1. **signals_emitted.csv** - Signal generation log
2. **decisions.csv** - Trade decision log
3. **pnl_log.csv** - P&L tracking
4. **runtime_bandit.json** - Current state (position, cash, equity)
5. **trade_log.csv** - Executed trades
6. **sheets_upload.log** (if Google Sheets enabled)

#### 1h Bot (live_demo_1h/)
Same files as above in `live_demo_1h/` directory

#### 12h Bot (live_demo_12h/)
Same files as above in `live_demo_12h/` directory

#### 24h Bot (live_demo_24h/)
Same files as above in `live_demo_24h/` directory

### System Error Logs (logs/)
- **5m_err.log** - 5m stderr output
- **1h_err.log** - 1h stderr output
- **12h_err.log** - 12h stderr output
- **24h_err.log** - 24h stderr output

---

## Immediate Verification (12:24 PM - NOW)

### Step 1: Verify Processes Running (NOW)
```powershell
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, @{Name="Memory(MB)";Expression={[math]::round($_.WS / 1MB, 2)}}
```
**Expected**: At least 4 main Python processes (plus background tasks)

### Step 2: Check Error Logs (NOW)
```powershell
Get-Content logs\5m_err.log -Tail 10
Get-Content logs\1h_err.log -Tail 10
Get-Content logs\12h_err.log -Tail 10
Get-Content logs\24h_err.log -Tail 10
```
**Expected**: Only numpy warnings, NO CancelledError, NO connection timeouts

---

## First Checkpoint: 5m Bot (12:26 PM - 2 minutes from now)

### Wait Until: 12:26 PM (1 minute after 12:25 bar close)

### Files to Check:
```powershell
# Check if signal file exists and has new data
if (Test-Path live_demo\signals_emitted.csv) {
    $lines = (Get-Content live_demo\signals_emitted.csv | Measure-Object -Line).Lines
    Write-Host "5m signals: $lines rows"
    Get-Content live_demo\signals_emitted.csv -Tail 3
} else {
    Write-Host "5m signals file not created yet"
}

# Check runtime state
if (Test-Path live_demo\runtime_bandit.json) {
    $state = Get-Content live_demo\runtime_bandit.json | ConvertFrom-Json
    Write-Host "5m Position: $($state.position) | Cash: $($state.cash) | Equity: $($state.equity)"
} else {
    Write-Host "5m runtime file not created yet"
}

# Check decisions file
if (Test-Path live_demo\decisions.csv) {
    Get-Content live_demo\decisions.csv -Tail 2
} else {
    Write-Host "5m decisions file not created yet"
}
```

### Expected Results:
- ✅ **signals_emitted.csv**: At least 1-2 rows (header + first signal)
- ✅ **runtime_bandit.json**: Position=0, Cash=10000, Equity=10000 (initial state)
- ✅ **decisions.csv**: At least 1 decision row
- ✅ Signal value should be shown (will likely be < 12% threshold, so NO TRADE expected)

---

## Second Checkpoint: 1h Bot (13:01 PM - 37 minutes from now)

### Wait Until: 13:01 PM (1 minute after 13:00 bar close)

### Files to Check:
```powershell
# Check 1h bot logs
if (Test-Path live_demo_1h\signals_emitted.csv) {
    Write-Host "`n=== 1H BOT SIGNALS ==="
    Get-Content live_demo_1h\signals_emitted.csv | Select-Object -Last 3
}

if (Test-Path live_demo_1h\runtime_bandit.json) {
    $state = Get-Content live_demo_1h\runtime_bandit.json | ConvertFrom-Json
    Write-Host "1h Position: $($state.position)"
}

# Check if trade executed (thresholds lowered to 6%)
if (Test-Path live_demo_1h\trade_log.csv) {
    Write-Host "`n=== 1H TRADES ==="
    Get-Content live_demo_1h\trade_log.csv -Tail 3
} else {
    Write-Host "No trades yet (signal below 6% threshold)"
}
```

### Expected Results:
- ✅ **signals_emitted.csv**: First 1h signal recorded
- ✅ **runtime_bandit.json**: Updated state
- ⏳ **trade_log.csv**: May or may not exist depending on signal strength
  - If signal > 6%: Trade executed (VALIDATES threshold fix)
  - If signal < 6%: No trade (normal, need to wait for stronger signal)

---

## Third Checkpoint: 12h Bot (00:01 AM - 11h 37m from now)

### Wait Until: 00:01 AM December 24 (midnight)

### Why Wait So Long?
- 12h bars close at 00:00 and 12:00 only
- Bot restarted at 12:17 PM (17 minutes AFTER the 12:00 bar close)
- The bot **MISSED** the 12:00 PM bar close today
- Next opportunity is midnight tonight

### Files to Check (at 00:01 AM):
```powershell
# Check 12h bot first bar close
if (Test-Path live_demo_12h\signals_emitted.csv) {
    Write-Host "`n=== 12H BOT SIGNALS ==="
    Get-Content live_demo_12h\signals_emitted.csv
}

if (Test-Path live_demo_12h\runtime_bandit.json) {
    $state = Get-Content live_demo_12h\runtime_bandit.json | ConvertFrom-Json
    Write-Host "12h Position: $($state.position) | Cash: $($state.cash)"
}
```

### Expected Results:
- ✅ **signals_emitted.csv**: First 12h signal at midnight
- ✅ Runtime state updated
- ⏳ Possible trade if signal > 6% (testing lowered thresholds)

---

## Fourth Checkpoint: 24h Bot (00:01 AM - 11h 37m from now)

### Wait Until: 00:01 AM December 24 (midnight)

### Files to Check (at 00:01 AM):
```powershell
# Check 24h bot first bar close
if (Test-Path live_demo_24h\signals_emitted.csv) {
    Write-Host "`n=== 24H BOT SIGNALS ==="
    Get-Content live_demo_24h\signals_emitted.csv
}

if (Test-Path live_demo_24h\runtime_bandit.json) {
    $state = Get-Content live_demo_24h\runtime_bandit.json | ConvertFrom-Json
    Write-Host "24h Position: $($state.position) | Cash: $($state.cash)"
}
```

### Expected Results:
- ✅ **signals_emitted.csv**: First 24h signal at midnight
- ✅ Runtime state initialized

---

## Continuous Monitoring Commands

### Monitor All Bots at Once
```powershell
# Check if all bots are generating files
$timeframes = @("live_demo", "live_demo_1h", "live_demo_12h", "live_demo_24h")
foreach ($tf in $timeframes) {
    $name = $tf -replace 'live_demo_', '' -replace 'live_demo', '5m'
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    
    # Check signals
    $sig = "$tf\signals_emitted.csv"
    if (Test-Path $sig) {
        $lines = (Get-Content $sig | Measure-Object -Line).Lines
        $last = Get-Content $sig -Tail 1
        Write-Host "  Signals: $lines rows | Latest: $last"
    } else {
        Write-Host "  Signals: Not created yet"
    }
    
    # Check runtime
    $rt = "$tf\runtime_bandit.json"
    if (Test-Path $rt) {
        Write-Host "  Runtime: Exists"
    } else {
        Write-Host "  Runtime: Not created yet"
    }
}
```

### Check Process Health
```powershell
# Monitor processes every 5 minutes
while ($true) {
    Clear-Host
    Get-Date
    Write-Host "`nPython Processes:" -ForegroundColor Green
    Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, @{Name="CPU";Expression={$_.CPU}}, @{Name="Memory(MB)";Expression={[math]::round($_.WS / 1MB, 2)}} | Format-Table -AutoSize
    
    Write-Host "`nLatest Error Log Entries:" -ForegroundColor Yellow
    Get-Content logs\5m_err.log -Tail 2 -ErrorAction SilentlyContinue
    Get-Content logs\1h_err.log -Tail 2 -ErrorAction SilentlyContinue
    Get-Content logs\12h_err.log -Tail 2 -ErrorAction SilentlyContinue
    Get-Content logs\24h_err.log -Tail 2 -ErrorAction SilentlyContinue
    
    Start-Sleep -Seconds 300  # Wait 5 minutes
}
```

---

## Quick Status Check (Run Anytime)

```powershell
# Quick status of all 4 bots
Write-Host "`n=== BOT STATUS $(Get-Date -Format 'HH:mm:ss') ===" -ForegroundColor Cyan

# Process count
$procs = (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "Python processes: $procs" -ForegroundColor $(if ($procs -ge 4) {"Green"} else {"Red"})

# Check each timeframe
$tfs = @{
    "5m" = "live_demo"
    "1h" = "live_demo_1h"
    "12h" = "live_demo_12h"
    "24h" = "live_demo_24h"
}

foreach ($name in $tfs.Keys) {
    $dir = $tfs[$name]
    $hasSignals = Test-Path "$dir\signals_emitted.csv"
    $hasRuntime = Test-Path "$dir\runtime_bandit.json"
    $status = if ($hasSignals -and $hasRuntime) {"✅ GENERATING"} 
              elseif ($hasRuntime) {"⏳ INITIALIZING"} 
              else {"⚠️ WAITING"}
    Write-Host "  [$name] $status"
}
```

---

## Verification Schedule Summary

| Time       | Timeframe | Action                           | Expected Files                          |
|------------|-----------|----------------------------------|-----------------------------------------|
| **NOW**    | All       | Check processes & error logs     | Error logs clean, 10 processes          |
| **12:26**  | **5m**    | First signal verification        | signals_emitted.csv, runtime_bandit.json|
| 12:30      | 5m        | Second signal                    | Updated CSV files                        |
| 12:35      | 5m        | Third signal                     | Updated CSV files                        |
| **13:01**  | **1h**    | First 1h signal & potential trade| All CSV files, check if trade executed  |
| 13:30      | 5m        | Verify continuous operation      | Multiple signals logged                  |
| 14:01      | 1h        | Second 1h bar                    | Updated logs                             |
| **00:01**  | **12h**   | First 12h bar (CRITICAL)         | First 12h signal generated               |
| **00:01**  | **24h**   | First 24h bar (CRITICAL)         | First 24h signal generated               |

---

## Current Status (12:24 PM)

### ✅ Confirmed Working
- All 4 bots started successfully at 12:17 PM
- No CancelledError in 12h/24h (Binance fix working)
- 10 Python processes running (healthy)
- Error logs show only numpy warnings (normal)

### ⏳ Waiting For First Bar Close
- **5m**: 1 minute away (12:25 PM) ← **CHECK THIS FIRST!**
- **1h**: 36 minutes away (13:00 PM)
- **12h**: 11h 36min away (00:00 AM) - bot started after 12:00 bar, must wait
- **24h**: 11h 36min away (00:00 AM)

### 🎯 Priority Checkpoints
1. **12:26 PM** - Verify 5m bot generating signals
2. **13:01 PM** - Verify 1h bot operational (first trade possible)
3. **00:01 AM** - Verify 12h/24h bots operational (first signals)

---

## Files Currently Being Generated

The bots are running but waiting for their first bar close to write files:
- **5m**: Will create files at 12:25 PM (60 seconds from now)
- **1h**: Will create files at 13:00 PM (36 minutes from now)
- **12h**: Will create files at 00:00 AM (11h 36m from now)
- **24h**: Will create files at 00:00 AM (11h 36m from now)

**All bots are IN PROCESS** but outputs are pending bar closes!

---

*Next action: Wait until 12:26 PM and run the 5m verification commands*
