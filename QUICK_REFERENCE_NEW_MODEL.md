# 5M NEW MODEL - QUICK REFERENCE CARD

## ✅ MODEL STATUS
- **Deployed:** Jan 2, 2026, 11:13 AM IST
- **Accuracy:** 64.95% (vs old 43.05%)
- **Improvement:** +51% better
- **Status:** ✅ READY

## 🚀 QUICK COMMANDS

### Monitor Performance:
```powershell
python monitor_new_model.py
```

### Restart Bot:
```powershell
python run_5m.py
```

### Rollback (if needed):
```powershell
cp live_demo/models/backup/backup_*/​* live_demo/models/
python run_5m.py
```

## ⏰ CHECK SCHEDULE

| Time | Action |
|------|--------|
| **Now - 6h** | Check every 30 min |
| **6h - 24h** | Check every 2 hours |
| **24h - 48h** | Check every 4 hours |
| **48h+** | Make decision |

## 🎯 SUCCESS CRITERIA

### After 6 hours:
- ✅ At least 1 BUY and 1 SELL trade
- ✅ No bot errors

### After 24 hours:
- ✅ Win rate > 45%
- ✅ P&L >= $0
- ✅ 10+ trades

### After 48 hours:
- ✅ Win rate >= 50%
- ✅ P&L > $0
- ✅ Better than old model

## 🚨 STOP SIGNALS

**Rollback if:**
- ❌ P&L < -$100 after 48h
- ❌ Win rate < 40%
- ❌ Only BUY or only SELL (not both)
- ❌ Bot crashes repeatedly

## 📊 WHAT TO CHECK

1. **Total P&L** - Should be positive
2. **Win Rate** - Should be >= 50%
3. **BUY/SELL Balance** - Both should exist
4. **Confidence** - Should be > 0.5

## ✅ EXPECTED RESULTS

**Old Model:**
- Accuracy: 43%
- Win Rate: ~40%
- P&L: Negative

**New Model (Expected):**
- Accuracy: 65%
- Win Rate: ~50-55%
- P&L: Positive

**Improvement:** ~51% better!

---

**Next Check:** 30 minutes from deployment
**Command:** `python monitor_new_model.py`
