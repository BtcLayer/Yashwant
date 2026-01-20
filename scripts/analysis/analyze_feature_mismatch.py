"""
ANALYZE OLD MODEL vs NEW MODEL
Find the feature mismatch issue
"""
import joblib
import json
import os

print("=" * 80)
print("FEATURE MISMATCH ANALYSIS")
print("=" * 80)
print()

# ============================================
# PART 1: ANALYZE OLD MODEL (WORKING)
# ============================================
print("📊 PART 1: OLD MODEL (WORKING)")
print("-" * 80)

# Find backup
backup_dir = "live_demo/models/backup"
backups = sorted([d for d in os.listdir(backup_dir) if d.startswith('backup_')])

if backups:
    latest_backup = backups[-1]
    print(f"Backup folder: {latest_backup}")
    
    # Load old LATEST.json
    old_latest_path = f"{backup_dir}/{latest_backup}/LATEST.json"
    with open(old_latest_path, 'r') as f:
        old_latest = json.load(f)
    
    print(f"\nOld model files:")
    print(f"  Meta: {old_latest['meta_classifier']}")
    print(f"  Calibrator: {old_latest['calibrator']}")
    
    # Load old meta-classifier
    old_meta_path = f"{backup_dir}/{latest_backup}/{old_latest['meta_classifier']}"
    old_meta = joblib.load(old_meta_path)
    
    print(f"\nOld Meta-Classifier:")
    print(f"  Type: {type(old_meta).__name__}")
    print(f"  Expected features: {old_meta.n_features_in_ if hasattr(old_meta, 'n_features_in_') else 'Unknown'}")
    if hasattr(old_meta, 'coef_'):
        print(f"  Coef shape: {old_meta.coef_.shape}")
        print(f"  Classes: {old_meta.classes_}")
    
    # Load old feature schema
    old_feat_path = f"{backup_dir}/{latest_backup}/{old_latest['feature_columns']}"
    with open(old_feat_path, 'r') as f:
        old_feat = json.load(f)
    
    print(f"\nOld Feature Schema:")
    print(f"  Base features: {len(old_feat['feature_cols'])}")
    print(f"  Features: {old_feat['feature_cols']}")
    
    # Load old metadata
    old_meta_meta_path = f"{backup_dir}/{latest_backup}/{old_latest['training_meta']}"
    with open(old_meta_meta_path, 'r') as f:
        old_meta_meta = json.load(f)
    
    print(f"\nOld Training Info:")
    if 'cv_scores' in old_meta_meta:
        print(f"  Base models: {len(old_meta_meta['cv_scores'])}")
        for model_name in old_meta_meta['cv_scores'].keys():
            print(f"    - {model_name}")

print()

# ============================================
# PART 2: ANALYZE NEW MODEL (BROKEN)
# ============================================
print("📊 PART 2: NEW MODEL (BROKEN)")
print("-" * 80)

with open('live_demo/models/LATEST.json', 'r') as f:
    new_latest = json.load(f)

print(f"New model files:")
print(f"  Meta: {new_latest['meta_classifier']}")
print(f"  Calibrator: {new_latest['calibrator']}")

# Load new meta-classifier
new_meta = joblib.load(f"live_demo/models/{new_latest['meta_classifier']}")

print(f"\nNew Meta-Classifier:")
print(f"  Type: {type(new_meta).__name__}")
print(f"  Expected features: {new_meta.n_features_in_ if hasattr(new_meta, 'n_features_in_') else 'Unknown'}")
if hasattr(new_meta, 'coef_'):
    print(f"  Coef shape: {new_meta.coef_.shape}")
    print(f"  Classes: {new_meta.classes_}")

# Load new feature schema
with open(f"live_demo/models/{new_latest['feature_columns']}", 'r') as f:
    new_feat = json.load(f)

print(f"\nNew Feature Schema:")
print(f"  Base features: {len(new_feat['feature_cols'])}")
print(f"  Features: {new_feat['feature_cols']}")

# Load new metadata
with open(f"live_demo/models/{new_latest['training_meta']}", 'r') as f:
    new_meta_meta = json.load(f)

print(f"\nNew Training Info:")
if 'cv_scores' in new_meta_meta:
    print(f"  Base models: {len(new_meta_meta['cv_scores'])}")
    for model_name in new_meta_meta['cv_scores'].keys():
        print(f"    - {model_name}")

print()

# ============================================
# PART 3: IDENTIFY THE MISMATCH
# ============================================
print("=" * 80)
print("🔍 MISMATCH ANALYSIS")
print("=" * 80)
print()

old_meta_features = old_meta.n_features_in_ if hasattr(old_meta, 'n_features_in_') else 0
new_meta_features = new_meta.n_features_in_ if hasattr(new_meta, 'n_features_in_') else 0

print(f"Old meta-classifier expects: {old_meta_features} features")
print(f"New meta-classifier expects: {new_meta_features} features")
print()

old_base_count = len(old_meta_meta.get('cv_scores', {}))
new_base_count = len(new_meta_meta.get('cv_scores', {}))

print(f"Old base models: {old_base_count}")
print(f"New base models: {new_base_count}")
print()

# Calculate expected meta features
print("Expected meta-features calculation:")
print(f"  Old: {old_base_count} models × 3 classes = {old_base_count * 3} meta-features")
print(f"  New: {new_base_count} models × 3 classes = {new_base_count * 3} meta-features")
print()

# ============================================
# PART 4: ROOT CAUSE
# ============================================
print("=" * 80)
print("🎯 ROOT CAUSE")
print("=" * 80)
print()

if new_meta_features == 18 and new_base_count == 6:
    print("✅ Meta-classifier is CORRECT (6 models × 3 classes = 18)")
    print()
    print("🔴 PROBLEM: The issue is in how predictions are being fed to meta-classifier")
    print()
    print("Likely causes:")
    print("  1. One base model is not being used during inference")
    print("  2. Predictions are being concatenated incorrectly")
    print("  3. Feature order mismatch")
    
elif new_meta_features != new_base_count * 3:
    print(f"🔴 PROBLEM: Meta-classifier expects {new_meta_features} but should expect {new_base_count * 3}")
    print()
    print("This happened during training - meta-classifier was trained wrong")

print()

# ============================================
# PART 5: SOLUTION
# ============================================
print("=" * 80)
print("✅ SOLUTION")
print("=" * 80)
print()

print("The training script needs to:")
print()
print("1. Train exactly 6 base models:")
for model_name in new_meta_meta.get('cv_scores', {}).keys():
    print(f"   - {model_name}")
print()

print("2. During meta-training:")
print("   - Get predictions from ALL 6 models")
print("   - Each model outputs 3 probabilities (DOWN, NEUTRAL, UP)")
print("   - Concatenate: 6 models × 3 probs = 18 features")
print("   - Train meta-classifier on these 18 features")
print()

print("3. During inference (live bot):")
print("   - Get predictions from ALL 6 models (same order)")
print("   - Concatenate in SAME order as training")
print("   - Feed 18 features to meta-classifier")
print()

print("🔴 CURRENT ISSUE:")
print("   The live bot is only getting 17 features instead of 18")
print("   This means one model's predictions are missing OR")
print("   predictions are being concatenated wrong")

print()
print("=" * 80)
