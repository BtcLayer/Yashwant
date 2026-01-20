"""
Simplified Model Training Script for MetaStackerBandit
Train models for 1h, 12h, or 24h timeframes

This is easier than using Jupyter notebooks - just run it!
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
import joblib
import json
from datetime import datetime
import os

# ============================================
# CONFIGURATION - CHANGE THIS FOR EACH TIMEFRAME
# ============================================
TIMEFRAME = "1h"  # Change to "1h", "12h", or "24h"
DATA_FILE = "ohlc_btc_1h.csv"  # Change to match timeframe
OUTPUT_DIR = f"live_demo_{TIMEFRAME}/models"  # Where to save models

# For 1h: use "1h" and "ohlc_btc_1h.csv"
# For 24h: use "24h" and "ohlc_btc_24h.csv"
# For 12h: use "12h" and "ohlc_btc_12h.csv"

print("=" * 70)
print(f"MetaStackerBandit Model Training - {TIMEFRAME} Timeframe")
print("=" * 70)
print()

# ============================================
# STEP 1: LOAD DATA
# ============================================
print("📂 Step 1: Loading data...")
print("-" * 70)

df = pd.read_csv(DATA_FILE)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"✅ Loaded {len(df)} candles")
print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print()

# ============================================
# STEP 2: CREATE FEATURES
# ============================================
print("🔧 Step 2: Creating features...")
print("-" * 70)

def create_features(df, timeframe="1h"):
    """Create technical indicators as features"""
    
    # Adjust windows based on timeframe
    if timeframe == "1h":
        short_window = 5
        med_window = 20
        long_window = 50
    elif timeframe == "24h":
        short_window = 7
        med_window = 30
        long_window = 90
    else:  # 12h
        short_window = 5
        med_window = 14
        long_window = 30
    
    # Returns
    df['returns_1'] = df['close'].pct_change(1)
    df['returns_short'] = df['close'].pct_change(short_window)
    df['returns_med'] = df['close'].pct_change(med_window)
    
    # Volatility
    df['volatility'] = df['returns_1'].rolling(med_window).std()
    
    # Moving averages
    df['sma_short'] = df['close'].rolling(short_window).mean()
    df['sma_med'] = df['close'].rolling(med_window).mean()
    df['sma_long'] = df['close'].rolling(long_window).mean()
    
    # Price relative to MAs
    df['price_vs_sma_short'] = (df['close'] - df['sma_short']) / df['sma_short']
    df['price_vs_sma_med'] = (df['close'] - df['sma_med']) / df['sma_med']
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Volume features
    df['volume_sma'] = df['volume'].rolling(med_window).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    
    # High-Low range
    df['hl_range'] = (df['high'] - df['low']) / df['close']
    
    # Momentum
    df['momentum'] = df['close'] - df['close'].shift(short_window)
    
    return df

df = create_features(df, TIMEFRAME)

# Define feature columns
feature_columns = [
    'returns_1', 'returns_short', 'returns_med',
    'volatility', 'price_vs_sma_short', 'price_vs_sma_med',
    'rsi', 'volume_ratio', 'hl_range', 'momentum'
]

print(f"✅ Created {len(feature_columns)} features")
print(f"   Features: {', '.join(feature_columns)}")
print()

# ============================================
# STEP 3: CREATE TARGET VARIABLE
# ============================================
print("🎯 Step 3: Creating target variable...")
print("-" * 70)

# Predict future direction
df['future_return'] = df['close'].pct_change(1).shift(-1)

# Define thresholds for classification
up_threshold = 0.005  # 0.5% increase = UP
down_threshold = -0.005  # 0.5% decrease = DOWN

df['target'] = 1  # Default to NEUTRAL
df.loc[df['future_return'] > up_threshold, 'target'] = 2  # UP
df.loc[df['future_return'] < down_threshold, 'target'] = 0  # DOWN

# Remove NaN values
df = df.dropna()

print(f"✅ Target distribution:")
target_counts = df['target'].value_counts().sort_index()
for label, count in target_counts.items():
    label_name = ['DOWN', 'NEUTRAL', 'UP'][label]
    pct = count / len(df) * 100
    print(f"   {label_name}: {count} ({pct:.1f}%)")
print()

# ============================================
# STEP 4: PREPARE TRAINING DATA
# ============================================
print("📊 Step 4: Preparing training/test split...")
print("-" * 70)

X = df[feature_columns]
y = df['target']

# Time-based split (80% train, 20% test)
split_idx = int(len(df) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

print(f"✅ Training samples: {len(X_train)}")
print(f"✅ Test samples: {len(X_test)}")
print()

# ============================================
# STEP 5: TRAIN BASE MODELS
# ============================================
print("🤖 Step 5: Training base models...")
print("-" * 70)

models = {
    'randomforest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
    'extratrees': ExtraTreesClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
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
    print(f"✅ Accuracy: {score:.4f}")

print()

# ============================================
# STEP 6: CREATE META-CLASSIFIER
# ============================================
print("🎯 Step 6: Creating meta-classifier (ensemble)...")
print("-" * 70)

# Stack predictions from all base models
meta_features_train = []
meta_features_test = []

for name, model in trained_models.items():
    pred_train = model.predict_proba(X_train)
    pred_test = model.predict_proba(X_test)
    meta_features_train.append(pred_train)
    meta_features_test.append(pred_test)

# Combine predictions
X_meta_train = np.hstack(meta_features_train)
X_meta_test = np.hstack(meta_features_test)

# Train meta-classifier
meta_classifier = LogisticRegression(random_state=42, max_iter=1000)
meta_classifier.fit(X_meta_train, y_train)

meta_score = meta_classifier.score(X_meta_test, y_test)
print(f"✅ Meta-classifier accuracy: {meta_score:.4f}")
print()

# ============================================
# STEP 7: CALIBRATE MODEL
# ============================================
print("📐 Step 7: Calibrating probabilities...")
print("-" * 70)

calibrator = CalibratedClassifierCV(meta_classifier, cv=3, method='isotonic')
calibrator.fit(X_meta_train, y_train)

calibrated_score = calibrator.score(X_meta_test, y_test)
print(f"✅ Calibrated accuracy: {calibrated_score:.4f}")
print()

# ============================================
# STEP 8: SAVE MODELS
# ============================================
print("💾 Step 8: Saving models...")
print("-" * 70)

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Generate timestamp and hash
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
schema_hash = f"hash_{TIMEFRAME}_{timestamp[:8]}"

# Save meta-classifier
meta_file = f'meta_classifier_{timestamp}_{schema_hash}.joblib'
joblib.dump(meta_classifier, os.path.join(OUTPUT_DIR, meta_file))
print(f"✅ Saved: {meta_file}")

# Save calibrator
cal_file = f'calibrator_{timestamp}_{schema_hash}.joblib'
joblib.dump(calibrator, os.path.join(OUTPUT_DIR, cal_file))
print(f"✅ Saved: {cal_file}")

# Save feature columns
feat_file = f'feature_columns_{timestamp}_{schema_hash}.json'
with open(os.path.join(OUTPUT_DIR, feat_file), 'w') as f:
    json.dump(feature_columns, f)
print(f"✅ Saved: {feat_file}")

# Save training metadata
metadata = {
    'timestamp_utc': timestamp,
    'target': f'direction_confidence_{TIMEFRAME}',
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
    'test_samples': len(X_test)
}

meta_meta_file = f'training_meta_{timestamp}_{schema_hash}.json'
with open(os.path.join(OUTPUT_DIR, meta_meta_file), 'w') as f:
    json.dump(metadata, f, indent=2)
print(f"✅ Saved: {meta_meta_file}")

# Create LATEST.json with enhanced metadata
try:
    from live_demo.models.manifest_utils import enhance_manifest
    
    # Base manifest
    latest = {
        'meta_classifier': meta_file,
        'calibrator': cal_file,
        'feature_columns': feat_file,
        'training_meta': meta_meta_file
    }
    
    # Enhance with metadata (git_commit, trained_at_utc, feature_dim)
    latest = enhance_manifest(
        latest,
        feature_file_path=os.path.join(OUTPUT_DIR, feat_file)
    )
    print(f"✅ Enhanced manifest with metadata:")
    print(f"   - git_commit: {latest.get('git_commit')}")
    print(f"   - trained_at_utc: {latest.get('trained_at_utc')}")
    print(f"   - feature_dim: {latest.get('feature_dim')}")
    
except ImportError:
    # Fallback if manifest_utils not available
    latest = {
        'meta_classifier': meta_file,
        'calibrator': cal_file,
        'feature_columns': feat_file,
        'training_meta': meta_meta_file
    }
    print(f"⚠️  manifest_utils not available, using basic manifest")

with open(os.path.join(OUTPUT_DIR, 'LATEST.json'), 'w') as f:
    json.dump(latest, f, indent=2)
print(f"✅ Saved: LATEST.json")


print()
print("=" * 70)
print("🎉 MODEL TRAINING COMPLETE!")
print("=" * 70)
print()
print(f"📁 Models saved to: {OUTPUT_DIR}")
print()
print("📊 Performance Summary:")
print(f"   Meta-classifier accuracy: {meta_score:.4f}")
print(f"   Calibrated accuracy: {calibrated_score:.4f}")
print(f"   Training samples: {len(X_train)}")
print(f"   Test samples: {len(X_test)}")
print()
print("✅ Next steps:")
print(f"   1. Test the model: python run_{TIMEFRAME}.py")
print(f"   2. Monitor performance in dry-run mode")
print(f"   3. If good, enable live trading")
print()
print("=" * 70)
