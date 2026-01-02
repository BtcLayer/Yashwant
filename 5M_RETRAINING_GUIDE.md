# 5M MODEL RETRAINING - COMPLETE GUIDE

## 🎯 WHY RETRAINING IS NEEDED

### Current Situation:
- ✅ Consensus bug fixed (SELL trades now work)
- ❌ Bot still losing money
- ❌ Model predictions are not profitable
- **Conclusion:** Model needs retraining with correct labels/features

### Root Causes:
1. **Model Age:** 73 days old (Oct 18, 2025) - market conditions changed
2. **Low Accuracy:** ~43% training accuracy - not good enough
3. **Possible Issues:**
   - Inverted labels (UP/DOWN swapped)
   - Wrong target definition
   - Stale patterns
   - Poor feature engineering

---

## 📋 WHAT THE 5M MODEL NEEDS

### Required Features (17 total):
```
1. mom_1                  - 1-bar momentum
2. mom_3                  - 3-bar momentum  
3. mr_ema20_z             - Mean reversion z-score
4. rv_1h                  - Realized volatility
5. regime_high_vol        - High volatility regime flag
6. gk_volatility          - Garman-Klass volatility
7. jump_magnitude         - Price jump size
8. volume_intensity       - Volume relative to average
9. price_efficiency       - Price movement efficiency
10. price_volume_corr     - Price-volume correlation
11. vwap_momentum         - VWAP-based momentum
12. depth_proxy           - Order book depth proxy
13. funding_rate          - Funding rate
14. funding_momentum_1h   - Funding rate momentum
15. flow_diff             - Cohort flow difference
16. S_top                 - Top cohort signal
17. S_bot                 - Bottom cohort signal
```

### Model Structure:
```
Base Models (4):
├── RandomForestClassifier
├── ExtraTreesClassifier
├── HistGradientBoostingClassifier
└── GradientBoostingClassifier

Meta-Classifier:
└── LogisticRegression (trained on stacked predictions)

Final Model:
└── CalibratedClassifierCV (wraps meta-classifier)
```

### Target Variable:
- **Classes:** 0=DOWN, 1=NEUTRAL, 2=UP
- **Thresholds:** 
  - UP: future_return > +0.5%
  - DOWN: future_return < -0.5%
  - NEUTRAL: between -0.5% and +0.5%

---

## 🔧 RETRAINING PROCESS

### Step 1: Data Collection
- **Source:** Hyperliquid API
- **Timeframe:** 5-minute bars
- **Duration:** Last 6 months (~50,000+ bars)
- **Format:** OHLCV (Open, High, Low, Close, Volume)

### Step 2: Feature Engineering
- Create all 17 features using exact formulas
- Match the live bot's feature computation
- Handle missing values properly
- Ensure no look-ahead bias

### Step 3: Target Creation
- Calculate future returns
- Apply thresholds correctly
- **CRITICAL:** Ensure labels are NOT inverted
- Validate distribution (should have all 3 classes)

### Step 4: Model Training
1. Split data (80% train, 20% test, time-based)
2. Train 4 base models
3. Stack predictions (4 models × 3 classes = 12 features)
4. Train meta-classifier on stacked predictions
5. Calibrate with CalibratedClassifierCV

### Step 5: Validation
- Check accuracy on test set (target: >60%)
- Verify predicts all 3 classes
- Test on recent data
- Compare with old model

### Step 6: Deployment
- Backup old model
- Save new model files
- Update LATEST.json
- Restart bot
- Monitor for 24-48 hours

---

## ⚠️ CRITICAL SUCCESS FACTORS

### Must Get Right:
1. ✅ **Feature Engineering** - Exact match to live bot
2. ✅ **Label Direction** - UP is UP, DOWN is DOWN (not inverted!)
3. ✅ **Model Structure** - Same format as current working model
4. ✅ **Save Format** - Compatible with bot's loader

### Common Pitfalls to Avoid:
- ❌ Using different features than live bot
- ❌ Inverting UP/DOWN labels
- ❌ Wrong model structure (missing calibrator)
- ❌ Incompatible save format
- ❌ Not testing before deployment

---

## 🎯 EXPECTED OUTCOMES

### Immediate (After Deployment):
- ✅ Model loads without errors
- ✅ Bot makes predictions
- ✅ Both BUY and SELL trades execute

### Short-term (24-48 hours):
- ✅ Predictions align with market
- ✅ Win rate improves (target: >45%)
- ✅ Fewer consecutive losses

### Medium-term (1-2 weeks):
- ✅ Consistent profitability
- ✅ Positive P&L trend
- ✅ Stable performance

---

## 🤖 AUTOMATION BENEFITS

### Why Automate:
- ✅ Repeatable process
- ✅ Reduces human error
- ✅ Can retrain anytime
- ✅ Same script for all timeframes (5m, 1h, 12h, 24h)
- ✅ Faster iteration

### What Gets Automated:
1. Data fetching from Hyperliquid
2. Feature engineering
3. Target creation
4. Model training
5. Validation
6. Saving in correct format
7. Backup management
8. Deployment

---

## 📊 TIMELINE

### One-Time Setup:
- Create retraining script: 30-60 minutes
- Test and validate: 15-30 minutes

### Each Retraining Run:
- Data fetching: 5-10 minutes
- Feature engineering: 10-15 minutes
- Model training: 15-30 minutes
- Validation & deployment: 5-10 minutes
- **Total: ~1 hour per retraining**

### Monitoring:
- First 24 hours: Check every 2-4 hours
- Next 48 hours: Check daily
- Ongoing: Weekly performance review

---

## 🚀 NEXT STEPS

1. **Create automated retraining script**
   - Fetch Hyperliquid data
   - Engineer features
   - Train models
   - Save correctly

2. **Run initial retraining**
   - Execute script
   - Validate output
   - Test predictions

3. **Deploy new model**
   - Backup old model
   - Update LATEST.json
   - Restart 5m bot

4. **Monitor performance**
   - Track win rate
   - Monitor P&L
   - Adjust if needed

5. **Apply to other timeframes**
   - Use same script for 1h
   - Use same script for 24h
   - Use same script for 12h

---

## ✅ SUCCESS CRITERIA

### Model Quality:
- [ ] Training accuracy > 60%
- [ ] Test accuracy > 55%
- [ ] Predicts all 3 classes
- [ ] No overfitting (train/test scores close)

### Technical:
- [ ] Model loads without errors
- [ ] Features match live bot
- [ ] Saved in correct format
- [ ] LATEST.json updated

### Performance:
- [ ] Bot executes both BUY and SELL
- [ ] Win rate > 45% after 100 trades
- [ ] Positive P&L over 7 days
- [ ] Fewer losing streaks

---

**Ready to create the automated retraining script!**
