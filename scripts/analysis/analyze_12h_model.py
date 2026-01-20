"""
COMPREHENSIVE 12H MODEL ANALYSIS
Check model existence, performance, training quality, and improvement plan
"""
import json
import os
from datetime import datetime
import joblib
import pandas as pd

print("=" * 80)
print("12H TIMEFRAME MODEL - COMPREHENSIVE ANALYSIS")
print("=" * 80)
print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================
# PART 1: CHECK IF 12H HAS ITS OWN MODEL
# ============================================
print("📦 PART 1: MODEL EXISTENCE CHECK")
print("-" * 80)

# Check if 12h directory exists
if os.path.exists('live_demo_12h'):
    print("✅ 12h directory exists: live_demo_12h/")
    
    # Check for models directory
    if os.path.exists('live_demo_12h/models'):
        print("✅ Models directory exists: live_demo_12h/models/")
        
        # Check for LATEST.json
        if os.path.exists('live_demo_12h/models/LATEST.json'):
            print("✅ LATEST.json found")
            
            with open('live_demo_12h/models/LATEST.json', 'r') as f:
                latest_12h = json.load(f)
            
            print()
            print("12H Model Files:")
            for key, filename in latest_12h.items():
                filepath = f"live_demo_12h/models/{filename}"
                exists = "✅" if os.path.exists(filepath) else "❌"
                if os.path.exists(filepath):
                    size_kb = os.path.getsize(filepath) / 1024
                    print(f"   {exists} {key}: {filename} ({size_kb:.1f} KB)")
                else:
                    print(f"   {exists} {key}: {filename} (MISSING)")
            
            has_own_model = True
        else:
            print("❌ LATEST.json NOT found in live_demo_12h/models/")
            has_own_model = False
    else:
        print("❌ Models directory NOT found")
        has_own_model = False
else:
    print("❌ 12h directory NOT found")
    has_own_model = False

print()

# ============================================
# PART 2: MODEL METADATA ANALYSIS
# ============================================
if has_own_model:
    print("📊 PART 2: 12H MODEL METADATA")
    print("-" * 80)
    
    try:
        meta_file = f"live_demo_12h/models/{latest_12h['training_meta']}"
        with open(meta_file, 'r') as f:
            meta_12h = json.load(f)
        
        print("Training Information:")
        print(f"   Training Date: {meta_12h['timestamp_utc']}")
        
        train_date = datetime.strptime(meta_12h['timestamp_utc'], '%Y%m%d_%H%M%S')
        age_days = (datetime.now() - train_date).days
        print(f"   Model Age: {age_days} days")
        
        print(f"   Target: {meta_12h.get('target', 'N/A')}")
        print(f"   Features: {meta_12h.get('n_features', 'N/A')}")
        print()
        
        print("Performance Metrics:")
        train_acc = meta_12h.get('meta_score_in_sample', 0)
        print(f"   Training Accuracy: {train_acc:.4f} ({train_acc*100:.2f}%)")
        
        if 'calibrated_score' in meta_12h:
            cal_acc = meta_12h['calibrated_score']
            print(f"   Calibrated Accuracy: {cal_acc:.4f} ({cal_acc*100:.2f}%)")
        
        print()
        
        print("Training Data:")
        if 'training_samples' in meta_12h:
            print(f"   Training Samples: {meta_12h['training_samples']:,}")
        if 'test_samples' in meta_12h:
            print(f"   Test Samples: {meta_12h['test_samples']:,}")
        
        if 'data_start' in meta_12h and 'data_end' in meta_12h:
            print(f"   Data Period: {meta_12h['data_start']} to {meta_12h['data_end']}")
        
        print()
        
        # Base model scores
        if 'cv_scores' in meta_12h:
            print("Base Model Scores:")
            for model_name, score in meta_12h['cv_scores'].items():
                print(f"   {model_name:20s}: {score:.4f} ({score*100:.2f}%)")
        
        print()
        
    except Exception as e:
        print(f"⚠️ Error reading metadata: {e}")
        print()

# ============================================
# PART 3: COMPARE WITH OTHER TIMEFRAMES
# ============================================
print("🔄 PART 3: COMPARISON WITH OTHER TIMEFRAMES")
print("-" * 80)

timeframes = {
    '5m': 'live_demo/models/LATEST.json',
    '1h': 'live_demo_1h/models/LATEST.json',
    '12h': 'live_demo_12h/models/LATEST.json',
    '24h': 'live_demo_24h/models/LATEST.json'
}

comparison = []

for tf, latest_path in timeframes.items():
    if os.path.exists(latest_path):
        with open(latest_path, 'r') as f:
            latest = json.load(f)
        
        meta_path = latest_path.replace('LATEST.json', latest['training_meta'])
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            train_date = datetime.strptime(meta['timestamp_utc'], '%Y%m%d_%H%M%S')
            age_days = (datetime.now() - train_date).days
            
            comparison.append({
                'timeframe': tf,
                'has_model': True,
                'age_days': age_days,
                'accuracy': meta.get('meta_score_in_sample', 0),
                'samples': meta.get('training_samples', 0),
                'features': meta.get('n_features', 0)
            })
        else:
            comparison.append({
                'timeframe': tf,
                'has_model': True,
                'age_days': 'N/A',
                'accuracy': 'N/A',
                'samples': 'N/A',
                'features': 'N/A'
            })
    else:
        comparison.append({
            'timeframe': tf,
            'has_model': False,
            'age_days': 'N/A',
            'accuracy': 'N/A',
            'samples': 'N/A',
            'features': 'N/A'
        })

print("Timeframe Comparison:")
print()
print(f"{'TF':>4s} | {'Model':>6s} | {'Age (days)':>11s} | {'Accuracy':>10s} | {'Samples':>10s} | {'Features':>8s}")
print("-" * 70)

for item in comparison:
    tf = item['timeframe']
    has = "✅ Yes" if item['has_model'] else "❌ No"
    age = str(item['age_days']) if item['age_days'] != 'N/A' else 'N/A'
    acc = f"{item['accuracy']*100:.2f}%" if isinstance(item['accuracy'], float) else 'N/A'
    samp = f"{item['samples']:,}" if isinstance(item['samples'], int) else 'N/A'
    feat = str(item['features']) if item['features'] != 'N/A' else 'N/A'
    
    print(f"{tf:>4s} | {has:>6s} | {age:>11s} | {acc:>10s} | {samp:>10s} | {feat:>8s}")

print()

# ============================================
# PART 4: 12H MODEL QUALITY ASSESSMENT
# ============================================
if has_own_model:
    print("=" * 80)
    print("🎯 PART 4: 12H MODEL QUALITY ASSESSMENT")
    print("=" * 80)
    print()
    
    issues = []
    strengths = []
    
    # Check age
    if age_days > 90:
        issues.append(f"❌ Model is very old ({age_days} days)")
    elif age_days > 60:
        issues.append(f"⚠️ Model is getting old ({age_days} days)")
    else:
        strengths.append(f"✅ Model age is acceptable ({age_days} days)")
    
    # Check accuracy
    if train_acc < 0.45:
        issues.append(f"❌ Low training accuracy ({train_acc*100:.1f}%)")
    elif train_acc < 0.60:
        issues.append(f"⚠️ Moderate training accuracy ({train_acc*100:.1f}%)")
    else:
        strengths.append(f"✅ Good training accuracy ({train_acc*100:.1f}%)")
    
    # Check training samples
    if 'training_samples' in meta_12h:
        samples = meta_12h['training_samples']
        if samples < 1000:
            issues.append(f"❌ Very few training samples ({samples:,})")
        elif samples < 5000:
            issues.append(f"⚠️ Limited training samples ({samples:,})")
        else:
            strengths.append(f"✅ Sufficient training samples ({samples:,})")
    
    # Check features
    if meta_12h.get('n_features', 0) != 17:
        issues.append(f"⚠️ Feature count mismatch (expected 17, got {meta_12h.get('n_features', 0)})")
    else:
        strengths.append(f"✅ Correct feature count (17)")
    
    print("Strengths:")
    for s in strengths:
        print(f"  {s}")
    
    print()
    
    print("Issues:")
    for i in issues:
        print(f"  {i}")
    
    print()
    
    # Overall verdict
    critical_issues = sum(1 for i in issues if i.startswith("❌"))
    warnings = sum(1 for i in issues if i.startswith("⚠️"))
    
    print("Overall Assessment:")
    if critical_issues >= 2:
        print("  🔴 POOR: Model needs retraining urgently")
        needs_retraining = True
    elif critical_issues == 1 or warnings >= 2:
        print("  🟡 FAIR: Model should be retrained soon")
        needs_retraining = True
    else:
        print("  🟢 GOOD: Model is acceptable")
        needs_retraining = False

# ============================================
# PART 5: RETRAINING RECOMMENDATION
# ============================================
print()
print("=" * 80)
print("📋 PART 5: RETRAINING RECOMMENDATION FOR 12H")
print("=" * 80)
print()

if not has_own_model:
    print("🔴 CRITICAL: 12H DOES NOT HAVE ITS OWN MODEL")
    print()
    print("Action Required:")
    print("  1. Create 12h model from scratch")
    print("  2. Fetch 12h OHLCV data")
    print("  3. Train using same approach as 5m")
    print()
    
elif needs_retraining:
    print("🟡 RECOMMENDED: RETRAIN 12H MODEL")
    print()
    print("Reasons:")
    for i in issues:
        print(f"  {i}")
    print()
    
    print("How to Retrain:")
    print("  1. Check if ohlc_btc_12h.csv exists")
    print("  2. If not, fetch 12h data from Hyperliquid")
    print("  3. Use same training script as 5m (adapt for 12h)")
    print("  4. Expected improvement: Better accuracy, more samples")
    print()
    
else:
    print("✅ OPTIONAL: 12H MODEL IS ACCEPTABLE")
    print()
    print("Current model is functional.")
    print("Retraining would still help but not urgent.")
    print()

# ============================================
# PART 6: DATA AVAILABILITY CHECK
# ============================================
print("📁 PART 6: DATA AVAILABILITY FOR 12H RETRAINING")
print("-" * 80)

data_files = [
    'ohlc_btc_12h.csv',
    'historical_trades_btc.csv',
    'funding_btc.csv',
    'top_cohort.csv',
    'bottom_cohort.csv'
]

print("Checking for training data files:")
print()

data_available = True
for filename in data_files:
    if os.path.exists(filename):
        size_mb = os.path.getsize(filename) / (1024 * 1024)
        print(f"  ✅ {filename:30s} ({size_mb:.2f} MB)")
    else:
        print(f"  ❌ {filename:30s} (NOT FOUND)")
        if filename == 'ohlc_btc_12h.csv':
            data_available = False

print()

if data_available:
    print("✅ Primary data file (ohlc_btc_12h.csv) is available!")
    print("   Can proceed with retraining immediately.")
else:
    print("❌ Primary data file (ohlc_btc_12h.csv) is MISSING")
    print("   Need to fetch 12h data before retraining.")
    print()
    print("How to get 12h data:")
    print("  1. Fetch from Hyperliquid API (12h timeframe)")
    print("  2. Or resample 5m data to 12h (if sufficient)")

print()

# ============================================
# SUMMARY
# ============================================
print("=" * 80)
print("📊 SUMMARY - 12H MODEL STATUS")
print("=" * 80)
print()

if has_own_model:
    print(f"✅ 12H has its own model")
    print(f"   Age: {age_days} days")
    print(f"   Accuracy: {train_acc*100:.2f}%")
    print(f"   Training Samples: {meta_12h.get('training_samples', 'N/A'):,}" if 'training_samples' in meta_12h else "   Training Samples: N/A")
    print()
    
    if needs_retraining:
        print("🟡 RECOMMENDATION: Retrain 12h model")
        print()
        print("Priority: Medium")
        print("Reason: Model has issues that retraining would fix")
        print("Timeline: Can do after 5m model is stable")
    else:
        print("✅ RECOMMENDATION: 12h model is acceptable")
        print()
        print("Priority: Low")
        print("Reason: Model is functional")
        print("Timeline: Retrain when convenient")
else:
    print("❌ 12H does NOT have its own model")
    print()
    print("🔴 RECOMMENDATION: Create 12h model")
    print()
    print("Priority: High (if using 12h timeframe)")
    print("Reason: No dedicated model exists")
    print("Timeline: After 5m model is proven successful")

print()
print("=" * 80)
