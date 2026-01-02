# 📦 Quick Reference - MetaStackerBandit Archives

**Created:** January 2, 2026

---

## Your Archives

### 1️⃣ Source Code Archive
```
MetaStackerBandit_source_2026-01-02_135659.zip
Size: ~38 MB
```

**What's inside:**
- Complete source code (all .py files)
- Frontend & Backend code
- All 4 timeframe bots (5m, 1h, 12h, 24h)
- Configuration files
- Documentation
- Scripts & tools

**What's NOT inside:**
- No dependencies (.venv, node_modules)
- No data files (.csv)
- No logs
- No git history

**Use for:** Setting up on new machine, code review, deployment

---

### 2️⃣ Logs & Emitters Archive
```
MetaStackerBandit_logs_emitters_2026-01-02_141214.zip
Size: ~96 MB
```

**What's inside:**
- System logs (all timeframes)
- Paper trading outputs
- Trading signals & equity data
- Emitter source code

**Data Dates:**
- 5m: Dec 1, 2025 → **Jan 2, 2026 14:10** ✅ ACTIVE
- 1h: Up to Dec 30, 2025
- 12h: Up to Dec 29, 2025
- 24h: Up to Dec 23, 2025

**Use for:** Performance analysis, debugging, historical review

---

## 🎯 Quick Actions

### To Set Up Project Elsewhere:
1. Extract `MetaStackerBandit_source_2026-01-02_135659.zip`
2. Create virtual environment: `python -m venv .venv`
3. Activate: `.venv\Scripts\activate`
4. Install: `pip install -r requirements.txt`
5. Configure: Copy `.env.example` to `.env` and edit

### To Analyze Trading Performance:
1. Extract `MetaStackerBandit_logs_emitters_2026-01-02_141214.zip`
2. Navigate to `paper_trading_outputs/5m/`
3. Open `signals.csv` for trading signals
4. Open `equity.csv` for P&L tracking
5. Check logs in `logs/` folder

---

## 📊 Current Status (from logs analysis)

**5m Bot:** 🟢 RUNNING (last update: Jan 2, 2026 14:10)
- Currently active and trading
- Running for 2h40m+
- Latest data available

**Other Bots:** 🟡 INACTIVE
- 1h: Last ran Dec 30
- 12h: Last ran Dec 29
- 24h: Last ran Dec 23

---

## 📁 File Locations

Both files are in:
```
c:\Users\yashw\MetaStackerBandit\
```

---

## 📖 More Info

See `ARCHIVES_SUMMARY.md` for detailed information
See `SOURCE_ARCHIVE_README.md` for source code details
