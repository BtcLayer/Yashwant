"""
Compare current model vs what we can train with available data
"""
import json

print("=" * 80)
print("CURRENT MODEL vs NEW MODEL COMPARISON")
print("=" * 80)
print()

# Load current model metadata
with open('live_demo/models/training_meta_20251018_101628_d7a9e9fb3a42.json', 'r') as f:
    current_meta = json.load(f)

print("CURRENT MODEL (October 18, 2025):")
print("-" * 80)
print(f"Training Date: {current_meta['timestamp_utc']}")
print(f"Features: {current_meta['n_features']}")
print(f"Training Accuracy: {current_meta['meta_score_in_sample']:.4f} ({current_meta['meta_score_in_sample']*100:.2f}%)")
print(f"Age: 75 days old")
print()

# The metadata doesn't show training samples, but based on model size (74.5 MB)
# and typical sklearn model sizes, estimate was trained on significant data
print("Estimated training data:")
print("  Model file size: 74.5 MB")
print("  This suggests: Likely 20,000-50,000+ samples")
print("  (Large model size indicates substantial training data)")
print()

print("=" * 80)
print()

print("NEW MODEL (With Available Data):")
print("-" * 80)
print(f"Available Data: 5,008 candles")
print(f"Training split (80%): ~4,006 samples")
print(f"Test split (20%): ~1,002 samples")
print(f"Data period: Last 17 days (Dec 15, 2025 - Jan 1, 2026)")
print()

print("=" * 80)
print("COMPARISON")
print("=" * 80)
print()

print("Current Model:")
print("  ✅ Trained on more data (estimated 20k-50k+ samples)")
print("  ✅ Larger time period (months of data)")
print("  ❌ 75 days old (stale patterns)")
print("  ❌ Low accuracy (43%)")
print("  ❌ Not profitable")
print()

print("New Model (with 5,008 candles):")
print("  ✅ Fresh data (last 17 days)")
print("  ✅ Recent market patterns")
print("  ❌ Less training data (~4,000 vs 20k-50k+)")
print("  ❌ Shorter time period (17 days vs months)")
print("  ⚠️ May not capture all market conditions")
print()

print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()

print("Given the comparison:")
print()
print("Option A: Train with 5,008 candles")
print("  Pros: Fresh patterns, recent data")
print("  Cons: Limited data, may miss patterns")
print("  Risk: Medium - might not be better than current")
print()

print("Option B: Keep current model, optimize parameters")
print("  Pros: More training data, proven structure")
print("  Cons: Stale patterns, already not profitable")
print("  Risk: Low - but limited improvement potential")
print()

print("Option C: Wait 2-3 weeks to collect more data")
print("  Pros: Best of both (fresh + sufficient data)")
print("  Cons: Must wait")
print("  Risk: Low - most likely to succeed")
print()

print("My recommendation: Option C (wait and collect)")
print("  - Let bot run and collect data")
print("  - In 2-3 weeks, have 10k+ fresh candles")
print("  - Then retrain with confidence")
print()

print("Alternative: Option A if you want to try now")
print("  - Accept risk of limited data")
print("  - Can always retrain again later")
print()

print("=" * 80)
