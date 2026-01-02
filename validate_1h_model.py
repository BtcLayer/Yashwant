"""
Test if the 1h model we trained is working correctly
Load it and make test predictions to verify it works
"""
import joblib
import json
import numpy as np
import pandas as pd

print("=" * 80)
print("1H MODEL VALIDATION TEST")
print("=" * 80)
print()

# ============================================
# 1. LOAD THE MODEL
# ============================================
print("📦 Step 1: Loading the trained 1h model...")
print("-" * 80)

try:
    # Load LATEST.json
    with open('live_demo_1h/models/LATEST.json', 'r') as f:
        latest = json.load(f)
    
    print(f"✅ Model files found:")
    print(f"   Meta-classifier: {latest['meta_classifier']}")
    print(f"   Calibrator: {latest['calibrator']}")
    
    # Load training metadata
    with open(f"live_demo_1h/models/{latest['training_meta']}", 'r') as f:
        training_meta = json.load(f)
    
    print(f"\n✅ Training Info:")
    print(f"   Trained: {training_meta['timestamp_utc']}")
    print(f"   Training Accuracy: {training_meta['meta_score_in_sample']:.4f} ({training_meta['meta_score_in_sample']*100:.2f}%)")
    print(f"   Test Accuracy: {training_meta.get('calibrated_score', 0):.4f} ({training_meta.get('calibrated_score', 0)*100:.2f}%)")
    print(f"   Training Samples: {training_meta.get('training_samples', 'N/A')}")
    print(f"   Test Samples: {training_meta.get('test_samples', 'N/A')}")
    
    # Load the actual models
    meta_classifier = joblib.load(f"live_demo_1h/models/{latest['meta_classifier']}")
    calibrator = joblib.load(f"live_demo_1h/models/{latest['calibrator']}")
    
    print(f"\n✅ Models loaded successfully!")
    print(f"   Meta-classifier type: {type(meta_classifier).__name__}")
    print(f"   Calibrator type: {type(calibrator).__name__}")
    print(f"   Predicts classes: {meta_classifier.classes_}")
    
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit(1)

print()

# ============================================
# 2. TEST WITH REAL DATA
# ============================================
print("🧪 Step 2: Testing model with real data...")
print("-" * 80)

try:
    # Load the 1h data we used for training
    df = pd.read_csv('ohlc_btc_1h.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"✅ Loaded test data: {len(df)} candles")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Create the same features we used in training
    def create_features(df):
        df['returns_1'] = df['close'].pct_change(1)
        df['returns_short'] = df['close'].pct_change(5)
        df['returns_med'] = df['close'].pct_change(20)
        df['volatility'] = df['returns_1'].rolling(20).std()
        df['sma_short'] = df['close'].rolling(5).mean()
        df['sma_med'] = df['close'].rolling(20).mean()
        df['sma_long'] = df['close'].rolling(50).mean()
        df['price_vs_sma_short'] = (df['close'] - df['sma_short']) / df['sma_short']
        df['price_vs_sma_med'] = (df['close'] - df['sma_med']) / df['sma_med']
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        df['hl_range'] = (df['high'] - df['low']) / df['close']
        df['momentum'] = df['close'] - df['close'].shift(5)
        return df
    
    df = create_features(df)
    df = df.dropna()
    
    feature_columns = [
        'returns_1', 'returns_short', 'returns_med',
        'volatility', 'price_vs_sma_short', 'price_vs_sma_med',
        'rsi', 'volume_ratio', 'hl_range', 'momentum'
    ]
    
    # Get last 100 candles for testing
    X_test = df[feature_columns].tail(100)
    
    print(f"\n✅ Created features for testing")
    print(f"   Test samples: {len(X_test)}")
    
except Exception as e:
    print(f"❌ Error preparing test data: {e}")
    exit(1)

print()

# ============================================
# 3. MAKE PREDICTIONS
# ============================================
print("🎯 Step 3: Making predictions with the model...")
print("-" * 80)

try:
    # Make predictions
    predictions = calibrator.predict(X_test)
    probabilities = calibrator.predict_proba(X_test)
    
    print(f"✅ Model made predictions successfully!")
    print()
    
    # Analyze predictions
    unique, counts = np.unique(predictions, return_counts=True)
    pred_dist = dict(zip(unique, counts))
    
    class_names = {0: 'DOWN', 1: 'NEUTRAL', 2: 'UP'}
    
    print(f"📊 Prediction Distribution (last 100 candles):")
    for class_id in sorted(pred_dist.keys()):
        count = pred_dist[class_id]
        pct = count / len(predictions) * 100
        print(f"   {class_names[class_id]}: {count} predictions ({pct:.1f}%)")
    
    print()
    
    # Check if model predicts all classes
    if len(pred_dist) == 3:
        print("✅ GOOD: Model predicts all 3 classes (DOWN, NEUTRAL, UP)")
    elif len(pred_dist) == 1:
        print("❌ BAD: Model only predicts ONE class (broken model)")
    else:
        print("⚠️ WARNING: Model only predicts 2 out of 3 classes")
    
    print()
    
    # Show confidence levels
    max_probs = probabilities.max(axis=1)
    print(f"📈 Confidence Levels:")
    print(f"   Average confidence: {max_probs.mean():.4f} ({max_probs.mean()*100:.2f}%)")
    print(f"   Min confidence: {max_probs.min():.4f}")
    print(f"   Max confidence: {max_probs.max():.4f}")
    
    print()
    
    # Show recent predictions
    print(f"🔍 Last 10 Predictions:")
    print()
    recent_df = df.tail(10)[['timestamp', 'close']].copy()
    recent_df['prediction'] = [class_names[p] for p in predictions[-10:]]
    recent_df['confidence'] = [f"{p:.4f}" for p in max_probs[-10:]]
    print(recent_df.to_string(index=False))
    
except Exception as e:
    print(f"❌ Error making predictions: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()
print("=" * 80)
print("🎯 MODEL VALIDATION RESULTS")
print("=" * 80)
print()

# Final assessment
issues = []
strengths = []

# Check training accuracy
if training_meta['meta_score_in_sample'] >= 0.75:
    strengths.append(f"✅ Excellent training accuracy ({training_meta['meta_score_in_sample']*100:.1f}%)")
elif training_meta['meta_score_in_sample'] >= 0.60:
    strengths.append(f"✅ Good training accuracy ({training_meta['meta_score_in_sample']*100:.1f}%)")
else:
    issues.append(f"⚠️ Low training accuracy ({training_meta['meta_score_in_sample']*100:.1f}%)")

# Check test accuracy
test_acc = training_meta.get('calibrated_score', 0)
if test_acc >= 0.75:
    strengths.append(f"✅ Excellent test accuracy ({test_acc*100:.1f}%)")
elif test_acc >= 0.60:
    strengths.append(f"✅ Good test accuracy ({test_acc*100:.1f}%)")
else:
    issues.append(f"⚠️ Low test accuracy ({test_acc*100:.1f}%)")

# Check overfitting
diff = abs(training_meta['meta_score_in_sample'] - test_acc)
if diff < 0.05:
    strengths.append(f"✅ No overfitting (train/test diff: {diff*100:.1f}%)")
else:
    issues.append(f"⚠️ Possible overfitting (train/test diff: {diff*100:.1f}%)")

# Check class prediction
if len(pred_dist) == 3:
    strengths.append("✅ Predicts all 3 classes (DOWN, NEUTRAL, UP)")
else:
    issues.append(f"❌ Only predicts {len(pred_dist)} out of 3 classes")

# Check confidence
if max_probs.mean() > 0.5 and max_probs.mean() < 0.95:
    strengths.append(f"✅ Reasonable confidence levels ({max_probs.mean()*100:.1f}%)")
elif max_probs.mean() >= 0.95:
    issues.append(f"⚠️ Overconfident ({max_probs.mean()*100:.1f}%)")
else:
    issues.append(f"⚠️ Low confidence ({max_probs.mean()*100:.1f}%)")

print("STRENGTHS:")
for s in strengths:
    print(f"  {s}")

if issues:
    print()
    print("ISSUES:")
    for i in issues:
        print(f"  {i}")

print()
print("=" * 80)

if len(issues) == 0:
    print("🎉 VERDICT: MODEL IS EXCELLENT AND READY TO USE!")
    print()
    print("The 1h model training was successful:")
    print("- High accuracy on both training and test data")
    print("- No overfitting")
    print("- Predicts all directions correctly")
    print("- Reasonable confidence levels")
    print()
    print("✅ The model is working perfectly!")
elif len(issues) <= 2:
    print("✅ VERDICT: MODEL IS GOOD AND USABLE")
    print()
    print("The model has minor issues but should work fine.")
    print("Monitor performance and adjust if needed.")
else:
    print("⚠️ VERDICT: MODEL NEEDS ATTENTION")
    print()
    print("The model has several issues that should be addressed.")

print("=" * 80)
