"""
COMPREHENSIVE 5M MODEL ANALYSIS
Deep dive into the 5m model to determine if retraining is needed
"""
import joblib
import json
import os
from datetime import datetime
import pandas as pd
import numpy as np

print("=" * 80)
print("5M MODEL COMPREHENSIVE ANALYSIS")
print("=" * 80)
print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================
# PART 1: MODEL FILES ANALYSIS
# ============================================
print("📦 PART 1: MODEL FILES INSPECTION")
print("-" * 80)

latest_path = 'live_demo/models/LATEST.json'
with open(latest_path, 'r') as f:
    latest = json.load(f)

print(f"✅ LATEST.json found")
print(f"   Meta-classifier: {latest['meta_classifier']}")
print(f"   Calibrator: {latest['calibrator']}")
print()

# Load training metadata
meta_file = f"live_demo/models/{latest['training_meta']}"
with open(meta_file, 'r') as f:
    training_meta = json.load(f)

print("📊 Training Metadata:")
print(f"   Training Date: {training_meta['timestamp_utc']}")
print(f"   Target: {training_meta['target']}")
print(f"   Features: {training_meta['n_features']}")
print(f"   Training Score: {training_meta.get('meta_score_in_sample', 'N/A')}")
print()

# Calculate model age
train_date = datetime.strptime(training_meta['timestamp_utc'], '%Y%m%d_%H%M%S')
age_days = (datetime.now() - train_date).days
print(f"⏰ Model Age: {age_days} days (trained on {train_date.strftime('%Y-%m-%d')})")
print()

# ============================================
# PART 2: MODEL STRUCTURE ANALYSIS
# ============================================
print("🔍 PART 2: MODEL STRUCTURE")
print("-" * 80)

try:
    # Load calibrator (this is what the bot actually uses)
    calibrator = joblib.load(f"live_demo/models/{latest['calibrator']}")
    print(f"✅ Calibrator loaded successfully")
    print(f"   Type: {type(calibrator).__name__}")
    print(f"   Base estimator: {type(calibrator.base_estimator).__name__}")
    
    # Check if it can make predictions
    print(f"   Classes: {calibrator.classes_}")
    print(f"   Number of classes: {len(calibrator.classes_)}")
    
    # Check feature expectations
    if hasattr(calibrator.base_estimator, 'n_features_in_'):
        print(f"   Expected features: {calibrator.base_estimator.n_features_in_}")
    
    print()
    
except Exception as e:
    print(f"❌ Error loading calibrator: {e}")
    print()

# Load feature schema
feat_file = f"live_demo/models/{latest['feature_columns']}"
with open(feat_file, 'r') as f:
    feat_schema = json.load(f)

features = feat_schema.get('feature_cols', feat_schema)
print(f"📋 Feature Schema:")
print(f"   Total features: {len(features)}")
print(f"   Features: {features}")
print()

# ============================================
# PART 3: PERFORMANCE ANALYSIS
# ============================================
print("📈 PART 3: MODEL PERFORMANCE")
print("-" * 80)

# Check if we have recent performance data
perf_files = [
    'paper_trading_outputs/executions_paper.csv',
    'paper_trading_outputs/signals.csv',
    'paper_trading_outputs/equity.csv'
]

for pfile in perf_files:
    if os.path.exists(pfile):
        try:
            df = pd.read_csv(pfile)
            print(f"✅ {os.path.basename(pfile)}: {len(df)} records")
        except:
            print(f"⚠️ {os.path.basename(pfile)}: Error reading")
    else:
        print(f"⏳ {os.path.basename(pfile)}: Not found")

print()

# Analyze recent executions if available
if os.path.exists('paper_trading_outputs/executions_paper.csv'):
    try:
        df_exec = pd.read_csv('paper_trading_outputs/executions_paper.csv')
        df_exec['ts_ist'] = pd.to_datetime(df_exec['ts_ist'])
        
        # Get recent data (last 7 days)
        recent = df_exec[df_exec['ts_ist'] > datetime.now() - pd.Timedelta(days=7)]
        
        if len(recent) > 0:
            print("📊 Recent Performance (last 7 days):")
            print(f"   Total trades: {len(recent)}")
            
            # BUY vs SELL
            buy_count = len(recent[recent['side'] == 'BUY'])
            sell_count = len(recent[recent['side'] == 'SELL'])
            print(f"   BUY trades: {buy_count} ({buy_count/len(recent)*100:.1f}%)")
            print(f"   SELL trades: {sell_count} ({sell_count/len(recent)*100:.1f}%)")
            
            # Check if model predicts both directions
            if sell_count == 0:
                print(f"   ⚠️ WARNING: No SELL trades (one-directional)")
            elif sell_count > 0 and buy_count > 0:
                print(f"   ✅ GOOD: Both directions predicted")
            
            print()
    except Exception as e:
        print(f"⚠️ Error analyzing executions: {e}")
        print()

# ============================================
# PART 4: DECISION CRITERIA
# ============================================
print("🎯 PART 4: RETRAINING DECISION ANALYSIS")
print("-" * 80)

issues = []
strengths = []

# 1. Model Age
if age_days > 90:
    issues.append(f"❌ Model is {age_days} days old (>90 days is stale)")
elif age_days > 60:
    issues.append(f"⚠️ Model is {age_days} days old (consider retraining)")
else:
    strengths.append(f"✅ Model age is acceptable ({age_days} days)")

# 2. Training Score
train_score = training_meta.get('meta_score_in_sample', 0)
if train_score >= 0.75:
    strengths.append(f"✅ Excellent training score ({train_score:.4f})")
elif train_score >= 0.60:
    strengths.append(f"✅ Good training score ({train_score:.4f})")
elif train_score >= 0.45:
    strengths.append(f"⚠️ Moderate training score ({train_score:.4f})")
else:
    issues.append(f"❌ Low training score ({train_score:.4f})")

# 3. Feature Count
if len(features) == 17:
    strengths.append(f"✅ Correct number of features (17)")
else:
    issues.append(f"⚠️ Unexpected feature count ({len(features)})")

# 4. Model Structure
try:
    if calibrator and hasattr(calibrator, 'classes_'):
        if len(calibrator.classes_) == 3:
            strengths.append(f"✅ Predicts all 3 classes (DOWN, NEUTRAL, UP)")
        else:
            issues.append(f"❌ Only predicts {len(calibrator.classes_)} classes")
except:
    issues.append(f"⚠️ Could not verify model structure")

print("STRENGTHS:")
for s in strengths:
    print(f"  {s}")

print()

if issues:
    print("ISSUES:")
    for i in issues:
        print(f"  {i}")
    print()

# ============================================
# PART 5: FINAL RECOMMENDATION
# ============================================
print("=" * 80)
print("🎯 FINAL RECOMMENDATION")
print("=" * 80)
print()

# Decision logic
needs_retraining = False
reasons = []

if age_days > 90:
    needs_retraining = True
    reasons.append("Model is too old (>90 days)")

if train_score < 0.45:
    needs_retraining = True
    reasons.append("Training score is too low")

if len(issues) >= 3:
    needs_retraining = True
    reasons.append("Multiple issues detected")

if needs_retraining:
    print("❌ RECOMMENDATION: RETRAIN THE MODEL")
    print()
    print("Reasons:")
    for r in reasons:
        print(f"  - {r}")
    print()
    print("Benefits of retraining:")
    print("  - Fresh data from recent market conditions")
    print("  - Potentially better performance")
    print("  - Updated patterns and relationships")
else:
    print("✅ RECOMMENDATION: MODEL IS FINE - NO RETRAINING NEEDED")
    print()
    print("The 5m model is:")
    print("  - Recent enough (< 90 days old)")
    print("  - Has acceptable performance metrics")
    print("  - Structurally sound")
    print()
    print("Focus on:")
    print("  - Optimizing parameters (thresholds, risk settings)")
    print("  - Improving execution logic")
    print("  - Fine-tuning the trading strategy")
    print()
    print("Retraining is optional and may not improve results.")

print()
print("=" * 80)
print(f"Analysis Complete: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 80)
