# 24H Trading Bot - Integration Guide

## Overview
The `live_demo_24h` bot is configured to trade on **daily (1d/24h) timeframes**, creating a fourth parallel trading strategy alongside the 5m, 1h, and 12h bots.

## Key Configuration

### Timeframe Settings
- **Interval**: `1d` (daily candles from Binance)
- **Bar Frequency**: Once per UTC day (00:00 UTC candle close)
- **Feature Timeframe**: Daily rolling features
- **Output Directory**: `paper_trading_outputs/24h/`

### Integration Points

#### 1. Unified Runner (`run_unified_bots.py`)
✅ **Status**: Fully integrated
- Imports `live_demo_24h.main.run_live` as `run_24h`
- Runs concurrently with 5m, 1h, and 12h bots
- Supports individual error handling and auto-restart
- Respects shared `DRY_RUN` environment variable

#### 2. Azure VM Deployment
✅ **Status**: Configured
- Direct Python deployment on Azure VM
- All bot versions run as background processes
- Shares `paper_trading_outputs` directory for 24h outputs
- Resource limits managed by VM size

#### 3. Backend API (`backend/main.py`)
✅ **Status**: Full API support
- All endpoints accept `24h` version parameter:
  - `/api/bots/status` - Bot status and health
  - `/api/bots/24h/equity` - Equity curve and metrics
  - `/api/bots/24h/signals` - Trading signals
  - `/api/bots/24h/executions` - Execution logs
  - `/api/bots/24h/health` - Health metrics
  - `/api/bots/24h/bandit` - Bandit statistics
  - `/api/bots/24h/overlay` - Overlay signals
- Dashboard summary includes 24h bot data

#### 4. Module Structure
✅ **Status**: Properly isolated
```
live_demo_24h/
├── main.py               # Main trading loop (uses ops from root)
├── config.json          # Daily timeframe config (interval: 1d)
├── config_overlay.json  # Overlay config (disabled by default)
├── features.py          # Daily feature computation
├── market_data.py       # Binance API integration
├── ops/                 # Operational modules (BMA, logging, routing)
│   ├── bma.py
│   ├── log_router.py
│   ├── log_emitter.py
│   └── llm_logging.py
├── assets/              # Cohort CSVs
├── models/              # ML artifacts
└── ...                  # Other modules (copied from live_demo)
```

### Shared Infrastructure

#### Ops Module
The 24h bot uses the **root-level `ops/` module** for:
- `log_emitter`: Structured logging with sanitization
- `log_router`: Topic-based routing (emitter/llm/sheets)
- `llm_logging`: Compact JSONL with IST timestamps
- `bma`: BMA ensemble weight computation

This ensures consistency across all bot versions.

#### Outputs
Each bot writes to its own subdirectory:
- 5m: `paper_trading_outputs/5m/`
- 1h: `paper_trading_outputs/1h/`
- 12h: `paper_trading_outputs/12h/`
- **24h**: `paper_trading_outputs/24h/` ✅

Within each directory:
- `logs/` - Partitioned JSONL.gz logs
- `sheets_fallback/` - CSV backups (equity, signals, executions, etc.)

## Configuration Highlights

### Daily-Specific Settings (`config.json`)
```json
{
  "data": {
    "interval": "1d",           // Daily candles
    "warmup_bars": 1000          // 1000 days history
  },
  "execution": {
    "health_emit_every_bars": 1  // Emit health each daily bar
  },
  "overlay": {
    "enabled": false,            // Disabled by default
    "timeframes": ["1d"]         // Single timeframe (no multi-TF)
  },
  "cohorts": {
    "top_file": "live_demo_24h/assets/top_cohort.csv",
    "bottom_file": "live_demo_24h/assets/bottom_cohort.csv"
  },
  "artifacts": {
    "latest_manifest": "live_demo_24h/models/LATEST.json"
  }
}
```

### Feature Computation
- `LiveFeatureComputer(timeframe="1d")` in `main.py`
- Rolling windows adjusted for daily bars
- RV/volatility computed over daily returns

## Running the 24H Bot

### Standalone (Local)
```powershell
# Set environment
$env:LIVE_DEMO_CONFIG = "live_demo_24h\config.json"
$env:PAPER_TRADING_ROOT = "paper_trading_outputs\24h"

# Run
python -m live_demo_24h.main
```

### Unified Runner (All Bots)
```powershell
# Runs 5m, 1h, 12h, AND 24h concurrently
python run_unified_bots.py
```

### Azure VM Deployment
```bash
# Deploy to Azure VM (all bots including 24h)
./deploy_vm.sh
```

## Validation Checklist

### ✅ Integration
- [x] Unified runner includes 24h task
- [x] Azure VM deployment includes 24h bot
- [x] Frontend API recognizes `24h` version
- [x] Healthcheck verifies 24h module import
- [x] Shared ops module for consistency

### ✅ Configuration
- [x] Interval set to `1d`
- [x] Output root points to `24h/`
- [x] Cohort/creds/manifests use 24h paths
- [x] Health emits per daily bar
- [x] Feature computer uses daily timeframe

### ✅ Functionality
- [x] All modules copied from live_demo
- [x] Imports updated to `live_demo_24h.*`
- [x] Log routing via shared ops
- [x] Bandit state isolated per bot
- [x] Execution tracking and PnL attribution

### ⚠️ Prerequisites
Before running, ensure these exist:
- [ ] `live_demo_24h/hyperliquid-473106-b11ba8ae73b4.json` (credentials)
- [ ] `live_demo_24h/assets/top_cohort.csv` (cohort addresses)
- [ ] `live_demo_24h/assets/bottom_cohort.csv` (cohort addresses)
- [ ] `live_demo_24h/models/LATEST.json` (model manifest)
- [ ] Trained model artifacts referenced in manifest

## Expected Behavior

### Timing
- **Bar Close**: Once per UTC day at 00:00:00
- **Warmup**: Fetches 1000 daily bars (~3 years history)
- **Health Emission**: Every daily bar (not every 60 bars)
- **Idle Time**: 23+ hours between bars (by design)

### Trade Frequency
- Daily timeframe means **much lower turnover** than 5m/1h
- Expected: 0-3 trades per week (depending on signals)
- Cost/impact dynamics favor larger, less frequent trades
- Ideal for swing/position trading strategies

### Metrics Differences
- **Sharpe Annualization**: Uses sqrt(252) for daily returns
- **Volatility Window**: 50-day realized vol (vs 50 bars at 5m)
- **IC Window**: 200-day (vs 200 5m bars)
- **Turnover**: Much lower bps/day due to lower frequency

## Troubleshooting

### Import Errors
If you see `ImportError: No module named 'live_demo_24h'`:
- Ensure running from repo root
- Check `PYTHONPATH` includes project root
- Verify `live_demo_24h/__init__.py` exists

### No Data After Hours
This is **normal** for daily timeframe. The bot:
- Waits for Binance to close the UTC day candle
- Polls every 1-2 seconds but returns `None` until close
- Processes exactly once per day

### Ops Module Conflicts
If you see dual import warnings:
- The bot uses **root-level `ops/`** (shared)
- Local `live_demo_24h/ops/` is a fallback copy
- Prefer root for consistency across all bots

### Missing Credentials
Copy from existing bot:
```powershell
Copy-Item live_demo\hyperliquid-*.json live_demo_24h\
```

### Missing Cohorts
Copy from existing bot:
```powershell
Copy-Item live_demo\assets\*.csv live_demo_24h\assets\
```

### Missing Models
Either:
1. Point to shared models: `"latest_manifest": "live_demo/models/LATEST.json"`
2. Train daily-specific models and place in `live_demo_24h/models/`

## Performance Considerations

### Resource Usage
- **Memory**: ~500MB (lower than 5m due to less state)
- **CPU**: Minimal (1 bar/day = negligible compute)
- **Disk**: 24h outputs are smallest (1 row/day vs 288/day for 5m)

### Concurrency
Running all 4 bots concurrently:
- **Total Memory**: ~3GB (5m is heaviest)
- **Total CPU**: <1 core average (spikes at bar closes)
- **Network**: Shared API calls (Binance, Hyperliquid)

### Scalability
The 4-bot setup is production-ready:
- Independent state and outputs
- Shared logging infrastructure
- Isolated bandit arms per timeframe
- No cross-contamination

## Next Steps

1. **Copy Prerequisites**:
   ```powershell
   Copy-Item live_demo\hyperliquid-*.json live_demo_24h\
   Copy-Item live_demo\assets\*.csv live_demo_24h\assets\
   ```

2. **Verify Config**:
   ```powershell
   cat live_demo_24h\config.json | Select-String interval
   # Should show: "interval": "1d"
   ```

3. **Dry Run (One-Shot)**:
   ```powershell
   $env:LIVE_DEMO_ONE_SHOT = "true"
   python -m live_demo_24h.main
   ```

4. **Check Outputs**:
   ```powershell
   ls paper_trading_outputs\24h\sheets_fallback\
   # Should see equity_24h.csv, signals_24h.csv, etc.
   ```

5. **Enable in Unified Runner**:
   ```powershell
   python run_unified_bots.py
   # Logs should show "24-hour version: live_demo_24h/config.json"
   ```

6. **Monitor via API**:
   ```bash
   curl http://localhost:8000/api/bots/status
   # Should include "24h" in response
   ```

## Summary

✅ **Fully Integrated**: The 24h bot is now a first-class citizen alongside 5m, 1h, and 12h.

✅ **Isolated Outputs**: Each bot writes to its own `paper_trading_outputs/{version}/` directory.

✅ **Shared Infrastructure**: Uses common ops, API, and Azure VM deployment.

✅ **Daily Timeframe**: Properly configured for 1d candles, daily features, and lower turnover.

**Ready to run!** Just add credentials, cohorts, and models, then launch via unified runner or standalone.
