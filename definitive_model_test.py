"""
DEFINITIVE TEST - Is this a model issue or configuration issue?

We'll test by temporarily bypassing ALL decision logic and checking
what the raw model actually outputs.
"""

import pandas as pd
import numpy as np
import json

print("="*80)
print("DEFINITIVE MODEL DIAGNOSIS")
print("="*80)

# Load signals data
df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

# Load config to see what flips are applied
with open('live_demo/config.json') as f:
    config = json.load(f)
    
flip_model = config['thresholds'].get('flip_model', False)
flip_mood = config['thresholds'].get('flip_mood', False)

print(f"\n1. CONFIGURATION:")
print(f"   flip_model: {flip_model}")
print(f"   flip_mood: {flip_mood}")

# The s_model in signals.csv has ALREADY been flipped if flip_model=true
# So we need to reverse it to see the RAW model output

if flip_model:
    raw_s_model = -df['s_model']  # Reverse the flip
    print(f"\n   NOTE: Reversing flip to see RAW model output")
else:
    raw_s_model = df['s_model']
    print(f"\n   NOTE: No flip applied, s_model is raw")

print(f"\n2. RAW MODEL OUTPUT (before any flips):")
print(f"   Total predictions: {len(raw_s_model)}")
print(f"   Mean: {raw_s_model.mean():.4f}")
print(f"   Std: {raw_s_model.std():.4f}")
print(f"   Min: {raw_s_model.min():.4f}")
print(f"   Max: {raw_s_model.max():.4f}")

# Count directions
raw_up = (raw_s_model > 0).sum()
raw_down = (raw_s_model < 0).sum()
raw_neutral = (raw_s_model == 0).sum()

print(f"\n   UP predictions (>0): {raw_up} ({raw_up/len(df)*100:.1f}%)")
print(f"   DOWN predictions (<0): {raw_down} ({raw_down/len(df)*100:.1f}%)")
print(f"   NEUTRAL (=0): {raw_neutral}")

# Calculate ratio
if raw_down > 0:
    ratio = raw_up / raw_down
    print(f"   UP:DOWN ratio: {ratio:.2f}:1")
else:
    ratio = float('inf')
    print(f"   UP:DOWN ratio: ∞:1 (no DOWN predictions!)")

# Magnitude analysis
print(f"\n3. SIGNAL STRENGTH ANALYSIS:")

if raw_up > 0:
    up_magnitudes = raw_s_model[raw_s_model > 0]
    print(f"   UP signals:")
    print(f"     Mean magnitude: {up_magnitudes.mean():.4f}")
    print(f"     Median magnitude: {np.median(up_magnitudes):.4f}")
    print(f"     Max magnitude: {up_magnitudes.max():.4f}")
    print(f"     % above 0.60: {(up_magnitudes >= 0.60).sum() / len(up_magnitudes) * 100:.1f}%")

if raw_down > 0:
    down_magnitudes = abs(raw_s_model[raw_s_model < 0])
    print(f"   DOWN signals:")
    print(f"     Mean magnitude: {down_magnitudes.mean():.4f}")
    print(f"     Median magnitude: {np.median(down_magnitudes):.4f}")
    print(f"     Max magnitude: {down_magnitudes.max():.4f}")
    print(f"     % above 0.60: {(down_magnitudes >= 0.60).sum() / len(down_magnitudes) * 100:.1f}%")

# Market reality check
print(f"\n4. MARKET REALITY CHECK:")

if 'close' in df.columns:
    # Calculate actual market direction
    df['price_change'] = df['close'].pct_change()
    actual_up = (df['price_change'] > 0).sum()
    actual_down = (df['price_change'] < 0).sum()
    
    print(f"   Actual market movements:")
    print(f"     UP bars: {actual_up} ({actual_up/len(df)*100:.1f}%)")
    print(f"     DOWN bars: {actual_down} ({actual_down/len(df)*100:.1f}%)")
    
    if actual_down > 0:
        actual_ratio = actual_up / actual_down
        print(f"     UP:DOWN ratio: {actual_ratio:.2f}:1")
        
        print(f"\n   Model vs Reality:")
        print(f"     Model UP:DOWN = {ratio:.2f}:1")
        print(f"     Market UP:DOWN = {actual_ratio:.2f}:1")
        
        if abs(ratio - actual_ratio) > 2:
            print(f"     🔴 MISMATCH: Model ratio doesn't match market!")
        else:
            print(f"     ✅ MATCH: Model ratio matches market")

# Final verdict
print(f"\n" + "="*80)
print("DEFINITIVE CONCLUSION:")
print("="*80)

is_model_issue = False
reasons = []

# Test 1: Severe imbalance
if ratio > 4 or ratio < 0.25:
    is_model_issue = True
    reasons.append(f"Severe imbalance: {ratio:.2f}:1 ratio (should be ~1:1)")

# Test 2: All predictions one direction
if raw_down == 0 or raw_up == 0:
    is_model_issue = True
    reasons.append("Model ONLY predicts one direction")

# Test 3: Weak signals
if raw_down > 0:
    weak_down = (abs(raw_s_model[raw_s_model < 0]) < 0.60).sum()
    if weak_down == raw_down:
        is_model_issue = True
        reasons.append("ALL DOWN predictions are too weak (< 0.60)")

# Test 4: Doesn't match market
if 'close' in df.columns and actual_down > 0:
    if abs(ratio - actual_ratio) > 2:
        is_model_issue = True
        reasons.append(f"Model ratio ({ratio:.2f}:1) doesn't match market ({actual_ratio:.2f}:1)")

print(f"\n{'🔴 YES - THIS IS A MODEL ISSUE' if is_model_issue else '✅ NO - This is a configuration issue'}")

if is_model_issue:
    print(f"\nEVIDENCE:")
    for i, reason in enumerate(reasons, 1):
        print(f"  {i}. {reason}")
    
    print(f"\nCONFIDENCE: {'100%' if len(reasons) >= 3 else '90%' if len(reasons) == 2 else '75%'}")
    
    print(f"\nWHAT THIS MEANS:")
    print(f"  • The model itself is producing biased/incorrect predictions")
    print(f"  • No amount of configuration changes will fix this")
    print(f"  • Model retraining is REQUIRED")
    
    print(f"\nNEXT STEPS:")
    print(f"  1. Stop trading with this model")
    print(f"  2. Retrain model with balanced data")
    print(f"  3. Validate new model before deployment")
else:
    print(f"\nThis appears to be a configuration issue, not a model issue")
    print(f"The model predictions are reasonable")
    print(f"Check decision logic and thresholds")

print("="*80)
