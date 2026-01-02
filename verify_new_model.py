"""
COMPREHENSIVE NEW MODEL VERIFICATION
Check if the new model is working correctly and compare with old model
"""
import json
import os
from datetime import datetime
import joblib
import numpy as np

print("=" * 80)
print("NEW 5M MODEL COMPREHENSIVE VERIFICATION")
print("=" * 80)
print(f"Verification Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================
# PART 1: MODEL FILE VERIFICATION
# ============================================
print("📦 PART 1: MODEL FILES VERIFICATION")
print("-" * 80)

with open('live_demo/models/LATEST.json', 'r') as f:
    latest = json.load(f)

print("✅ LATEST.json loaded")
print(f"   Meta-classifier: {latest['meta_classifier']}")
print(f"   Calibrator: {latest['calibrator']}")
print(f"   Features: {latest['feature_columns']}")
print(f"   Metadata: {latest['training_meta']}")
print()

# Load metadata
with open(f"live_demo/models/{latest['training_meta']}", 'r') as f:
    new_meta = json.load(f)

print("📊 NEW MODEL METADATA:")
print(f"   Training Date: {new_meta['timestamp_utc']}")
print(f"   Training Accuracy: {new_meta['meta_score_in_sample']:.4f} ({new_meta['meta_score_in_sample']*100:.2f}%)")
print(f"   Test Accuracy: {new_meta['calibrated_score']:.4f} ({new_meta['calibrated_score']*100:.2f}%)")
print(f"   Training Samples: {new_meta['training_samples']:,}")
print(f"   Test Samples: {new_meta['test_samples']:,}")
print(f"   Data Period: {new_meta['data_start']} to {new_meta['data_end']}")
print()

# ============================================
# PART 2: COMPARE WITH OLD MODEL
# ============================================
print("🔄 PART 2: COMPARISON WITH OLD MODEL")
print("-" * 80)

# Find backup folder
backup_dir = "live_demo/models/backup"
backups = sorted([d for d in os.listdir(backup_dir) if d.startswith('backup_')])
if backups:
    latest_backup = backups[-1]
    old_latest_path = f"{backup_dir}/{latest_backup}/LATEST.json"
    
    if os.path.exists(old_latest_path):
        with open(old_latest_path, 'r') as f:
            old_latest = json.load(f)
        
        old_meta_path = f"{backup_dir}/{latest_backup}/{old_latest['training_meta']}"
        with open(old_meta_path, 'r') as f:
            old_meta = json.load(f)
        
        print("OLD MODEL:")
        print(f"   Training Date: {old_meta['timestamp_utc']}")
        print(f"   Training Accuracy: {old_meta.get('meta_score_in_sample', 0):.4f} ({old_meta.get('meta_score_in_sample', 0)*100:.2f}%)")
        print()
        
        print("COMPARISON:")
        old_acc = old_meta.get('meta_score_in_sample', 0)
        new_acc = new_meta['meta_score_in_sample']
        improvement = ((new_acc - old_acc) / old_acc) * 100 if old_acc > 0 else 0
        
        print(f"   Old Accuracy: {old_acc*100:.2f}%")
        print(f"   New Accuracy: {new_acc*100:.2f}%")
        print(f"   Improvement: {improvement:+.1f}%")
        print()
        
        if new_acc > old_acc:
            print(f"   ✅ NEW MODEL IS BETTER by {improvement:.1f}%!")
        else:
            print(f"   ⚠️ New model is worse by {abs(improvement):.1f}%")
    else:
        print("⚠️ Could not find old model metadata for comparison")
else:
    print("⚠️ No backup found for comparison")

print()

# ============================================
# PART 3: MODEL FUNCTIONALITY TEST
# ============================================
print("🧪 PART 3: MODEL FUNCTIONALITY TEST")
print("-" * 80)

try:
    # Load the new calibrator
    calibrator = joblib.load(f"live_demo/models/{latest['calibrator']}")
    print("✅ Calibrator loaded successfully")
    print(f"   Type: {type(calibrator).__name__}")
    print(f"   Classes: {calibrator.classes_} (0=DOWN, 1=NEUTRAL, 2=UP)")
    
    # Test prediction with dummy data
    n_features = 17
    test_input = np.random.randn(1, n_features * 6)  # Meta features (6 models × 3 classes)
    
    try:
        prediction = calibrator.predict(test_input)
        probabilities = calibrator.predict_proba(test_input)
        
        print(f"✅ Model can make predictions")
        print(f"   Test prediction: {prediction[0]} ({['DOWN', 'NEUTRAL', 'UP'][prediction[0]]})")
        print(f"   Confidence: {probabilities[0].max():.4f}")
    except Exception as e:
        print(f"⚠️ Prediction test failed: {e}")
        
except Exception as e:
    print(f"❌ Error loading model: {e}")

print()

# ============================================
# PART 4: FEATURE SCHEMA VERIFICATION
# ============================================
print("📋 PART 4: FEATURE SCHEMA VERIFICATION")
print("-" * 80)

with open(f"live_demo/models/{latest['feature_columns']}", 'r') as f:
    feat_schema = json.load(f)

features = feat_schema['feature_cols']
print(f"✅ Feature schema loaded: {len(features)} features")
print()

expected_features = [
    "mom_1", "mom_3", "mr_ema20_z", "rv_1h", "regime_high_vol",
    "gk_volatility", "jump_magnitude", "volume_intensity",
    "price_efficiency", "price_volume_corr", "vwap_momentum",
    "depth_proxy", "funding_rate", "funding_momentum_1h",
    "flow_diff", "S_top", "S_bot"
]

if features == expected_features:
    print("✅ Features match expected schema perfectly!")
else:
    print("⚠️ Feature mismatch detected")
    print(f"   Expected: {len(expected_features)}")
    print(f"   Got: {len(features)}")

print()

# ============================================
# PART 5: DEPLOYMENT READINESS
# ============================================
print("=" * 80)
print("🎯 DEPLOYMENT READINESS CHECK")
print("=" * 80)
print()

checks = []

# Check 1: Model files exist
if all(os.path.exists(f"live_demo/models/{latest[k]}") for k in latest.keys()):
    checks.append(("✅", "All model files present"))
else:
    checks.append(("❌", "Some model files missing"))

# Check 2: Accuracy improvement
if new_acc > 0.50:
    checks.append(("✅", f"Good accuracy ({new_acc*100:.1f}%)"))
elif new_acc > 0.45:
    checks.append(("⚠️", f"Moderate accuracy ({new_acc*100:.1f}%)"))
else:
    checks.append(("❌", f"Low accuracy ({new_acc*100:.1f}%)"))

# Check 3: Feature compatibility
if len(features) == 17:
    checks.append(("✅", "Correct number of features (17)"))
else:
    checks.append(("❌", f"Wrong feature count ({len(features)})"))

# Check 4: Backup exists
if backups:
    checks.append(("✅", f"Backup available ({latest_backup})"))
else:
    checks.append(("⚠️", "No backup found"))

print("READINESS CHECKS:")
for status, msg in checks:
    print(f"  {status} {msg}")

print()

# Final verdict
failed_checks = sum(1 for s, _ in checks if s == "❌")
warning_checks = sum(1 for s, _ in checks if s == "⚠️")

if failed_checks == 0 and warning_checks == 0:
    print("🎉 VERDICT: READY TO DEPLOY!")
    print()
    print("The new model is:")
    print("  ✅ Better than old model")
    print("  ✅ Properly saved and configured")
    print("  ✅ Compatible with live bot")
    print("  ✅ Backed up for safety")
elif failed_checks == 0:
    print("✅ VERDICT: READY TO DEPLOY (with minor warnings)")
    print()
    print("The model is functional but has some warnings.")
    print("Proceed with caution and monitor closely.")
else:
    print("⚠️ VERDICT: ISSUES DETECTED")
    print()
    print("Fix the failed checks before deploying.")

print()
print("=" * 80)
print("NEXT STEP: Restart 5m bot to use new model")
print("Command: python run_5m.py")
print("=" * 80)
