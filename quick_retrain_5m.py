"""
QUICK RETRAIN: 5M Model with Fresh Data
Fetches last 60 days and retrains immediately
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

# Model wrapper class
class SimpleMetaClassifier:
    def __init__(self, base_models, meta_model, feature_columns):
        self.base_models = base_models
        self.meta_model = meta_model
        self.feature_columns = feature_columns
        self.is_fitted = True
        
    def predict_proba(self, X):
        meta_features = []
        for name, model in self.base_models.items():
            pred = model.predict_proba(X)
            meta_features.append(pred)
        X_meta = np.hstack(meta_features)
        return self.meta_model.predict_proba(X_meta)
    
    def predict(self, X):
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)

print("=" * 80)
print("QUICK 5M MODEL RETRAIN - FRESH DATA")
print("=" * 80)
print(f"Started: {datetime.now()}")
print()

MODEL_DIR = "live_demo/models"
BACKUP_DIR = "live_demo/models/backup"

# Step 1: Backup
print("Step 1: Backing up current model...")
try:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    with open(f'{MODEL_DIR}/LATEST.json', 'r') as f:
        current_latest = json.load(f)
    
    backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_subdir = f"{BACKUP_DIR}/backup_{backup_timestamp}"
    os.makedirs(backup_subdir, exist_ok=True)
    
    for key, filename in current_latest.items():
        src = f"{MODEL_DIR}/{filename}"
        dst = f"{backup_subdir}/{filename}"
        if os.path.exists(src):
            shutil.copy2(src, dst)
    
    with open(f"{backup_subdir}/LATEST.json", 'w') as f:
        json.dump(current_latest, f, indent=2)
    
    print(f"✓ Backup: {backup_subdir}")
except Exception as e:
    print(f"✗ Backup failed: {e}")
    exit(1)

# Step 2: Fetch fresh data (60 days)
print("\nStep 2: Fetching fresh 5m data (60 days)...")
url = "https://api.hyperliquid.xyz/info"
end_time = datetime.now()
start_time = end_time - timedelta(days=60)

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
    
    candles = []
    for c in data:
        candles.append({
            'timestamp': datetime.fromtimestamp(c['t'] / 1000),
            'open': float(c['o']),
            'high': float(c['h']),
            'low': float(c['l']),
            'close': float(c['c']),
            'volume': float(c['v'])
        })
    
    df = pd.DataFrame(candles).sort_values('timestamp').reset_index(drop=True)
    print(f"✓ Fetched {len(df)} candles")
    print(f"  Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    if len(df) < 5000:
        print(f"✗ Insufficient data: {len(df)} < 5000")
        exit(1)
        
except Exception as e:
    print(f"✗ Fetch failed: {e}")
    exit(1)

# Step 3: Create features
print("\nStep 3: Creating 17 features...")

df['mom_1'] = df['close'].pct_change(1)
df['mom_3'] = df['close'].pct_change(3)
df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
df['rv_1h'] = df['mom_1'].rolling(12).apply(lambda x: np.sqrt(np.sum(x**2)), raw=True)
df['mr_ema20_z'] = (df['close'] - df['ema20']) / (df['rv_1h'] + 1e-9)

rv_median = df['rv_1h'].rolling(12).median()
df['regime_high_vol'] = ((df['rv_1h'] > 2.0 * rv_median) & (df['rv_1h'] > 0)).astype(float)

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
df['jump_magnitude'] = df['mom_1'].abs()
df['volume_mean'] = df['volume'].rolling(50).mean()
df['volume_intensity'] = (df['volume'] / (df['volume_mean'] + 1e-9)) - 1.0
df['price_range'] = (df['high'] - df['low']) / (df['close'] + 1e-9)
df['price_efficiency'] = df['mom_1'].abs() / (df['price_range'] + 1e-9)

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
df['vwap_momentum'] = df['mom_3']
df['depth_proxy'] = 0.0
df['funding_rate'] = 0.0
df['funding_momentum_1h'] = 0.0
df['flow_diff'] = 0.0
df['S_top'] = 0.0
df['S_bot'] = 0.0

feature_columns = [
    "mom_1", "mom_3", "mr_ema20_z", "rv_1h", "regime_high_vol",
    "gk_volatility", "jump_magnitude", "volume_intensity",
    "price_efficiency", "price_volume_corr", "vwap_momentum",
    "depth_proxy", "funding_rate", "funding_momentum_1h",
    "flow_diff", "S_top", "S_bot"
]

print(f"✓ Created {len(feature_columns)} features")

# Step 4: Create target
print("\nStep 4: Creating target...")
df['future_return'] = df['close'].pct_change(1).shift(-1)
df['target'] = 1
df.loc[df['future_return'] > 0.005, 'target'] = 2
df.loc[df['future_return'] < -0.005, 'target'] = 0
df = df.dropna()

print(f"✓ Target distribution:")
for label, count in df['target'].value_counts().sort_index().items():
    print(f"  {['DOWN', 'NEUTRAL', 'UP'][label]}: {count} ({count/len(df)*100:.1f}%)")

# Step 5: Train
print("\nStep 5: Training model...")
X = df[feature_columns]
y = df['target']

split_idx = int(len(df) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

print(f"Train: {len(X_train)}, Test: {len(X_test)}")

models = {
    'randomforest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1, class_weight='balanced'),
    'extratrees': ExtraTreesClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1, class_weight='balanced'),
    'histgb': HistGradientBoostingClassifier(max_iter=100, random_state=42),
    'gb_classifier': GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42),
}

trained_models = {}
for name, model in models.items():
    print(f"  Training {name}...", end=" ")
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    trained_models[name] = model
    print(f"✓ {score:.4f}")

meta_features_train = []
meta_features_test = []
for name, model in trained_models.items():
    meta_features_train.append(model.predict_proba(X_train))
    meta_features_test.append(model.predict_proba(X_test))

X_meta_train = np.hstack(meta_features_train)
X_meta_test = np.hstack(meta_features_test)

meta_classifier = LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced')
meta_classifier.fit(X_meta_train, y_train)
meta_score = meta_classifier.score(X_meta_test, y_test)
print(f"  Meta-classifier: ✓ {meta_score:.4f}")

calibrator = CalibratedClassifierCV(meta_classifier, cv=3, method='isotonic')
calibrator.fit(X_meta_train, y_train)
calibrated_score = calibrator.score(X_meta_test, y_test)
print(f"  Calibrated: ✓ {calibrated_score:.4f}")

# Step 6: Save
print("\nStep 6: Saving model...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
schema_hash = "d7a9e9fb3a42"

# Save calibrator
cal_file = f'calibrator_{timestamp}_{schema_hash}.joblib'
joblib.dump(calibrator, f"{MODEL_DIR}/{cal_file}")
print(f"✓ {cal_file}")

# Save FULL model with wrapper
full_model = SimpleMetaClassifier(
    base_models=trained_models,
    meta_model=meta_classifier,
    feature_columns=feature_columns
)
meta_file = f'meta_classifier_{timestamp}_{schema_hash}.joblib'
joblib.dump(full_model, f"{MODEL_DIR}/{meta_file}")
print(f"✓ {meta_file} (FULL MODEL - 17 features)")

# Save feature columns
feat_file = f'feature_columns_{timestamp}_{schema_hash}.json'
with open(f"{MODEL_DIR}/{feat_file}", 'w') as f:
    json.dump({"feature_cols": feature_columns, "schema_hash": schema_hash}, f)
print(f"✓ {feat_file}")

# Save metadata
meta_meta_file = f'training_meta_{timestamp}_{schema_hash}.json'
metadata = {
    'timestamp_utc': timestamp,
    'target': 'direction_confidence_5m',
    'n_features': 17,
    'schema_hash': schema_hash,
    'class_mapping': {'down': 0, 'neutral': 1, 'up': 2},
    'meta_score_in_sample': float(meta_score),
    'calibrated_score': float(calibrated_score),
    'training_samples': len(X_train),
    'test_samples': len(X_test),
    'data_start': str(df['timestamp'].min()),
    'data_end': str(df['timestamp'].max())
}
with open(f"{MODEL_DIR}/{meta_meta_file}", 'w') as f:
    json.dump(metadata, f, indent=2)
print(f"✓ {meta_meta_file}")

# Update LATEST.json
new_latest = {
    'meta_classifier': meta_file,
    'calibrator': cal_file,
    'feature_columns': feat_file,
    'training_meta': meta_meta_file
}
with open(f"{MODEL_DIR}/LATEST.json", 'w') as f:
    json.dump(new_latest, f, indent=2)
print(f"✓ LATEST.json updated")

print("\n" + "=" * 80)
print("✓ RETRAINING COMPLETE!")
print("=" * 80)
print(f"\nPerformance:")
print(f"  Training Accuracy: {meta_score:.2%}")
print(f"  Test Accuracy: {calibrated_score:.2%}")
print(f"\nData:")
print(f"  {len(df)} bars from {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
print(f"\nNext: Restart bot with: python run_5m_debug.py")
print("=" * 80)
