# 🚀 Quick Reference: Model Training & Monitoring

## ✅ What's Running Now

- **5m Bot:** ✅ Running (1h 40m) - Original trained model
- **1h Bot:** ✅ Running (5m) - **NEWLY TRAINED MODEL**

---

## 📊 Check 1h Bot Health

```powershell
python check_1h_health.py
```

**Run this every 1-2 hours to monitor progress**

---

## 🎯 Your Plan

### ✅ Phase 1: Monitor 1h (CURRENT)
- Wait 24 hours
- Check signals every 1-2 hours
- Verify both BUY and SELL trades
- Confirm no crashes

### ⏳ Phase 2: Train 24h (If 1h Works)
1. Edit `train_model.py`:
   ```python
   TIMEFRAME = "24h"
   DATA_FILE = "ohlc_btc_24h.csv"
   ```
2. Run: `python train_model.py`
3. Start bot: `python run_24h.py`

### ⏳ Phase 3: Train 12h (If 1h Works)
1. Fetch 12h data first
2. Edit `train_model.py`:
   ```python
   TIMEFRAME = "12h"
   DATA_FILE = "ohlc_btc_12h.csv"
   ```
3. Run: `python train_model.py`
4. Start bot: `python run_12h.py`

---

## 🔍 What to Look For

### ✅ Good Signs:
- Signals every hour
- Both UP and DOWN predictions
- Both BUY and SELL trades
- No errors/crashes
- Win rate > 30%

### 🔴 Bad Signs:
- No signals after 2+ hours
- Only one direction (UP or DOWN only)
- Only BUY trades (no SELL)
- Bot crashes
- All trades losing

---

## 📁 Important Files

### Data Files:
- `ohlc_btc_1h.csv` - 1h training data ✅
- `ohlc_btc_24h.csv` - 24h training data ✅
- `ohlc_btc_12h.csv` - 12h training data (need to fetch)

### Training Scripts:
- `train_model.py` - Main training script
- `fetch_hyperliquid_data.py` - Get historical data

### Monitoring Scripts:
- `check_1h_health.py` - Check 1h bot status
- `monitor_1h_bot.py` - Monitor 1h activity

### Model Files (1h):
- `live_demo_1h/models/meta_classifier_*.joblib`
- `live_demo_1h/models/calibrator_*.joblib`
- `live_demo_1h/models/LATEST.json`

---

## ⏰ Timeline

**Now (12:56 PM):** 1h bot started  
**1:00 PM - 2:00 PM:** First signal expected  
**Every 2 hours:** Run health check  
**Tomorrow 1:00 PM:** 24h review → Decide on 24h/12h training

---

## 🆘 Quick Fixes

### If No Signals:
```powershell
# Check bot is running
# Look for "python run_1h.py" in terminal

# Restart if needed
# Stop current bot (Ctrl+C)
python run_1h.py
```

### If Only BUY Trades:
Edit `live_demo_1h/config.json`:
```json
"thresholds": {
  "require_consensus": false
}
```

---

## 📞 Summary

**Status:** 1h model trained and running ✅  
**Next:** Monitor for 24 hours ⏳  
**Then:** Train 24h and 12h if 1h works well ⏳  
**Goal:** All timeframes with proper models 🎯

---

**Check health:** `python check_1h_health.py`  
**Full details:** See `1H_MODEL_TRAINING_SESSION.md`
