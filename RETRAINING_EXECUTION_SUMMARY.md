# PRODUCTION MODEL RETRAINING - EXECUTION SUMMARY

**Date:** 2026-01-06 15:34 IST  
**Status:** IN PROGRESS  
**Objective:** Fix all timeframe models with production-grade methodology

---

## WHAT WAS DONE

### 1. FORENSIC ANALYSIS COMPLETED ✓

**Findings:**
- **5m Model:** 91.5% neutral, confidence 0.175 (need 0.60), 0% eligible
- **1h Model:** NOT RUNNING (no signals file)
- **12h Model:** NOT RUNNING (no signals file)
- **24h Model:** 100% BUY bias, confidence 0.134, ZERO variance (broken)

**Root Causes Identified:**
1. **Class Imbalance:** Training data heavily skewed to neutral
2. **Poor Calibration:** Sigmoid calibration on 3-class problem
3. **Wrong Objective:** Optimizing accuracy instead of trading utility
4. **Feature Leakage:** 24h model has constant output (leaked features)
5. **Timeframe Mismatch:** Same methodology for all timeframes

### 2. PRODUCTION REQUIREMENTS DEFINED ✓

**Per-Timeframe Targets:**

| Timeframe | Role | Class Dist | Conf Mean | Eligibility |
|-----------|------|------------|-----------|-------------|
| 5m | Execution | 40/20/40 | ≥0.65 | ≥30% |
| 1h | Tactical | 45/10/45 | ≥0.60 | ≥30% |
| 12h | Regime | 40/20/40 | ≥0.55 | ≥25% |
| 24h | Strategic | 45/10/45 | ≥0.50 | ≥25% |

### 3. PRODUCTION SCRIPTS CREATED ✓

**Files Created:**
- `PRODUCTION_RETRAINING_PLAN.md` - Complete methodology document
- `retrain_5m_production_v2.py` - 5m model retraining
- `retrain_1h_production.py` - 1h model retraining
- `retrain_12h_production.py` - 12h model retraining (pending)
- `retrain_24h_production.py` - 24h model retraining (pending)
- `retrain_all_timeframes.py` - Unified execution script
- `forensic_analysis.py` - Multi-timeframe diagnostic tool

**Script Features:**
- Adaptive volatility-based labeling
- Intelligent class balancing (NOT naive oversampling)
- Timeframe-appropriate feature engineering
- Ensemble architecture (RF + XGB + LR → Meta → Calibrated)
- Separate calibration set with isotonic method
- Strict validation against requirements
- **FAIL-LOUD** if quality checks don't pass
- Automatic backup before deployment

### 4. RETRAINING METHODOLOGY

**Key Improvements Over Previous Approach:**

#### Old (Broken) Method:
```python
# Naive labeling
df['target'] = 0
df.loc[df['returns'] > 0.01, 'target'] = 1
df.loc[df['returns'] < -0.01, 'target'] = -1

# No class balancing
model.fit(X, y)

# Poor calibration
calibrator = CalibratedClassifierCV(model, method='sigmoid', cv=3)
```

**Problems:**
- Fixed threshold → Most samples labeled neutral
- No balancing → Model learns majority class
- Sigmoid calibration → Breaks for 3-class
- CV=3 → Overfits calibration

#### New (Production) Method:
```python
# Adaptive labeling
df['threshold'] = df['realized_vol'] * 1.5  # Volatility-adjusted
df['target'] = 0
df.loc[df['forward_return'] > df['threshold'], 'target'] = 1
df.loc[df['forward_return'] < -df['threshold'], 'target'] = -1

# Intelligent class balancing
target_dist = {-1: 0.40, 0: 0.20, 1: 0.40}
sample_weights = compute_class_weights(y, target_dist)

# Proper calibration
calibrator = CalibratedClassifierCV(
    meta_model,
    method='isotonic',  # Better for multi-class
    cv='prefit'  # Use separate calibration set
)
calibrator.fit(X_cal, y_cal)  # Separate set!
```

**Benefits:**
- Adaptive threshold → Balanced labels
- Sample weighting → Achieves target distribution
- Isotonic calibration → Proper for 3-class
- Separate cal set → No overfitting

### 5. VALIDATION FRAMEWORK

**Strict Requirements Enforced:**

```python
# Example for 5m:
REQUIREMENTS = {
    'min_down_pct': 0.30,      # At least 30% DOWN predictions
    'max_down_pct': 0.45,      # At most 45% DOWN predictions
    'min_up_pct': 0.30,        # At least 30% UP predictions
    'max_up_pct': 0.45,        # At most 45% UP predictions
    'max_neutral_pct': 0.40,   # At most 40% NEUTRAL
    'min_conf_mean': 0.65,     # Mean confidence ≥ 0.65
    'min_pct_above_conf_060': 0.40,  # 40% of signals with conf ≥ 0.60
    'min_alpha_mean': 0.12,    # Mean alpha ≥ 12%
    'min_eligibility_pct': 0.30  # 30% of signals eligible for trading
}
```

**If ANY requirement fails → Script exits with error code 1**

No deployment of broken models!

---

## CURRENT STATUS

### 5m Model Retraining: IN PROGRESS

**Command Running:**
```bash
.\.venv\Scripts\python.exe retrain_5m_production_v2.py
```

**Expected Duration:** 5-10 minutes

**Steps:**
1. [RUNNING] Fetch 90 days of 5m data from Hyperliquid
2. [PENDING] Compute 17 technical features
3. [PENDING] Adaptive labeling with volatility-based thresholds
4. [PENDING] 70/15/15 train/cal/test split
5. [PENDING] Class balancing to 40/20/40
6. [PENDING] Train ensemble (RF + XGB + LR)
7. [PENDING] Validate against requirements
8. [PENDING] Deploy if validation passes

**Possible Outcomes:**
- ✓ **SUCCESS:** Model meets all requirements → Deployed
- ✗ **VALIDATION FAILED:** Model doesn't meet requirements → NOT deployed, script exits
- ✗ **ERROR:** Data fetch or training error → Script exits with error

### 1h, 12h, 24h Models: PENDING

Will be executed after 5m completes (if using unified script) or manually.

---

## WHAT HAPPENS AFTER RETRAINING

### If 5m Retraining Succeeds:

1. **New model files created:**
   ```
   live_demo/models/
   ├── meta_classifier_20260106_HHMMSS_d7a9e9fb3a42.joblib
   ├── calibrator_20260106_HHMMSS_d7a9e9fb3a42.joblib
   ├── feature_columns_20260106_HHMMSS_d7a9e9fb3a42.json
   ├── training_meta_20260106_HHMMSS_d7a9e9fb3a42.json
   └── LATEST.json (updated)
   ```

2. **Old model backed up:**
   ```
   live_demo/models/backup/backup_20260106_HHMMSS/
   └── LATEST.json (old version)
   ```

3. **Deployment steps (MANUAL):**
   ```bash
   # Stop bot
   Ctrl+C in terminal running bot
   
   # Clear stale cache
   Remove-Item paper_trading_outputs\cache\BTCUSDT_5m_*.csv
   
   # Restart bot
   .\.venv\Scripts\python.exe -m live_demo.main
   
   # Monitor for 30-60 minutes
   .\.venv\Scripts\python.exe monitor_5m_realtime_dashboard.py
   ```

4. **Expected behavior:**
   - Signals will have confidence ≥ 0.60 (40%+ of them)
   - Class distribution: ~40% UP, ~40% DOWN, ~20% NEUTRAL
   - Trades will execute (not all neutral)
   - BUY/SELL balance maintained
   - Eligibility rate ≥ 30%

### If 5m Retraining Fails:

**Validation Failure:**
```
VALIDATION FAILED - MODEL DOES NOT MEET REQUIREMENTS
Model training completed but validation failed.
This model will NOT be deployed.

Recommendations:
1. Adjust class balancing weights
2. Increase training data
3. Tune model hyperparameters
4. Review labeling logic
```

**What to do:**
1. Review console output to see which requirement failed
2. Adjust parameters in script
3. Re-run retraining
4. **DO NOT** lower requirements or adjust thresholds

**Common Failure Modes:**
- Insufficient training data → Fetch more days
- Market regime change → Adjust labeling threshold multiplier
- Feature quality → Review feature engineering
- Class imbalance too severe → Adjust target distribution

---

## MONITORING CHECKLIST

### After Deployment (First Hour):

- [ ] Bot starts without errors
- [ ] Models load successfully
- [ ] Signals are generated every 5 minutes
- [ ] Confidence distribution matches validation
- [ ] Trades execute (not all neutral)
- [ ] BUY and SELL trades both appear
- [ ] No Python warnings in logs
- [ ] Eligibility rate ≥ 30%

### After Deployment (First Day):

- [ ] Win rate > 40%
- [ ] Total PnL positive or near-zero
- [ ] No model degradation
- [ ] Class distribution stable
- [ ] Confidence remains high
- [ ] No recurring errors

### Red Flags:

- ⚠️ All trades are BUY or all SELL
- ⚠️ No trades executing (all neutral)
- ⚠️ Confidence dropping below 0.60
- ⚠️ Win rate < 30%
- ⚠️ Python errors in logs
- ⚠️ Model predictions constant

**If red flags appear:** STOP bot, investigate, potentially revert to backup.

---

## ROLLBACK PROCEDURE

If new model performs poorly:

```bash
# 1. Stop bot
Ctrl+C

# 2. Find backup
ls live_demo/models/backup/

# 3. Restore old LATEST.json
cp live_demo/models/backup/backup_TIMESTAMP/LATEST.json live_demo/models/LATEST.json

# 4. Restart bot
.\.venv\Scripts\python.exe -m live_demo.main
```

---

## NEXT STEPS

### Immediate (Now):
1. ⏳ Wait for 5m retraining to complete
2. ✓ Review validation output
3. ✓ If passed, proceed to deployment
4. ✓ If failed, review and adjust

### Short-term (Today):
1. Retrain 1h, 12h, 24h models
2. Deploy all models
3. Monitor for 2-4 hours
4. Verify system stability

### Medium-term (This Week):
1. Run backtests on new models
2. Compare performance vs old models
3. Document any issues
4. Create automated retraining schedule

### Long-term (Ongoing):
1. Monitor model drift
2. Retrain monthly or when performance degrades
3. Maintain model quality standards
4. Never deploy models that fail validation

---

## FILES REFERENCE

### Analysis Documents:
- `PRODUCTION_RETRAINING_PLAN.md` - Complete methodology
- `forensic_analysis_results.json` - Current state analysis
- `forensic_report.txt` - Detailed forensic output

### Retraining Scripts:
- `retrain_5m_production_v2.py` - 5m model (RUNNING)
- `retrain_1h_production.py` - 1h model
- `retrain_all_timeframes.py` - Unified runner

### Monitoring Tools:
- `monitor_5m_realtime_dashboard.py` - Live monitoring
- `quick_5m_status.py` - Quick status check
- `forensic_analysis.py` - Multi-timeframe diagnostic

### Diagnostic Reports:
- `step1_output.txt` - Model prediction analysis
- `step2_output.txt` - Decision logic analysis
- `step3_output.txt` - Data freshness analysis
- `model_investigation.txt` - Model change timeline
- `yesterday_vs_today.txt` - Day-over-day comparison

---

## CONTACT & ESCALATION

**If retraining fails repeatedly:**
1. Check data quality (Hyperliquid API)
2. Verify feature engineering logic
3. Review labeling thresholds
4. Consider market regime change
5. Escalate to senior quant team

**Success Criteria:**
- All validation checks pass
- Model deployed successfully
- Bot generates balanced signals
- Trades execute profitably
- System stable for 24+ hours

---

**Status:** Awaiting 5m retraining completion...
**Next Update:** After 5m validation results available
