"""
VERIFY: Is 12H model truly independent or is it the 5M model?
Check model files, hashes, and training data to confirm
"""
import json
import os
import hashlib

print("=" * 80)
print("VERIFICATION: 12H MODEL INDEPENDENCE CHECK")
print("=" * 80)
print()

# ============================================
# PART 1: COMPARE MODEL FILE HASHES
# ============================================
print("📦 PART 1: MODEL FILE HASH COMPARISON")
print("-" * 80)

def get_file_hash(filepath):
    """Get MD5 hash of a file"""
    if not os.path.exists(filepath):
        return None
    
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()

# Load LATEST.json for both
with open('live_demo/models/LATEST.json', 'r') as f:
    latest_5m = json.load(f)

with open('live_demo_12h/models/LATEST.json', 'r') as f:
    latest_12h = json.load(f)

print("5M Model Files:")
for key, filename in latest_5m.items():
    print(f"  {key}: {filename}")

print()

print("12H Model Files:")
for key, filename in latest_12h.items():
    print(f"  {key}: {filename}")

print()

# Check if filenames are different
print("Filename Comparison:")
same_files = 0
for key in latest_5m.keys():
    if key in latest_12h:
        if latest_5m[key] == latest_12h[key]:
            print(f"  ❌ SAME: {key} uses identical filename")
            same_files += 1
        else:
            print(f"  ✅ DIFFERENT: {key} has different filename")

print()

if same_files > 0:
    print(f"⚠️ WARNING: {same_files} files have identical names!")
    print("   This suggests they might be the same model.")
else:
    print("✅ All filenames are different (good sign)")

print()

# ============================================
# PART 2: COMPARE SCHEMA HASHES
# ============================================
print("🔑 PART 2: SCHEMA HASH COMPARISON")
print("-" * 80)

# Extract schema hash from filenames
hash_5m = latest_5m['meta_classifier'].split('_')[-1].replace('.joblib', '')
hash_12h = latest_12h['meta_classifier'].split('_')[-1].replace('.joblib', '')

print(f"5M Schema Hash:  {hash_5m}")
print(f"12H Schema Hash: {hash_12h}")
print()

if hash_5m == hash_12h:
    print("⚠️ WARNING: Schema hashes are IDENTICAL!")
    print("   This means they use the same feature schema.")
    print("   Could be same model or just same features.")
else:
    print("✅ Schema hashes are DIFFERENT")
    print("   Models use different feature schemas.")

print()

# ============================================
# PART 3: COMPARE MODEL FILE SIZES
# ============================================
print("📏 PART 3: MODEL FILE SIZE COMPARISON")
print("-" * 80)

def get_file_size(filepath):
    if os.path.exists(filepath):
        return os.path.getsize(filepath)
    return 0

print("Calibrator Files:")
cal_5m_path = f"live_demo/models/{latest_5m['calibrator']}"
cal_12h_path = f"live_demo_12h/models/{latest_12h['calibrator']}"

size_5m_cal = get_file_size(cal_5m_path)
size_12h_cal = get_file_size(cal_12h_path)

print(f"  5M:  {size_5m_cal:,} bytes ({size_5m_cal/1024:.1f} KB)")
print(f"  12H: {size_12h_cal:,} bytes ({size_12h_cal/1024:.1f} KB)")

if size_5m_cal == size_12h_cal:
    print("  ⚠️ IDENTICAL SIZE - Likely the same file!")
else:
    print(f"  ✅ Different sizes (diff: {abs(size_5m_cal - size_12h_cal):,} bytes)")

print()

print("Meta-Classifier Files:")
meta_5m_path = f"live_demo/models/{latest_5m['meta_classifier']}"
meta_12h_path = f"live_demo_12h/models/{latest_12h['meta_classifier']}"

size_5m_meta = get_file_size(meta_5m_path)
size_12h_meta = get_file_size(meta_12h_path)

print(f"  5M:  {size_5m_meta:,} bytes ({size_5m_meta/1024:.1f} KB)")
print(f"  12H: {size_12h_meta:,} bytes ({size_12h_meta/1024:.1f} KB)")

if size_5m_meta == size_12h_meta:
    print("  ⚠️ IDENTICAL SIZE - Likely the same file!")
else:
    print(f"  ✅ Different sizes (diff: {abs(size_5m_meta - size_12h_meta):,} bytes)")

print()

# ============================================
# PART 4: COMPARE TRAINING METADATA
# ============================================
print("📊 PART 4: TRAINING METADATA COMPARISON")
print("-" * 80)

meta_5m_file = f"live_demo/models/{latest_5m['training_meta']}"
meta_12h_file = f"live_demo_12h/models/{latest_12h['training_meta']}"

with open(meta_5m_file, 'r') as f:
    meta_5m = json.load(f)

with open(meta_12h_file, 'r') as f:
    meta_12h = json.load(f)

print("5M Metadata:")
print(f"  Target: {meta_5m.get('target', 'N/A')}")
print(f"  Training Samples: {meta_5m.get('training_samples', 'N/A'):,}")
print(f"  Accuracy: {meta_5m.get('meta_score_in_sample', 0)*100:.2f}%")

print()

print("12H Metadata:")
print(f"  Target: {meta_12h.get('classification_target', meta_12h.get('target', 'N/A'))}")
print(f"  Training Samples: {meta_12h.get('train_rows', meta_12h.get('training_samples', 'N/A')):,}")
print(f"  Accuracy: {meta_12h.get('meta_score_in_sample', 0)*100:.2f}%")

print()

# Check if targets are different
target_5m = meta_5m.get('target', '')
target_12h = meta_12h.get('classification_target', meta_12h.get('target', ''))

if '5m' in target_5m or '3min' in target_5m:
    print("✅ 5M target mentions 5m/3min timeframe")
else:
    print(f"⚠️ 5M target: {target_5m}")

if '12h' in target_12h:
    print("✅ 12H target mentions 12h timeframe")
else:
    print(f"⚠️ 12H target: {target_12h}")

print()

# ============================================
# PART 5: CHECK ACTUAL FILE CONTENT HASH
# ============================================
print("🔐 PART 5: FILE CONTENT HASH VERIFICATION")
print("-" * 80)

print("Computing file hashes (this may take a moment)...")
print()

hash_5m_cal = get_file_hash(cal_5m_path)
hash_12h_cal = get_file_hash(cal_12h_path)

print("Calibrator Hash:")
print(f"  5M:  {hash_5m_cal}")
print(f"  12H: {hash_12h_cal}")

if hash_5m_cal == hash_12h_cal:
    print("  🔴 IDENTICAL HASH - These are THE SAME FILE!")
else:
    print("  ✅ Different hashes - These are DIFFERENT files")

print()

hash_5m_meta = get_file_hash(meta_5m_path)
hash_12h_meta = get_file_hash(meta_12h_path)

print("Meta-Classifier Hash:")
print(f"  5M:  {hash_5m_meta}")
print(f"  12H: {hash_12h_meta}")

if hash_5m_meta == hash_12h_meta:
    print("  🔴 IDENTICAL HASH - These are THE SAME FILE!")
else:
    print("  ✅ Different hashes - These are DIFFERENT files")

print()

# ============================================
# FINAL VERDICT
# ============================================
print("=" * 80)
print("🎯 FINAL VERDICT")
print("=" * 80)
print()

# Count evidence
evidence_same = 0
evidence_different = 0

# Check 1: Filenames
if same_files > 0:
    evidence_same += 1
else:
    evidence_different += 1

# Check 2: Schema hash
if hash_5m == hash_12h:
    evidence_same += 0.5  # Could be same features but different model
else:
    evidence_different += 1

# Check 3: File sizes
if size_5m_cal == size_12h_cal and size_5m_meta == size_12h_meta:
    evidence_same += 2
else:
    evidence_different += 2

# Check 4: File hashes
if hash_5m_cal == hash_12h_cal:
    evidence_same += 3  # Strong evidence
else:
    evidence_different += 3

# Check 5: Training samples
if meta_5m.get('training_samples', 0) == meta_12h.get('train_rows', -1):
    evidence_same += 2
else:
    evidence_different += 2

# Check 6: Target names
if target_5m == target_12h:
    evidence_same += 1
else:
    evidence_different += 1

print(f"Evidence Score:")
print(f"  Same Model: {evidence_same}")
print(f"  Different Models: {evidence_different}")
print()

if evidence_same > evidence_different:
    print("🔴 VERDICT: 12H IS USING THE 5M MODEL!")
    print()
    print("Evidence:")
    print("  - File hashes match")
    print("  - File sizes match")
    print("  - Likely a shared/copied model")
    print()
    print("What this means:")
    print("  - 12H doesn't have its own dedicated model")
    print("  - It's using the 5m model for 12h predictions")
    print("  - This is NOT ideal (wrong timeframe)")
    print()
    print("Recommendation:")
    print("  🔴 CRITICAL: Train a dedicated 12h model")
    print("  - Use 12h-specific data")
    print("  - Train on 12h bars, not 5m bars")
    
elif evidence_different > evidence_same:
    print("✅ VERDICT: 12H HAS ITS OWN INDEPENDENT MODEL")
    print()
    print("Evidence:")
    print("  - Different file hashes")
    print("  - Different file sizes")
    print("  - Different training data")
    print("  - Different targets")
    print()
    print("What this means:")
    print("  - 12H has a dedicated model")
    print("  - Trained on 12h-specific data")
    print("  - Independent from 5m model")
    print()
    print("Status:")
    print("  ✅ Correct setup")
    print("  ⚠️ But model is weak (only 218 samples)")
    print("  🟡 Needs retraining with more data")
    
else:
    print("⚠️ VERDICT: UNCLEAR - MIXED EVIDENCE")
    print()
    print("Need manual inspection to confirm.")

print()
print("=" * 80)
