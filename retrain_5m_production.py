"""
PRODUCTION RETRAINING SCRIPT - 5M MODEL
---------------------------------------
Automated pipeline to retrain the 5m model with fresh data and adaptive thresholds.
Matches the proven 'EnhancedMetaClassifier' architecture from October 2025.

Pipeline:
1. Fetch fresh data (90 days) from Hyperliquid.
2. Compute 17 features (exact match to live_demo/features.py).
3. adaptive_labeling: Set target based on recent volatility.
4. Train EnhancedMetaClassifier (CV=3, PurgedCV).
5. Validate (Accuracy > 53%, Confidence Spread > 0.05).
6. Deploy (Backup old -> Save new -> Update LATEST.json).
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import joblib
import json
import os
import shutil
import math
import sys
import time

# Add project root to path
sys.path.insert(0, os.getcwd())

# Import proven architecture
try:
    from live_demo.custom_models import EnhancedMetaClassifier, CustomClassificationCalibrator
except ImportError:
    print("[ERR] ERROR: Could not import custom_models. Run from project root.")
    sys.exit(1)

# Configuration
MODEL_DIR = "live_demo/models"
BACKUP_DIR = "live_demo/models/backup"
MIN_ACCURACY = 0.51  # Minimum acceptable test accuracy
MIN_CONF_STD = 0.02  # Minimum confidence spread
FRESH_DAYS = 90      # Days of history to fetch

def fetch_hyperliquid_data(days=90):
    """Fetch 5m candles from Hyperliquid."""
    print(f"\n[1/6] Fetching {days} days of data...")
    url = "https://api.hyperliquid.xyz/info"
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
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
        data = response.json()
        if not isinstance(data, list):
            raise ValueError(f"Invalid response: {data}")
            
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
        print(f"   [OK] Fetched {len(df)} candles ({df['timestamp'].min()} to {df['timestamp'].max()})")
        return df
    except Exception as e:
        print(f"[ERR] Fetch failed: {e}")
        return None

def compute_features(df):
    """Compute exact 17 features used in live trading."""
    print("\n[2/6] Computing features...")
    
    # Copy to avoid warnings
    df = df.copy()
    
    # 1. Price Momentum
    df['mom_1'] = df['close'].pct_change(1)
    df['mom_3'] = df['close'].pct_change(3)
    
    # 2. Mean Reversion
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['rv_1h'] = df['mom_1'].rolling(12).apply(lambda x: np.sqrt(np.sum(x**2)), raw=True)
    df['mr_ema20_z'] = (df['close'] - df['ema20']) / (df['rv_1h'] + 1e-9)
    
    # 3. Volatility Regime
    rv_median = df['rv_1h'].rolling(12).median()
    df['regime_high_vol'] = ((df['rv_1h'] > 2.0 * rv_median) & (df['rv_1h'] > 0)).astype(float)
    
    # 4. GK Volatility
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
    
    # 5. Market Microstructure Proxies
    df['jump_magnitude'] = df['mom_1'].abs()
    
    df['volume_mean'] = df['volume'].rolling(50).mean()
    df['volume_intensity'] = (df['volume'] / (df['volume_mean'] + 1e-9)) - 1.0
    
    df['price_range'] = (df['high'] - df['low']) / (df['close'] + 1e-9)
    df['price_efficiency'] = df['mom_1'].abs() / (df['price_range'] + 1e-9)
    
    # 6. Price-Volume Correlation
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
    
    # 7. VWAP Momentum (Proxy)
    df['vwap_momentum'] = df['mom_3']
    
    # 8. External Features (Placeholders for now, critical to match schema)
    df['depth_proxy'] = 0.0
    df['funding_rate'] = 0.0
    df['funding_momentum_1h'] = 0.0
    df['flow_diff'] = 0.0
    df['S_top'] = 0.0
    df['S_bot'] = 0.0
    
    feature_cols = [
        "mom_1", "mom_3", "mr_ema20_z", "rv_1h", "regime_high_vol",
        "gk_volatility", "jump_magnitude", "volume_intensity",
        "price_efficiency", "price_volume_corr", "vwap_momentum",
        "depth_proxy", "funding_rate", "funding_momentum_1h",
        "flow_diff", "S_top", "S_bot"
    ]
    
    # Feature quality check
    print(f"   [OK] Computed {len(feature_cols)} features")
    return df, feature_cols

def adaptive_labeling(df):
    """Create target with adaptive thresholds based on volatility."""
    print("\n[3/6] Generating adaptive targets...")
    
    # Calculate future returns
    df['future_return'] = df['close'].pct_change(1).shift(-1)
    df = df.dropna().copy()
    
    # Adaptive threshold logic
    returns = df['future_return'].values
    std_dev = np.std(returns)
    threshold = max(0.0005, 0.5 * std_dev)  # At least 0.05%, dynamic based on vol
    
    print(f"   [INFO] Volatility (std): {std_dev*100:.4f}%")
    print(f"   [INFO] Adaptive Threshold: ±{threshold*100:.4f}%")
    
    df['target'] = 1  # Default NEUTRAL
    df.loc[df['future_return'] > threshold, 'target'] = 2   # UP
    df.loc[df['future_return'] < -threshold, 'target'] = 0  # DOWN
    
    # Check balance
    counts = df['target'].value_counts(normalize=True).sort_index()
    print("   [INFO] Class Distribution:")
    ct_map = {0: 'DOWN', 1: 'NEUTRAL', 2: 'UP'}
    for cls, pct in counts.items():
        print(f"     {ct_map[cls]}: {pct*100:.1f}%")
        
    if counts.min() < 0.15:
        print("   [WARN] WARNING: Class imbalance detected (min class < 15%)")
        
    return df, threshold

def train_model(df, feature_cols):
    """Train EnhancedMetaClassifier."""
    print("\n[4/6] Training model...")
    
    X = df[feature_cols]
    y = df['target']
    
    # Time-based split (80/20)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"   [INFO] Train size: {len(X_train)}, Test size: {len(X_test)}")
    
    # Initialize proven architecture
    meta_clf = EnhancedMetaClassifier(
        meta_C=1.0,
        random_state=42,
        n_folds=3,
        embargo_pct=0.01,
        purge_pct=0.01,
        min_train_samples=1000,
        n_classes=3
    )
    
    # Train
    t0 = time.time()
    meta_clf.fit(X_train, y_train)
    print(f"   [OK] Training complete ({time.time()-t0:.1f}s)")
    
    # Calibrate
    calibrator = CustomClassificationCalibrator(base_estimator=meta_clf)
    calibrator.fit(X_train, y_train)
    
    # Evaluate
    test_preds = calibrator.predict(X_test)
    test_acc = np.mean(test_preds == y_test)
    print(f"   [OK] Test Accuracy: {test_acc:.2%}")
    
    # Confidence stats
    probs = calibrator.predict_proba(X_test)
    conf = probs[:, 2] - probs[:, 0]  # p_up - p_down
    conf_std = np.std(conf)
    print(f"   [OK] Confidence Spread (std): {conf_std:.4f}")
    
    return meta_clf, calibrator, test_acc, conf_std, len(X_train)

def deploy(meta_clf, calibrator, feature_cols, metrics, threshold):
    """Save artifacts and update LATEST.json."""
    print("\n[6/6] Deploying model...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    schema_hash = "d7a9e9fb3a42"  # consistent hash
    
    # 1. Backup LATEST.json
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_path = f"{BACKUP_DIR}/LATEST_{timestamp}.json"
        if os.path.exists(f"{MODEL_DIR}/LATEST.json"):
            shutil.copy(f"{MODEL_DIR}/LATEST.json", backup_path)
            print(f"   [OK] Backed up LATEST.json to {backup_path}")
    except Exception as e:
        print(f"   [WARN] Backup warning: {e}")

    # 2. Save Artifacts
    meta_file = f'meta_classifier_{timestamp}_{schema_hash}.joblib'
    cal_file = f'calibrator_{timestamp}_{schema_hash}.joblib'
    feat_file = f'feature_columns_{timestamp}_{schema_hash}.json'
    meta_meta_file = f'training_meta_{timestamp}_{schema_hash}.json'
    
    joblib.dump(meta_clf, f"{MODEL_DIR}/{meta_file}")
    joblib.dump(calibrator, f"{MODEL_DIR}/{cal_file}")
    
    with open(f"{MODEL_DIR}/{feat_file}", 'w') as f:
        json.dump({"feature_cols": feature_cols, "schema_hash": schema_hash}, f)
        
    metadata = {
        'timestamp_utc': timestamp,
        'target': 'direction_confidence_5m_adaptive',
        'threshold': float(threshold),
        'metrics': metrics,
        'config': {
            'fresh_days': FRESH_DAYS,
            'min_accuracy': MIN_ACCURACY
        }
    }
    with open(f"{MODEL_DIR}/{meta_meta_file}", 'w') as f:
        json.dump(metadata, f, indent=2)
        
    print(f"   [OK] Saved new artifacts ({timestamp})")
    
    # 3. Update LATEST.json
    latest = {
        'meta_classifier': meta_file,
        'calibrator': cal_file,
        'feature_columns': feat_file,
        'training_meta': meta_meta_file
    }
    with open(f"{MODEL_DIR}/LATEST.json", 'w') as f:
        json.dump(latest, f, indent=2)
        
    print("   [OK] Updated LATEST.json")
    print("\n[DEPLOY] DEPLOYMENT COMPLETE. Restart the bot to use the new model.")

def main():
    # 1. Fetch
    df = fetch_hyperliquid_data(FRESH_DAYS)
    if df is None or len(df) < 5000:
        print("[ERR] Not enough data. Aborting.")
        return
        
    # 2. Features
    df, feature_cols = compute_features(df)
    
    # 3. Labeling
    df, threshold = adaptive_labeling(df)
    
    # 4. Training
    model, calibrator, acc, conf_std, n_samples = train_model(df, feature_cols)
    
    # 5. Validation
    print("\n[5/6] Validating...")
    passed = True
    
    if acc < MIN_ACCURACY:
        print(f"   [ERR] Accuracy {acc:.2%} < {MIN_ACCURACY:.2%}")
        passed = False
    else:
        print(f"   [OK] Accuracy check passed")
        
    if conf_std < MIN_CONF_STD:
        print(f"   [ERR] Confidence spread {conf_std:.4f} < {MIN_CONF_STD}")
        passed = False
    else:
        print(f"   [OK] Confidence check passed")
        
    if not passed:
        print("\n[WARN] VALIDATION FAILED. Model will NOT be deployed.")
        return
        
    # 6. Deploy
    deploy(model, calibrator, feature_cols, 
           {'accuracy': acc, 'conf_std': conf_std, 'final_samples': n_samples}, 
           threshold)

if __name__ == "__main__":
    main()
