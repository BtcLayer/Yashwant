"""
Test the newly trained 1h model
"""
import joblib
import json
import os

print("Testing 1h model...")
print("-" * 60)

# Load LATEST.json
latest_path = 'live_demo_1h/models/LATEST.json'
with open(latest_path, 'r') as f:
    latest = json.load(f)

print(f"✅ LATEST.json loaded")
print(f"   Meta-classifier: {latest['meta_classifier']}")
print(f"   Calibrator: {latest['calibrator']}")
print()

# Load meta-classifier
meta_path = f"live_demo_1h/models/{latest['meta_classifier']}"
meta_classifier = joblib.load(meta_path)
print(f"✅ Meta-classifier loaded successfully!")
print(f"   Type: {type(meta_classifier)}")
print(f"   Classes: {meta_classifier.classes_}")
print()

# Load calibrator
cal_path = f"live_demo_1h/models/{latest['calibrator']}"
calibrator = joblib.load(cal_path)
print(f"✅ Calibrator loaded successfully!")
print(f"   Type: {type(calibrator)}")
print()

# Load training metadata
meta_path = f"live_demo_1h/models/{latest['training_meta']}"
with open(meta_path, 'r') as f:
    training_meta = json.load(f)

print(f"✅ Training metadata:")
print(f"   Timestamp: {training_meta['timestamp_utc']}")
print(f"   Target: {training_meta['target']}")
print(f"   Features: {training_meta['n_features']}")
print(f"   Meta score: {training_meta['meta_score_in_sample']:.4f}")
print(f"   Calibrated score: {training_meta.get('calibrated_score', 'N/A')}")
print(f"   Training samples: {training_meta.get('training_samples', 'N/A')}")
print(f"   Test samples: {training_meta.get('test_samples', 'N/A')}")
print()

print("=" * 60)
print("🎉 1h MODEL IS READY TO USE!")
print("=" * 60)
print()
print("Next steps:")
print("1. Test the bot: python run_1h.py")
print("2. Monitor performance")
print("3. Compare with 5m model performance")
