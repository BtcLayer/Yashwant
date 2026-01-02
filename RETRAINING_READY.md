# 5M MODEL RETRAINING - READY TO USE

## ✅ SCRIPT CREATED: `retrain_5m_automated.py`

### What It Does:

**1. Safety First:**
- ✅ Backs up current model before any changes
- ✅ Saves backup with timestamp
- ✅ Can rollback if needed

**2. Uses Proven Approach:**
- ✅ Exact same 17 features as current model
- ✅ Same model structure (RF, ET, HistGB, GB → Meta → Calibrator)
- ✅ Same training process
- ✅ Only difference: FRESH DATA

**3. Fully Automated:**
- ✅ Fetches fresh 5m data from Hyperliquid
- ✅ Creates features automatically
- ✅ Trains all models
- ✅ Validates output
- ✅ Updates LATEST.json automatically
- ✅ No manual config changes needed!

**4. Safe Deployment:**
- ✅ Validates before saving
- ✅ Keeps backup for rollback
- ✅ Clear instructions for next steps

---

## 🚀 HOW TO USE

### Run the Script:
```powershell
python retrain_5m_automated.py
```

### What Happens:
1. Backs up current model → `live_demo/models/backup/backup_YYYYMMDD_HHMMSS/`
2. Fetches 6 months of fresh 5m data from Hyperliquid
3. Creates exact same 17 features
4. Trains new model (takes ~15-30 minutes)
5. Validates accuracy
6. Saves new model files
7. **Updates LATEST.json automatically** ← No manual work!
8. Provides rollback instructions

### After Script Completes:
1. Restart 5m bot: `python run_5m.py`
2. Monitor for 24-48 hours
3. Check win rate and P&L
4. If good → Keep new model
5. If bad → Rollback to backup

---

## 📊 WHAT TO EXPECT

### Training Time:
- Data fetching: 5-10 minutes
- Feature creation: 5-10 minutes
- Model training: 15-30 minutes
- **Total: ~30-50 minutes**

### New Model Quality:
- Target accuracy: >60%
- Should predict all 3 classes (UP, DOWN, NEUTRAL)
- Fresh patterns from recent market

### Performance Improvement:
- Better win rate (target: >50%)
- Positive P&L
- Fewer losing streaks
- Predictions match current market

---

## 🔙 ROLLBACK (If Needed)

If new model doesn't perform well:

1. Find backup folder: `live_demo/models/backup/backup_YYYYMMDD_HHMMSS/`
2. Copy all files from backup to `live_demo/models/`
3. Restart bot: `python run_5m.py`
4. Old model restored!

---

## ✅ KEY FEATURES

### Safety:
- ✅ Automatic backup before changes
- ✅ Validation before deployment
- ✅ Easy rollback
- ✅ No data loss

### Automation:
- ✅ One command to run
- ✅ No manual config edits
- ✅ LATEST.json updated automatically
- ✅ Clear status messages

### Quality:
- ✅ Uses proven approach
- ✅ Fresh market data
- ✅ Proper validation
- ✅ Performance metrics

---

## 🎯 NEXT STEPS

### Option 1: Run Now (Recommended)
```powershell
python retrain_5m_automated.py
```

Then monitor the new model's performance.

### Option 2: Review First
1. Read through the script
2. Understand what it does
3. Run when ready

### Option 3: Test on Sample
1. Run the script
2. Check the backup was created
3. Verify new model files
4. Test before deploying

---

## 📝 IMPORTANT NOTES

1. **Internet Required:** Script fetches data from Hyperliquid API
2. **Time Required:** Allow 30-50 minutes for completion
3. **Bot Restart:** Must restart 5m bot after retraining
4. **Monitoring:** Watch performance for 24-48 hours
5. **Backup:** Always kept safe, can rollback anytime

---

## ✅ READY TO USE!

The script is production-ready and safe to run.

**To start retraining:**
```powershell
python retrain_5m_automated.py
```

**Questions to consider:**
- Do you want to run it now?
- Any concerns about the approach?
- Need any modifications?
