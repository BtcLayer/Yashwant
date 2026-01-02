"""
12H MODEL ANALYSIS - SIMPLIFIED AND ROBUST
"""
import json
import os
from datetime import datetime

print("=" * 80)
print("12H TIMEFRAME MODEL ANALYSIS")
print("=" * 80)
print()

# Check if 12h has its own model
has_12h_model = os.path.exists('live_demo_12h/models/LATEST.json')

if has_12h_model:
    print("✅ 12H HAS ITS OWN MODEL")
    print()
    
    # Load model info
    with open('live_demo_12h/models/LATEST.json', 'r') as f:
        latest_12h = json.load(f)
    
    print("Model Files:")
    for key, filename in latest_12h.items():
        print(f"  - {filename}")
    print()
    
    # Load metadata
    meta_file = f"live_demo_12h/models/{latest_12h['training_meta']}"
    with open(meta_file, 'r') as f:
        meta_12h = json.load(f)
    
    print("=" * 80)
    print("MODEL DETAILS")
    print("=" * 80)
    print()
    
    # Extract timestamp from filename
    timestamp_str = latest_12h['meta_classifier'].split('_')[2]
    train_date = datetime.strptime(timestamp_str, '%Y%m%d')
    age_days = (datetime.now() - train_date).days
    
    print(f"Training Date: {train_date.strftime('%Y-%m-%d')}")
    print(f"Model Age: {age_days} days")
    print()
    
    print("Training Information:")
    print(f"  Timeframe: {meta_12h.get('timeframe', 'N/A')}")
    print(f"  Target: {meta_12h.get('classification_target', 'N/A')}")
    print(f"  Training Rows: {meta_12h.get('train_rows', 'N/A'):,}")
    print(f"  Calibration Rows: {meta_12h.get('calib_rows', 'N/A'):,}")
    print()
    
    print("Performance:")
    train_acc = meta_12h.get('meta_score_in_sample', 0)
    print(f"  Training Accuracy: {train_acc:.4f} ({train_acc*100:.2f}%)")
    print()
    
    if 'base_cv_scores' in meta_12h:
        print("Base Model Scores:")
        for model, score in meta_12h['base_cv_scores'].items():
            print(f"  {model:20s}: {score:.4f} ({score*100:.2f}%)")
    print()
    
    # Assessment
    print("=" * 80)
    print("ASSESSMENT")
    print("=" * 80)
    print()
    
    issues = []
    
    # Check age
    if age_days > 90:
        issues.append(("🔴 CRITICAL", f"Model is {age_days} days old (very stale)"))
    elif age_days > 60:
        issues.append(("🟡 WARNING", f"Model is {age_days} days old (getting old)"))
    else:
        print(f"✅ Model age is acceptable ({age_days} days)")
    
    # Check training samples
    train_rows = meta_12h.get('train_rows', 0)
    if train_rows < 500:
        issues.append(("🔴 CRITICAL", f"Very few training samples ({train_rows})"))
    elif train_rows < 1000:
        issues.append(("🟡 WARNING", f"Limited training samples ({train_rows})"))
    else:
        print(f"✅ Sufficient training samples ({train_rows:,})")
    
    # Check accuracy
    if train_acc < 0.50:
        issues.append(("🟡 WARNING", f"Low accuracy ({train_acc*100:.1f}%)"))
    else:
        print(f"✅ Acceptable accuracy ({train_acc*100:.1f}%)")
    
    print()
    
    if issues:
        print("Issues Found:")
        for severity, msg in issues:
            print(f"  {severity}: {msg}")
        print()
    
    # Verdict
    critical = sum(1 for s, _ in issues if "CRITICAL" in s)
    
    if critical >= 1:
        print("🔴 VERDICT: MODEL NEEDS RETRAINING")
        print()
        print("Reasons:")
        print(f"  - Only {train_rows} training samples (need 1000+)")
        print(f"  - Model is {age_days} days old")
        print()
        print("Recommendation: Retrain with more data")
    else:
        print("🟢 VERDICT: MODEL IS ACCEPTABLE")
        print()
        print("Model is functional but could be improved with retraining.")
    
else:
    print("❌ 12H DOES NOT HAVE ITS OWN MODEL")
    print()
    print("This means 12h timeframe is either:")
    print("  1. Not being used")
    print("  2. Using a shared model (from 5m or other timeframe)")
    print()
    print("Recommendation: Create dedicated 12h model if using this timeframe")

print()

# Compare with 5m model
print("=" * 80)
print("COMPARISON WITH 5M MODEL")
print("=" * 80)
print()

with open('live_demo/models/LATEST.json', 'r') as f:
    latest_5m = json.load(f)

with open(f"live_demo/models/{latest_5m['training_meta']}", 'r') as f:
    meta_5m = json.load(f)

print("5M Model:")
print(f"  Training Samples: {meta_5m.get('training_samples', 'N/A'):,}")
print(f"  Training Accuracy: {meta_5m.get('meta_score_in_sample', 0)*100:.2f}%")
print()

if has_12h_model:
    print("12H Model:")
    print(f"  Training Samples: {meta_12h.get('train_rows', 'N/A'):,}")
    print(f"  Training Accuracy: {meta_12h.get('meta_score_in_sample', 0)*100:.2f}%")
    print()
    
    print("Comparison:")
    if meta_12h.get('train_rows', 0) < meta_5m.get('training_samples', 0):
        print("  ⚠️ 12h has MUCH LESS training data than 5m")
        print(f"     ({meta_12h.get('train_rows', 0):,} vs {meta_5m.get('training_samples', 0):,})")

print()

# Retraining plan
print("=" * 80)
print("HOW TO RETRAIN 12H MODEL")
print("=" * 80)
print()

print("Option 1: Use Existing Data (if available)")
print("  1. Check if ohlc_btc_12h.csv exists")
print("  2. Use same training approach as 5m")
print("  3. Adapt retrain_5m_banditv3.py for 12h")
print()

print("Option 2: Fetch New Data")
print("  1. Fetch 12h OHLCV from Hyperliquid")
print("  2. Need ~6 months of data (minimum)")
print("  3. Train using proven BanditV3 approach")
print()

print("Expected Improvement:")
print("  - More training samples (target: 1000+)")
print("  - Better accuracy (target: 65%+)")
print("  - Fresh patterns from recent market")
print()

# Check for 12h data
print("Data Availability:")
if os.path.exists('ohlc_btc_12h.csv'):
    import pandas as pd
    df = pd.read_csv('ohlc_btc_12h.csv')
    print(f"  ✅ ohlc_btc_12h.csv exists ({len(df):,} rows)")
    print("     Can retrain immediately!")
else:
    print("  ❌ ohlc_btc_12h.csv NOT found")
    print("     Need to fetch 12h data first")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

if has_12h_model:
    print(f"✅ 12H has its own model ({age_days} days old)")
    print(f"⚠️ Only {train_rows} training samples (weak)")
    print(f"✅ Accuracy: {train_acc*100:.1f}%")
    print()
    print("🟡 RECOMMENDATION: Retrain with more data")
    print("   Priority: Medium (after 5m is stable)")
else:
    print("❌ 12H does NOT have its own model")
    print()
    print("🔴 RECOMMENDATION: Create 12h model")
    print("   Priority: High (if using 12h timeframe)")

print()
print("=" * 80)
