# ✅ Compact Logs & Emitted Data Archive - FINAL

**Archive:** `MetaStackerBandit_logs_data_2026-01-02_153356.zip`  
**Size:** **0.28 MB** ✅ (Well under 30MB target!)  
**Created:** January 2, 2026 at 15:33:56

---

## 📦 What's Inside

### ✅ YES - Included

#### 1. **System Logs** (All Timeframes)
- `5m.log`, `5m_err.log`, `5m_out.log` - 5-minute bot logs
- `1h.log`, `1h_err.log`, `1h_out.log` - 1-hour bot logs
- `12h.log`, `12h_err.log`, `12h_out.log` - 12-hour bot logs
- `24h.log`, `24h_err.log`, `24h_out.log` - 24-hour bot logs
- `5m_startup.log` - Startup diagnostics
- `unified_runner_*.log` - Unified runner logs

#### 2. **Emitted Trading Data** (All Timeframes)

**5m Timeframe** (Most Active - Latest Data)
- `signals.csv` (519 KB) - All trading signals
- `equity.csv` - Equity tracking
- `bandit.csv` - Bandit algorithm data
- `mood_debug.csv` (118 KB) - Market mood analysis
- `executions_paper.csv` - Trade executions
- `decisions.csv` - Trading decisions
- `signals_dedup.csv` (25 KB) - Deduplicated signals
- `oof_calibration.csv` (4.76 KB) - Out-of-fold calibration
- `system_alerts.csv` (0.44 KB) - System alerts
- Various JSON files (config, summaries, metadata)

**1h, 12h, 24h Timeframes**
- Similar CSV/JSON files for each timeframe
- Historical trading data

#### 3. **Summary Files**
- `README.md` - Archive documentation
- JSON summary files (gates, calibration, turnover reports)

---

### ❌ NO - Excluded (to keep under 30MB)

- ❌ Python source code (`.py` files)
- ❌ `hyperliquid_sheet.csv` (26+ MB - raw exchange data)
- ❌ Compressed archives (`*.jsonl.gz`)
- ❌ Large JSON logs (`*.jsonl`)
- ❌ `funding_debug.json` (6+ MB)
- ❌ Files over 5MB
- ❌ Dependencies, models, build files

---

## 📊 Data Coverage

| Timeframe | Logs | Emitted Data | Status |
|-----------|------|--------------|--------|
| **5m** | ✅ Yes | ✅ Yes (Latest: Jan 2, 2026) | 🟢 ACTIVE |
| **1h** | ✅ Yes | ✅ Yes | 🟡 Inactive |
| **12h** | ✅ Yes | ✅ Yes | 🟡 Inactive |
| **24h** | ✅ Yes | ✅ Yes | 🟡 Inactive |

---

## 🎯 What You Can Do With This Archive

### For Performance Analysis
1. Extract the archive
2. Navigate to `emitted_data/5m/`
3. Open `signals.csv` - See all trading signals
4. Open `equity.csv` - Track P&L and equity
5. Open `mood_debug.csv` - Analyze market conditions

### For Debugging
1. Check `logs/` folder
2. Review `5m_err.log` for errors
3. Check `5m_startup.log` for initialization issues
4. Review unified runner logs for multi-timeframe issues

### For Historical Review
1. Compare data across timeframes (5m, 1h, 12h, 24h)
2. Analyze signal quality and execution
3. Review calibration data
4. Check system alerts

---

## 📈 Key Files to Review

**Most Important:**
1. **`emitted_data/5m/signals.csv`** (519 KB) - All trading signals with timestamps
2. **`emitted_data/5m/equity.csv`** - P&L tracking and performance
3. **`logs/5m_err.log`** - Any errors from the 5m bot
4. **`emitted_data/5m/mood_debug.csv`** (118 KB) - Market regime analysis

**For Deep Analysis:**
- `executions_paper.csv` - Actual trade executions
- `decisions.csv` - Decision-making process
- `bandit.csv` - Multi-armed bandit algorithm behavior
- `oof_calibration.csv` - Model calibration metrics

---

## 💡 Why So Small?

The archive is only **0.28 MB** because:
- ✅ Excluded the 26MB `hyperliquid_sheet.csv` (raw exchange data)
- ✅ Excluded compressed archives (3-4 MB each)
- ✅ Excluded 6MB `funding_debug.json`
- ✅ No Python source code
- ✅ Only essential CSV/JSON trading data
- ✅ Focused on actionable data for analysis

**Result:** All the important logs and trading data you need, in a tiny package!

---

## 📁 Archive Structure

```
MetaStackerBandit_logs_data_2026-01-02_153356.zip
├── logs/
│   ├── 5m.log, 5m_err.log, 5m_out.log
│   ├── 1h.log, 1h_err.log, 1h_out.log
│   ├── 12h.log, 12h_err.log, 12h_out.log
│   ├── 24h.log, 24h_err.log, 24h_out.log
│   ├── 5m_startup.log
│   └── unified_runner_*.log
├── emitted_data/
│   ├── 5m/
│   │   ├── signals.csv (519 KB)
│   │   ├── equity.csv
│   │   ├── bandit.csv
│   │   ├── mood_debug.csv (118 KB)
│   │   ├── executions_paper.csv
│   │   ├── decisions.csv
│   │   └── *.json files
│   ├── 1h/
│   ├── 12h/
│   └── 24h/
└── README.md
```

---

## ✅ Summary

**Perfect for:**
- ✅ Quick performance review
- ✅ Debugging trading issues
- ✅ Analyzing signal quality
- ✅ Sharing with team (tiny file size!)
- ✅ Historical data analysis

**Contains:**
- ✅ All system logs from all timeframes
- ✅ All emitted trading data (CSV/JSON)
- ✅ Latest data from Jan 2, 2026
- ✅ No unnecessary files

**File Location:**
```
c:\Users\yashw\MetaStackerBandit\MetaStackerBandit_logs_data_2026-01-02_153356.zip
```

---

**🎉 Success!** You now have a compact, complete archive of all logs and emitted trading data from all timeframes, ready for analysis or sharing!
