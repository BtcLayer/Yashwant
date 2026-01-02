# MetaStackerBandit Archives Summary

**Generated:** January 2, 2026 at 14:12

---

## 📦 Archive 1: Source Code

**Filename:** `MetaStackerBandit_source_2026-01-02_135659.zip`  
**Size:** ~38 MB  
**Type:** Clean source code only

### Contents
- ✅ All Python source files (`.py`)
- ✅ Shell scripts (`.sh`, `.bat`, `.ps1`)
- ✅ Documentation (`.md` files)
- ✅ Configuration files (`config.json`, `requirements.txt`, `.env.example`)
- ✅ Frontend source code (React app)
- ✅ Backend API code
- ✅ All 4 timeframe bots (5m, 1h, 12h, 24h)
- ✅ Notebooks, tests, tools, scripts
- ✅ CI/CD workflows (`.github/`)

### Excluded
- ❌ Dependencies (`.venv`, `node_modules`)
- ❌ Data files (`.csv`, `.rar`)
- ❌ Logs (`.log`, `.jsonl`)
- ❌ Git history (`.git`)
- ❌ Previous archives
- ❌ Temporary files

### Use Case
Perfect for:
- Code review
- Setting up on a new machine
- Version control
- Sharing with developers
- Clean deployment

---

## 📊 Archive 2: Logs & Emitters

**Filename:** `MetaStackerBandit_logs_emitters_2026-01-02_141214.zip`  
**Size:** ~96.33 MB  
**Type:** Trading data and logs

### Contents

#### 1. System Logs (`logs/`)
- `5m.log`, `5m_err.log`, `5m_out.log` - 5-minute bot logs
- `1h.log`, `1h_err.log`, `1h_out.log` - 1-hour bot logs
- `12h.log`, `12h_err.log`, `12h_out.log` - 12-hour bot logs
- `24h.log`, `24h_err.log`, `24h_out.log` - 24-hour bot logs
- `5m_startup.log` - Startup diagnostics

#### 2. Paper Trading Outputs (`paper_trading_outputs/`)

**5m Timeframe** (ACTIVE - Most Recent)
- **Files:** 32
- **Date Range:** Dec 1, 2025 → **Jan 2, 2026 14:10** ✨
- **Status:** Currently running
- **Data:**
  - `signals.csv` - Trading signals (518 KB)
  - `equity.csv` - Equity tracking (210 KB)
  - `bandit.csv` - Bandit algorithm data (109 KB)
  - `hyperliquid_sheet.csv` - Exchange data
  - `mood_debug.csv` - Market mood analysis (117 KB)
  - Additional CSV/JSON files

**1h Timeframe**
- **Last Update:** Dec 30, 2025 17:33
- **Data:**
  - `signals_1h.csv` (54 KB)
  - `equity_1h.csv`
  - `hyperliquid_sheet_1h.csv`

**12h Timeframe**
- **Last Update:** Dec 29, 2025 12:05
- **Data:**
  - `overlay_12h.csv` (12 KB)

**24h Timeframe**
- **Last Update:** Dec 23, 2025 17:05
- **Data:**
  - `equity_24h.csv` (1.84 KB)

#### 3. Emitter Source Code (`emitters_code/`)
- `live_demo/` - 5m emitter code
  - `production_emitter.py`
  - `health_snapshot_emitter.py`
  - `__init__.py`
- `live_demo_1h/` - 1h emitter code
- `live_demo_12h/` - 12h emitter code
- `live_demo_24h/` - 24h emitter code

#### 4. Documentation
- `ARCHIVE_INFO.md` - Detailed archive information and date ranges

### Use Case
Perfect for:
- Performance analysis
- Debugging trading issues
- Historical data review
- Monitoring bot behavior
- Backtesting validation
- Understanding emitter logic

---

## 📈 Key Findings from Data Analysis

### Active Bot Status (as of Jan 2, 2026 14:10)

| Timeframe | Status | Last Update | Notes |
|-----------|--------|-------------|-------|
| **5m** | 🟢 **ACTIVE** | Jan 2, 2026 14:10 | Running for 2h40m+ |
| **1h** | 🟡 Inactive | Dec 30, 2025 17:33 | 3 days old |
| **12h** | 🟡 Inactive | Dec 29, 2025 12:05 | 4 days old |
| **24h** | 🟡 Inactive | Dec 23, 2025 17:05 | 10 days old |

### Data Freshness
- ✅ **5m bot is actively trading** - Latest data is from today (Jan 2, 2026)
- ⚠️ Other timeframes appear to be stopped or not running
- 📊 5m has the most comprehensive dataset (32 files)

### File Sizes (5m - Most Active)
- Signals: 518 KB (largest - lots of trading activity)
- Equity: 210 KB
- Mood Debug: 117 KB
- Bandit: 109 KB

---

## 🎯 Recommendations

### For Development
1. **Use the source code archive** (`MetaStackerBandit_source_2026-01-02_135659.zip`)
2. Extract and set up environment
3. Install dependencies from `requirements.txt`
4. Configure `.env` from `.env.example`

### For Analysis
1. **Use the logs/emitters archive** (`MetaStackerBandit_logs_emitters_2026-01-02_141214.zip`)
2. Focus on `paper_trading_outputs/5m/` for latest data
3. Review `signals.csv` for trading patterns
4. Check `equity.csv` for performance metrics

### Next Steps
- ✅ 5m bot is running well - continue monitoring
- ⚠️ Consider restarting 1h, 12h, 24h bots if needed
- 📊 Analyze 5m performance from the latest data
- 🔍 Review logs for any errors or warnings

---

## 📝 Archive Locations

Both archives are saved in:
```
c:\Users\yashw\MetaStackerBandit\
```

Files:
1. `MetaStackerBandit_source_2026-01-02_135659.zip` (38 MB)
2. `MetaStackerBandit_logs_emitters_2026-01-02_141214.zip` (96.33 MB)

---

## 🔐 Security Notes

- ✅ No sensitive credentials included (`.env` excluded)
- ✅ Only `.env.example` template provided
- ✅ No private keys (`.pem` files excluded)
- ⚠️ Logs may contain API endpoints - review before sharing externally

---

**Total Archive Size:** ~134 MB  
**Compression Ratio:** Excellent (excluded ~500+ MB of dependencies and large data files)
