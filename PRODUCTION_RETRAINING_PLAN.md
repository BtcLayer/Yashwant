# PRODUCTION-GRADE MODEL RETRAINING PLAN
## Multi-Timeframe Trading System Recovery

**Date:** 2026-01-06 15:30 IST  
**Analyst:** Senior Quant ML Engineer  
**Objective:** Permanent fix for model quality degradation across all timeframes

---

## EXECUTIVE SUMMARY

**Current State:** SYSTEM FAILURE
- 5m: 91.5% neutral, 0% eligible signals, confidence 0.175 (need 0.60)
- 1h: NO MODEL RUNNING
- 12h: NO MODEL RUNNING  
- 24h: 100% BUY bias, confidence 0.134 (need 0.60)

**Root Cause:** MODEL TRAINING METHODOLOGY FAILURE
- Not threshold misconfiguration
- Not gating logic
- Core model quality is fundamentally broken

**Required Action:** COMPLETE MODEL SUITE RETRAINING
- All 4 timeframes (5m, 1h, 12h, 24h)
- Production-grade methodology
- Validation before deployment
- No threshold adjustments

---

## PART 1: DEEP ROOT CAUSE ANALYSIS

### 1.1 FORENSIC FINDINGS

#### 5m Model (PRIMARY EXECUTION)
```
Status: DEPLOYED BUT BROKEN
Signals: 1,844 analyzed
Class Distribution:
  - Neutral (dir=0): 91.5% ← CATASTROPHIC
  - BUY (dir=1): 8.5%
  - SELL: 0% ← MISSING ENTIRELY

Probability Distribution:
  - p_neutral: 0.701 (70.1%) ← DOMINATING
  - p_up: 0.164 (16.4%)
  - p_down: 0.136 (13.6%)

Confidence:
  - Mean: 0.175
  - Max: 0.578
  - >= 0.60: 0 signals (0.0%) ← ZERO ELIGIBILITY

Alpha:
  - Mean: 0.051 (5.1%)
  - >= 0.10: 148 signals (8.0%)

Eligibility (conf>=0.60 AND alpha>=0.10): 0.0%
```

**Diagnosis:**
1. **Severe class imbalance in training data** → Model learned to predict neutral
2. **Poor calibration** → Probabilities don't reflect true confidence
3. **No SELL class representation** → Model cannot predict down moves
4. **Neutral class dominance** → 70% p_neutral means model is uncertain, not confident

#### 24h Model (OVERLAY/REGIME)
```
Status: DEPLOYED BUT BROKEN
Signals: 69 analyzed
Class Distribution:
  - BUY (dir=1): 100% ← COMPLETE BIAS
  - Neutral: 0%
  - SELL: 0%

Probability Distribution:
  - p_neutral: 0.802 (80.2%) ← EXTREME
  - p_up: 0.134 (13.4%)
  - p_down: 0.064 (6.4%)

Confidence:
  - Mean: 0.134
  - Max: 0.135
  - Std: 0.0008 ← ZERO VARIANCE (BROKEN)

Alpha:
  - Mean: 0.070 (7.0%)
  - >= 0.10: 0 signals (0.0%)

Eligibility: 0.0%
```

**Diagnosis:**
1. **Model is outputting CONSTANT predictions** → Std = 0.0008
2. **100% BUY bias** → Training data or labeling is broken
3. **80% p_neutral** → Model has no conviction
4. **No variance** → Model is not learning, just memorizing a constant

#### 1h and 12h Models
```
Status: NOT RUNNING
Error: No signals file found
```

**Diagnosis:**
1. **Models don't exist or aren't deployed**
2. **System is operating without overlay support**
3. **5m is making decisions in isolation** → Dangerous

### 1.2 ROOT CAUSES (TECHNICAL)

#### Cause 1: CLASS IMBALANCE IN TRAINING DATA
**Evidence:**
- 5m produces 91.5% neutral
- 24h produces 100% BUY
- No SELL predictions anywhere

**Why This Happens:**
```python
# Typical broken labeling logic:
def create_labels(df):
    df['returns'] = df['close'].pct_change(periods=forward_bars)
    df['target'] = 0  # Default neutral
    df.loc[df['returns'] > threshold, 'target'] = 1  # UP
    df.loc[df['returns'] < -threshold, 'target'] = -1  # DOWN
    return df
```

**Problems:**
1. If `threshold` is too high → Most samples labeled neutral
2. If market is ranging → Few directional moves
3. If forward_bars is wrong for timeframe → Mislabeled data
4. No class balancing → Model learns majority class

**Fix Required:**
- Adaptive thresholds based on volatility
- Proper class balancing (NOT naive oversampling)
- Timeframe-appropriate forward horizons
- Validation of label distribution BEFORE training

#### Cause 2: POOR CALIBRATION
**Evidence:**
- Mean confidence 0.175 vs required 0.60
- Probabilities don't sum to actionable decisions
- p_neutral dominates even when model has signal

**Why This Happens:**
```python
# Typical broken calibration:
calibrator = CalibratedClassifierCV(base_model, method='sigmoid', cv=3)
calibrator.fit(X_train, y_train)
```

**Problems:**
1. `sigmoid` calibration assumes binary → Breaks for 3-class
2. CV=3 is too small → Overfits calibration
3. No validation of calibrated output distribution
4. Calibration on imbalanced data → Amplifies bias

**Fix Required:**
- Use `isotonic` calibration for multi-class
- Larger CV folds (5-10)
- Post-calibration validation
- Separate calibration set (not train/test)

#### Cause 3: WRONG TRAINING OBJECTIVE
**Evidence:**
- Models optimize accuracy, not trading utility
- No consideration of confidence requirements
- No BPS/alpha optimization

**Why This Happens:**
```python
# Typical broken objective:
model = RandomForestClassifier()
model.fit(X_train, y_train)
score = model.score(X_test, y_test)  # Accuracy
```

**Problems:**
1. Accuracy doesn't care about confidence
2. Accuracy rewards predicting majority class
3. No penalty for low-confidence predictions
4. No reward for high-alpha predictions

**Fix Required:**
- Custom loss function incorporating confidence
- Weighted classes to force balance
- BPS-aware training
- Confidence-gated validation metrics

#### Cause 4: FEATURE LEAKAGE
**Evidence:**
- 24h model has ZERO variance (constant output)
- Suggests features are constant or leaked

**Why This Happens:**
```python
# Typical leakage:
df['future_return'] = df['close'].shift(-forward_bars) / df['close'] - 1
df['feature_using_future'] = df['future_return'].rolling(10).mean()
```

**Problems:**
1. Using future data in features
2. Using target-derived features
3. Not respecting time boundaries
4. Look-ahead bias in indicators

**Fix Required:**
- Strict feature audit
- No future data
- Proper time-series split
- Feature importance analysis

#### Cause 5: TIMEFRAME-INAPPROPRIATE METHODOLOGY
**Evidence:**
- Same training script used for 5m and 24h
- No timeframe-specific adaptations

**Why This Happens:**
- Copy-paste training code
- No consideration of noise profiles
- Wrong forward horizons
- Wrong feature windows

**Problems:**
| Timeframe | Horizon | Noise | Features | Forward Bars |
|-----------|---------|-------|----------|--------------|
| 5m | Minutes | HIGH | Short MA | 12-24 (1-2hr) |
| 1h | Hours | MEDIUM | Medium MA | 6-12 (6-12hr) |
| 12h | Days | LOW | Long MA | 2-4 (1-2 days) |
| 24h | Weeks | VERY LOW | Macro | 3-7 (3-7 days) |

**Current (Broken):**
- All use same forward_bars
- All use same features
- All use same thresholds

**Fix Required:**
- Timeframe-specific configurations
- Appropriate noise filtering
- Horizon-matched labeling
- Role-appropriate objectives

---

## PART 2: MODEL REQUIREMENTS (PER TIMEFRAME)

### 2.1 5m MODEL (EXECUTION ENGINE)

**Role:** Primary trade execution, high-frequency decisions

**Requirements:**
```
Class Distribution Target:
  - UP: 30-40%
  - DOWN: 30-40%
  - NEUTRAL: 20-40%

Confidence Target:
  - Mean: >= 0.65
  - Median: >= 0.60
  - Signals >= 0.60: >= 40%

Alpha Target:
  - Mean: >= 0.12 (12%)
  - Signals >= 0.10: >= 50%

Eligibility Target:
  - (conf >= 0.60 AND alpha >= 0.10): >= 30%

Activity Target:
  - Non-neutral signals: >= 60%
  - Trades per day: 10-30
```

**Training Specifications:**
- **Data:** 90 days of 5m candles
- **Forward Horizon:** 12 bars (1 hour)
- **Features:** 17 technical indicators (short-term)
- **Labeling:** Adaptive threshold based on 20-bar realized vol
- **Class Balance:** Weighted sampling to achieve 40/40/20
- **Model:** Ensemble (RF + XGB + LR) → Meta-classifier
- **Calibration:** Isotonic, CV=10, separate cal set
- **Validation:** Confidence distribution, BPS, eligibility rate

### 2.2 1h MODEL (TACTICAL OVERLAY)

**Role:** Medium-term trend confirmation, reduce 5m noise

**Requirements:**
```
Class Distribution Target:
  - UP: 35-45%
  - DOWN: 35-45%
  - NEUTRAL: 10-30%

Confidence Target:
  - Mean: >= 0.60
  - Signals >= 0.55: >= 50%

Alpha Target:
  - Mean: >= 0.10 (10%)
  - Signals >= 0.08: >= 60%

Activity Target:
  - Non-neutral signals: >= 70%
  - Signals per day: 8-16
```

**Training Specifications:**
- **Data:** 180 days of 1h candles
- **Forward Horizon:** 8 bars (8 hours)
- **Features:** 15 indicators (medium-term)
- **Labeling:** Volatility-adjusted, 8h forward return
- **Class Balance:** 45/45/10 target
- **Model:** Ensemble → Meta → Calibrated
- **Validation:** Overlay agreement with 5m, regime detection

### 2.3 12h MODEL (REGIME FILTER)

**Role:** Identify market regime, filter bad conditions

**Requirements:**
```
Class Distribution Target:
  - BULLISH: 30-40%
  - BEARISH: 30-40%
  - RANGING: 20-40%

Confidence Target:
  - Mean: >= 0.55
  - Signals >= 0.50: >= 60%

Alpha Target:
  - Mean: >= 0.08 (8%)

Activity Target:
  - Non-neutral signals: >= 60%
  - Regime changes: 2-6 per week
```

**Training Specifications:**
- **Data:** 365 days of 12h candles
- **Forward Horizon:** 4 bars (2 days)
- **Features:** 12 indicators (macro trends)
- **Labeling:** Regime-based (trending vs ranging)
- **Class Balance:** 40/40/20
- **Model:** Simpler (RF + LR) → Calibrated
- **Validation:** Regime stability, transition quality

### 2.4 24h MODEL (STRATEGIC BIAS)

**Role:** Long-term bias, position sizing modifier

**Requirements:**
```
Class Distribution Target:
  - BULLISH: 35-45%
  - BEARISH: 35-45%
  - NEUTRAL: 10-30%

Confidence Target:
  - Mean: >= 0.50
  - Signals >= 0.45: >= 70%

Alpha Target:
  - Mean: >= 0.06 (6%)

Activity Target:
  - Non-neutral signals: >= 70%
  - Changes per month: 4-8
```

**Training Specifications:**
- **Data:** 730 days (2 years) of 24h candles
- **Forward Horizon:** 5 bars (5 days)
- **Features:** 10 indicators (macro only)
- **Labeling:** Weekly return-based
- **Class Balance:** 45/45/10
- **Model:** Simple ensemble
- **Validation:** Directional accuracy, stability

---

## PART 3: RETRAINING STRATEGY

### 3.1 DATA PREPARATION (PER TIMEFRAME)

#### Step 1: Data Collection
```python
# Timeframe-specific data requirements
DATA_SPECS = {
    '5m': {'days': 90, 'min_bars': 25000},
    '1h': {'days': 180, 'min_bars': 4000},
    '12h': {'days': 365, 'min_bars': 700},
    '24h': {'days': 730, 'min_bars': 700}
}
```

#### Step 2: Feature Engineering
```python
# Timeframe-appropriate features
FEATURE_CONFIGS = {
    '5m': {
        'ma_windows': [5, 10, 20, 50],
        'vol_window': 20,
        'momentum_window': 10,
        'rsi_window': 14
    },
    '1h': {
        'ma_windows': [12, 24, 48, 96],
        'vol_window': 24,
        'momentum_window': 12,
        'rsi_window': 14
    },
    # ... etc
}
```

#### Step 3: Labeling
```python
def adaptive_labeling(df, timeframe):
    """Create labels with timeframe-appropriate logic"""
    
    # Forward horizon
    forward_bars = {
        '5m': 12,   # 1 hour
        '1h': 8,    # 8 hours
        '12h': 4,   # 2 days
        '24h': 5    # 5 days
    }[timeframe]
    
    # Compute forward returns
    df['forward_return'] = df['close'].shift(-forward_bars) / df['close'] - 1
    
    # Adaptive threshold based on realized volatility
    df['realized_vol'] = df['close'].pct_change().rolling(20).std()
    df['threshold'] = df['realized_vol'] * 1.5  # 1.5 sigma moves
    
    # Label with adaptive threshold
    df['target'] = 0  # Neutral
    df.loc[df['forward_return'] > df['threshold'], 'target'] = 1  # UP
    df.loc[df['forward_return'] < -df['threshold'], 'target'] = -1  # DOWN
    
    return df
```

#### Step 4: Class Balancing
```python
def balance_classes(X, y, target_dist={'up': 0.40, 'down': 0.40, 'neutral': 0.20}):
    """Intelligent class balancing"""
    
    # Current distribution
    counts = pd.Series(y).value_counts()
    
    # Calculate sampling weights
    weights = {}
    for cls in [-1, 0, 1]:
        target_count = len(y) * target_dist[{-1: 'down', 0: 'neutral', 1: 'up'}[cls]]
        weights[cls] = target_count / counts[cls]
    
    # Sample with replacement to achieve target distribution
    sample_weights = np.array([weights[yi] for yi in y])
    
    return sample_weights
```

### 3.2 MODEL ARCHITECTURE

```python
class ProductionMetaClassifier:
    """Production-grade meta-classifier with proper calibration"""
    
    def __init__(self, timeframe):
        self.timeframe = timeframe
        self.base_models = self._create_base_models()
        self.meta_model = LogisticRegression(
            class_weight='balanced',
            max_iter=1000,
            C=0.1  # Regularization
        )
        self.calibrator = None
        
    def _create_base_models(self):
        """Timeframe-appropriate base models"""
        if self.timeframe == '5m':
            # High noise → More regularization
            return {
                'rf': RandomForestClassifier(
                    n_estimators=200,
                    max_depth=8,
                    min_samples_leaf=50,
                    class_weight='balanced'
                ),
                'xgb': XGBClassifier(
                    n_estimators=200,
                    max_depth=6,
                    learning_rate=0.05,
                    scale_pos_weight=1.0
                ),
                'lr': LogisticRegression(
                    class_weight='balanced',
                    C=0.1
                )
            }
        elif self.timeframe in ['1h', '12h']:
            # Medium noise → Moderate regularization
            return {
                'rf': RandomForestClassifier(
                    n_estimators=150,
                    max_depth=10,
                    class_weight='balanced'
                ),
                'xgb': XGBClassifier(
                    n_estimators=150,
                    max_depth=8
                )
            }
        else:  # 24h
            # Low noise → Less regularization
            return {
                'rf': RandomForestClassifier(
                    n_estimators=100,
                    max_depth=12,
                    class_weight='balanced'
                ),
                'lr': LogisticRegression(class_weight='balanced')
            }
    
    def fit(self, X_train, y_train, X_cal, y_cal):
        """Train with proper calibration"""
        
        # Train base models
        meta_features_train = []
        for name, model in self.base_models.items():
            model.fit(X_train, y_train)
            pred_proba = model.predict_proba(X_train)
            meta_features_train.append(pred_proba)
        
        # Stack predictions
        X_meta = np.hstack(meta_features_train)
        
        # Train meta-model
        self.meta_model.fit(X_meta, y_train)
        
        # Calibrate on separate calibration set
        meta_features_cal = []
        for name, model in self.base_models.items():
            pred_proba = model.predict_proba(X_cal)
            meta_features_cal.append(pred_proba)
        
        X_meta_cal = np.hstack(meta_features_cal)
        meta_pred_cal = self.meta_model.predict_proba(X_meta_cal)
        
        # Isotonic calibration
        self.calibrator = CalibratedClassifierCV(
            self.meta_model,
            method='isotonic',
            cv='prefit'
        )
        self.calibrator.fit(X_meta_cal, y_cal)
        
    def predict_proba(self, X):
        """Calibrated predictions"""
        meta_features = []
        for name, model in self.base_models.items():
            pred_proba = model.predict_proba(X)
            meta_features.append(pred_proba)
        
        X_meta = np.hstack(meta_features)
        return self.calibrator.predict_proba(X_meta)
```

### 3.3 VALIDATION FRAMEWORK

```python
def validate_model(model, X_test, y_test, timeframe):
    """Production validation - trading-relevant metrics only"""
    
    # Get predictions
    proba = model.predict_proba(X_test)
    
    # Extract probabilities
    p_down = proba[:, 0]
    p_neutral = proba[:, 1]
    p_up = proba[:, 2]
    
    # Confidence
    conf = np.maximum(p_up, p_down)
    
    # Alpha
    alpha = np.abs(p_up - p_down)
    
    # Direction
    direction = np.argmax(proba, axis=1) - 1  # -1, 0, 1
    
    # Validation metrics
    results = {
        'class_distribution': {
            'down': (direction == -1).sum() / len(direction),
            'neutral': (direction == 0).sum() / len(direction),
            'up': (direction == 1).sum() / len(direction)
        },
        'confidence': {
            'mean': conf.mean(),
            'median': np.median(conf),
            'std': conf.std(),
            'pct_above_0.60': (conf >= 0.60).sum() / len(conf)
        },
        'alpha': {
            'mean': alpha.mean(),
            'median': np.median(alpha),
            'pct_above_0.10': (alpha >= 0.10).sum() / len(alpha)
        },
        'eligibility': {
            'pct': ((conf >= 0.60) & (alpha >= 0.10)).sum() / len(conf)
        },
        'p_neutral_mean': p_neutral.mean()
    }
    
    # Check against requirements
    requirements = get_requirements(timeframe)
    passed = check_requirements(results, requirements)
    
    return results, passed

def check_requirements(results, requirements):
    """Strict requirement checking"""
    checks = {
        'class_balance': (
            results['class_distribution']['down'] >= requirements['min_down_pct'] and
            results['class_distribution']['up'] >= requirements['min_up_pct'] and
            results['class_distribution']['neutral'] <= requirements['max_neutral_pct']
        ),
        'confidence': results['confidence']['mean'] >= requirements['min_conf_mean'],
        'eligibility': results['eligibility']['pct'] >= requirements['min_eligibility_pct']
    }
    
    return all(checks.values()), checks
```

---

## PART 4: AUTOMATED RETRAINING SCRIPTS

I will create 4 production scripts (5m, 1h, 12h, 24h) in the next response due to length constraints.

**Script Requirements:**
1. End-to-end automation
2. Timeframe-specific configurations
3. Validation gates
4. Fail-loud on quality issues
5. Backup before deployment
6. Diagnostic outputs

---

## PART 5: BACKTESTING FRAMEWORK

```python
class ProductionBacktest:
    """Realistic backtesting with proper constraints"""
    
    def __init__(self, model, config):
        self.model = model
        self.config = config
        self.trades = []
        self.equity = [10000]  # Starting capital
        
    def run(self, df):
        """Run backtest with realistic constraints"""
        
        for i in range(len(df)):
            # Get model prediction
            features = df.iloc[i][self.feature_cols].values.reshape(1, -1)
            proba = self.model.predict_proba(features)[0]
            
            p_up, p_neutral, p_down = proba[2], proba[1], proba[0]
            conf = max(p_up, p_down)
            alpha = abs(p_up - p_down)
            
            # Check eligibility
            if conf < 0.60 or alpha < 0.10:
                continue  # No trade
            
            # Determine direction
            direction = 'BUY' if p_up > p_down else 'SELL'
            
            # Simulate trade with costs
            entry_price = df.iloc[i]['close']
            exit_price = df.iloc[i + self.config['hold_bars']]['close']
            
            # Apply costs
            fee_bps = 5.0  # 5 bps taker fee
            slippage_bps = 1.0
            total_cost_bps = fee_bps + slippage_bps
            
            # Calculate PnL
            if direction == 'BUY':
                pnl_pct = (exit_price / entry_price - 1) - (total_cost_bps / 10000)
            else:
                pnl_pct = (entry_price / exit_price - 1) - (total_cost_bps / 10000)
            
            pnl_usd = self.equity[-1] * pnl_pct
            self.equity.append(self.equity[-1] + pnl_usd)
            
            self.trades.append({
                'timestamp': df.iloc[i]['timestamp'],
                'direction': direction,
                'entry': entry_price,
                'exit': exit_price,
                'pnl_pct': pnl_pct,
                'pnl_usd': pnl_usd,
                'conf': conf,
                'alpha': alpha
            })
        
        return self.analyze_results()
    
    def analyze_results(self):
        """Calculate realistic performance metrics"""
        trades_df = pd.DataFrame(self.trades)
        
        return {
            'total_trades': len(trades_df),
            'win_rate': (trades_df['pnl_usd'] > 0).sum() / len(trades_df),
            'total_pnl': trades_df['pnl_usd'].sum(),
            'sharpe': trades_df['pnl_pct'].mean() / trades_df['pnl_pct'].std() * np.sqrt(252),
            'max_drawdown': self.calculate_max_dd(),
            'avg_trade_pnl': trades_df['pnl_usd'].mean(),
            'direction_balance': trades_df['direction'].value_counts().to_dict()
        }
```

---

## PART 6: DEPLOYMENT CHECKLIST

### Pre-Deployment Validation
- [ ] Model passes all requirement checks
- [ ] Backtest shows positive Sharpe (>0.5)
- [ ] Class distribution is balanced
- [ ] Confidence meets thresholds
- [ ] Eligibility rate >= 30%
- [ ] No training warnings/errors
- [ ] Calibration is proper
- [ ] Feature leakage audit passed

### Deployment Steps
1. Stop running bot
2. Backup current models
3. Deploy new model files
4. Update LATEST.json
5. Clear stale cache
6. Restart bot
7. Monitor for 1 hour
8. Verify signal generation
9. Verify trade execution
10. Check performance metrics

### Runtime Verification
- [ ] Models load without errors
- [ ] Signals are generated every bar
- [ ] Confidence distribution matches validation
- [ ] Trades execute (not all neutral)
- [ ] BUY/SELL balance maintained
- [ ] No Python warnings
- [ ] Logs show normal operation

---

**NEXT STEPS:**

I will now create the 4 production retraining scripts. Due to length, I'll create them as separate files.

Would you like me to proceed with creating:
1. `retrain_5m_production_v2.py`
2. `retrain_1h_production.py`
3. `retrain_12h_production.py`
4. `retrain_24h_production.py`

Each with full implementation of the methodology above?
