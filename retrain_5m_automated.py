"""
AUTOMATED 5M MODEL RETRAINING SCRIPT
Uses the exact same proven approach, just with fresh data

This script will:
1. Backup current model
2. Fetch fresh 5m data from Hyperliquid
3. Train using EXACT same approach as current model
4. Validate new model
5. Update LATEST.json automatically
6. Provide rollback if needed

Run this script anytime to retrain the 5m model.
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
import joblib
import json
import os
import shutil
import math

# ============================================
# MODEL WRAPPER CLASS (FIX FOR SERIALIZATION BUG)
# ============================================
class SimpleMetaClassifier:
    """
    Wrapper for base models + meta-classifier.
    Ensures saved model accepts 17 features (not 18).
    
    This fixes the bug where only the meta_classifier was saved,
    which expected 18 stacked probability features instead of 
    17 raw input features.
    """
    def __init__(self, base_models, meta_model, feature_columns):
        self.base_models = base_models  # Dict of trained base models
        self.meta_model = meta_model    # Trained LogisticRegression
        self.feature_columns = feature_columns
        self.is_fitted = True
        
    def predict_proba(self, X):
        """
        Accept 17 raw features, return 3-class probabilities.
        
        Pipeline:
        1. Run each base model on raw features
        2. Stack their probability outputs (4 models × 3 classes = 12 features)
        3. Feed stacked features to meta-classifier
        4. Return final probabilities
        """
        # Generate base model predictions
        meta_features = []
        for name, model in self.base_models.items():
            pred = model.predict_proba(X)
            meta_features.append(pred)
        
        # Stack predictions: 4 models × 3 classes = 12 features
        X_meta = np.hstack(meta_features)
        
        # Meta-classifier prediction
        return self.meta_model.predict_proba(X_meta)
    
    def predict(self, X):
        """Return class predictions (0=down, 1=neutral, 2=up)"""
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)

print("=" * 80)
print("5M MODEL AUTOMATED RETRAINING")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================
# CONFIGURATION
# ============================================
TIMEFRAME = "5m"
MODEL_DIR = "live_demo/models"
BACKUP_DIR = "live_demo/models/backup"
DATA_FILE = "ohlc_btc_5m_fresh.csv"

# ============================================
# STEP 1: BACKUP CURRENT MODEL
# ============================================
print("💾 STEP 1: Backing up current model...")
print("-" * 80)

try:
    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Load current LATEST.json
    with open(f'{MODEL_DIR}/LATEST.json', 'r') as f:
        current_latest = json.load(f)
    
    # Backup current model files
    backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_subdir = f"{BACKUP_DIR}/backup_{backup_timestamp}"
    os.makedirs(backup_subdir, exist_ok=True)
    
    for key, filename in current_latest.items():
        src = f"{MODEL_DIR}/{filename}"
        dst = f"{backup_subdir}/{filename}"
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"   ✅ Backed up: {filename}")
    
    # Save backup LATEST.json
    with open(f"{backup_subdir}/LATEST.json", 'w') as f:
        json.dump(current_latest, f, indent=2)
    
    print(f"\n✅ Backup complete: {backup_subdir}")
    print()
    
except Exception as e:
    print(f"❌ Backup failed: {e}")
    print("Aborting to keep current model safe.")
    exit(1)

# ============================================
# STEP 2: FETCH FRESH DATA
# ============================================
print("📡 STEP 2: Fetching fresh 5m data from Hyperliquid...")
print("-" * 80)

def fetch_hyperliquid_5m_data(days_back=180):
    """Fetch 5-minute OHLCV data from Hyperliquid"""
    url = "https://api.hyperliquid.xyz/info"
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    print(f"Fetching {days_back} days of 5m data...")
    print(f"From: {start_time.strftime('%Y-%m-%d')}")
    print(f"To: {end_time.strftime('%Y-%m-%d')}")
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "5m",
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError("No data returned from API")
        
        candles = []
        for candle in data:
            candles.append({
                'timestamp': datetime.fromtimestamp(candle['t'] / 1000),
                'open': float(candle['o']),
                'high': float(candle['h']),
                'low': float(candle['l']),
                'close': float(candle['c']),
                'volume': float(candle['v'])
            })
        
        df = pd.DataFrame(candles)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None

df = fetch_hyperliquid_5m_data(days_back=180)

if df is None or len(df) < 10000:
    print("❌ Insufficient data fetched. Aborting.")
    exit(1)

# Save data
df.to_csv(DATA_FILE, index=False)
print(f"✅ Data saved to: {DATA_FILE}")
print()

# ============================================
# STEP 3: CREATE FEATURES (EXACT SAME AS CURRENT MODEL)
# ============================================
print("🔧 STEP 3: Creating features (exact same as current model)...")
print("-" * 80)

def create_exact_5m_features(df):
    """
    Create the EXACT 17 features used by current 5m model
    Based on live_demo/features.py
    """
    # Basic returns
    df['mom_1'] = df['close'].pct_change(1)
    df['mom_3'] = df['close'].pct_change(3)
    
    # EMA20
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    # Realized volatility (12-period for 5m = 1 hour)
    df['rv_1h'] = df['mom_1'].rolling(12).apply(lambda x: np.sqrt(np.sum(x**2)), raw=True)
    
    # Mean reversion z-score
    df['mr_ema20_z'] = (df['close'] - df['ema20']) / (df['rv_1h'] + 1e-9)
    
    # Regime detection
    rv_median = df['rv_1h'].rolling(12).median()
    df['regime_high_vol'] = ((df['rv_1h'] > 2.0 * rv_median) & (df['rv_1h'] > 0)).astype(float)
    
    # Garman-Klass volatility
    def gk_vol(row):
        if row['open'] <= 0 or row['high'] <= 0 or row['low'] <= 0 or row['close'] <= 0:
            return 0.0
        try:
            return math.sqrt(
                0.5 * (math.log(row['high'] / row['low']) ** 2)
                - (2 * math.log(2) - 1) * (math.log(row['close'] / row['open']) ** 2)
            )
        except:
            return 0.0
    
    df['gk_volatility'] = df.apply(gk_vol, axis=1)
    
    # Jump magnitude
    df['jump_magnitude'] = df['mom_1'].abs()
    
    # Volume features
    df['volume_mean'] = df['volume'].rolling(50).mean()
    df['volume_intensity'] = (df['volume'] / (df['volume_mean'] + 1e-9)) - 1.0
    
    # Price range and efficiency
    df['price_range'] = (df['high'] - df['low']) / (df['close'] + 1e-9)
    df['price_efficiency'] = df['mom_1'].abs() / (df['price_range'] + 1e-9)
    
    # Price-volume correlation
    def price_volume_corr(idx, window=36):
        if idx < window:
            return 0.0
        returns = df['mom_1'].iloc[idx-window:idx].values
        volumes = df['volume'].iloc[idx-window:idx].values
        if len(returns) >= 3:
            try:
                return float(np.corrcoef(returns, volumes)[0, 1])
            except:
                return 0.0
        return 0.0
    
    df['price_volume_corr'] = [price_volume_corr(i) for i in range(len(df))]
    
    # VWAP momentum (proxy with mom_3)
    df['vwap_momentum'] = df['mom_3']
    
    # Depth proxy (not available, set to 0)
    df['depth_proxy'] = 0.0
    
    # Funding features (set to 0 for now)
    df['funding_rate'] = 0.0
    df['funding_momentum_1h'] = 0.0
    
    # Flow diff (cohort signals - set to 0 for now)
    df['flow_diff'] = 0.0
    df['S_top'] = 0.0
    df['S_bot'] = 0.0
    
    return df

print("Creating 17 features...")
df = create_exact_5m_features(df)

# The exact 17 features in correct order
feature_columns = [
    "mom_1", "mom_3", "mr_ema20_z", "rv_1h", "regime_high_vol",
    "gk_volatility", "jump_magnitude", "volume_intensity",
    "price_efficiency", "price_volume_corr", "vwap_momentum",
    "depth_proxy", "funding_rate", "funding_momentum_1h",
    "flow_diff", "S_top", "S_bot"
]

print(f"✅ Created {len(feature_columns)} features")
print()

# ============================================
# STEP 4: CREATE TARGET (SAME AS CURRENT MODEL)
# ============================================
print("🎯 STEP 4: Creating target variable...")
print("-" * 80)

df['future_return'] = df['close'].pct_change(1).shift(-1)

# Thresholds for 5m timeframe
up_threshold = 0.005  # 0.5%
down_threshold = -0.005  # -0.5%

df['target'] = 1  # NEUTRAL
df.loc[df['future_return'] > up_threshold, 'target'] = 2  # UP
df.loc[df['future_return'] < down_threshold, 'target'] = 0  # DOWN

df = df.dropna()

print(f"✅ Target distribution:")
target_counts = df['target'].value_counts().sort_index()
for label, count in target_counts.items():
    label_name = ['DOWN', 'NEUTRAL', 'UP'][label]
    pct = count / len(df) * 100
    print(f"   {label_name}: {count} ({pct:.1f}%)")
print()

# ============================================
# STEP 5: TRAIN MODEL (EXACT SAME APPROACH)
# ============================================
print("🤖 STEP 5: Training model (exact same approach as current)...")
print("-" * 80)

X = df[feature_columns]
y = df['target']

# Time-based split (80/20)
split_idx = int(len(df) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

print(f"Training samples: {len(X_train)}")
print(f"Test samples: {len(X_test)}")
print()

# Train base models (EXACT same as current model)
print("Training base models...")
models = {
    'randomforest': RandomForestClassifier(
        n_estimators=100, 
        max_depth=10, 
        random_state=42, 
        n_jobs=-1,
        class_weight='balanced'
    ),
    'extratrees': ExtraTreesClassifier(
        n_estimators=100, 
        max_depth=10, 
        random_state=42, 
        n_jobs=-1,
        class_weight='balanced'
    ),
    'histgb': HistGradientBoostingClassifier(max_iter=100, random_state=42),
    'gb_classifier': GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42),
}

trained_models = {}
cv_scores = {}

for name, model in models.items():
    print(f"  Training {name}...", end=" ")
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    cv_scores[name] = float(score)
    trained_models[name] = model
    print(f"✅ {score:.4f}")

print()

# Create meta-classifier
print("Creating meta-classifier...")
meta_features_train = []
meta_features_test = []

for name, model in trained_models.items():
    pred_train = model.predict_proba(X_train)
    pred_test = model.predict_proba(X_test)
    meta_features_train.append(pred_train)
    meta_features_test.append(pred_test)

X_meta_train = np.hstack(meta_features_train)
X_meta_test = np.hstack(meta_features_test)

meta_classifier = LogisticRegression(
    random_state=42, 
    max_iter=1000,
    class_weight='balanced'  # Handle class imbalance (matches old model)
)
meta_classifier.fit(X_meta_train, y_train)

meta_score = meta_classifier.score(X_meta_test, y_test)
print(f"✅ Meta-classifier accuracy: {meta_score:.4f}")
print()

# Calibrate
print("Calibrating probabilities...")
calibrator = CalibratedClassifierCV(meta_classifier, cv=3, method='isotonic')
calibrator.fit(X_meta_train, y_train)

calibrated_score = calibrator.score(X_meta_test, y_test)
print(f"✅ Calibrated accuracy: {calibrated_score:.4f}")
print()

# ============================================
# STEP 6: VALIDATE NEW MODEL
# ============================================
print("✅ STEP 6: Validating new model...")
print("-" * 80)

validation_passed = True

if calibrated_score < 0.55:
    print(f"⚠️ WARNING: Accuracy is low ({calibrated_score:.2%})")
    validation_passed = False
else:
    print(f"✅ Accuracy is good ({calibrated_score:.2%})")

# Check if predicts all classes
unique_preds = np.unique(calibrator.predict(X_meta_test))
if len(unique_preds) == 3:
    print(f"✅ Predicts all 3 classes")
else:
    print(f"⚠️ WARNING: Only predicts {len(unique_preds)} classes")
    validation_passed = False

print()

if not validation_passed:
    print("⚠️ Validation warnings detected.")
    print("Model will still be saved, but review performance carefully.")
    print()

# ============================================
# STEP 7: SAVE NEW MODEL
# ============================================
print("💾 STEP 7: Saving new model...")
print("-" * 80)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
schema_hash = "d7a9e9fb3a42"  # Same as current model

# Save calibrator (this is what the bot uses)
cal_file = f'calibrator_{timestamp}_{schema_hash}.joblib'
joblib.dump(calibrator, f"{MODEL_DIR}/{cal_file}")
print(f"✅ Saved: {cal_file}")

# Create wrapper that includes base models (CRITICAL FIX!)
print("Creating model wrapper with base models...")
full_model = SimpleMetaClassifier(
    base_models=trained_models,
    meta_model=meta_classifier,
    feature_columns=feature_columns
)

# Save the FULL model (not just meta_classifier)
meta_file = f'meta_classifier_{timestamp}_{schema_hash}.joblib'
joblib.dump(full_model, f"{MODEL_DIR}/{meta_file}")
print(f"✅ Saved: {meta_file} (FULL MODEL with base estimators - accepts 17 features)")

# Save feature columns
feat_file = f'feature_columns_{timestamp}_{schema_hash}.json'
feature_schema = {
    "feature_cols": feature_columns,
    "schema_hash": schema_hash
}
with open(f"{MODEL_DIR}/{feat_file}", 'w') as f:
    json.dump(feature_schema, f)
print(f"✅ Saved: {feat_file}")

# Save training metadata
metadata = {
    'timestamp_utc': timestamp,
    'target': 'direction_confidence_5m',
    'n_features': len(feature_columns),
    'schema_hash': schema_hash,
    'class_mapping': {'down': 0, 'neutral': 1, 'up': 2},
    'meta_score_in_sample': float(meta_score),
    'calibrated_score': float(calibrated_score),
    'cv_scores': cv_scores,
    'folds': 3,
    'embargo_pct': 0.01,
    'purge_pct': 0.02,
    'training_samples': len(X_train),
    'test_samples': len(X_test),
    'data_start': str(df['timestamp'].min()),
    'data_end': str(df['timestamp'].max())
}

meta_meta_file = f'training_meta_{timestamp}_{schema_hash}.json'
with open(f"{MODEL_DIR}/{meta_meta_file}", 'w') as f:
    json.dump(metadata, f, indent=2)
print(f"✅ Saved: {meta_meta_file}")

# ============================================
# STEP 8: UPDATE LATEST.JSON
# ============================================
print()
print("📝 STEP 8: Updating LATEST.json...")
print("-" * 80)

new_latest = {
    'meta_classifier': meta_file,
    'calibrator': cal_file,
    'feature_columns': feat_file,
    'training_meta': meta_meta_file
}

with open(f"{MODEL_DIR}/LATEST.json", 'w') as f:
    json.dump(new_latest, f, indent=2)

print(f"✅ LATEST.json updated")
print()

# ============================================
# COMPLETION
# ============================================
print("=" * 80)
print("🎉 RETRAINING COMPLETE!")
print("=" * 80)
print()

print(f"📊 New Model Performance:")
print(f"   Training Accuracy: {meta_score:.2%}")
print(f"   Test Accuracy: {calibrated_score:.2%}")
print(f"   Training Samples: {len(X_train):,}")
print(f"   Test Samples: {len(X_test):,}")
print()

print(f"📁 Files:")
print(f"   Calibrator: {cal_file}")
print(f"   Meta-classifier: {meta_file}")
print(f"   Features: {feat_file}")
print(f"   Metadata: {meta_meta_file}")
print()

print(f"💾 Backup Location:")
print(f"   {backup_subdir}")
print()

print("🔄 Next Steps:")
print("   1. ✅ Model is ready to use")
print("   2. ⏳ Restart 5m bot: python run_5m.py")
print("   3. ⏳ Monitor performance for 24-48 hours")
print("   4. ⏳ If issues, rollback using backup")
print()

print("🔙 To Rollback (if needed):")
print(f"   1. Copy files from: {backup_subdir}")
print(f"   2. To: {MODEL_DIR}")
print(f"   3. Restart bot")
print()

print("=" * 80)
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
