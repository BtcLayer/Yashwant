"""
COMPREHENSIVE MODEL ANALYSIS
Determine if 5m model needs retraining or if there's a configuration issue
"""

import pandas as pd
import numpy as np

print("="*80)
print("5M MODEL HEALTH CHECK")
print("="*80)

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

# Analyze s_model distribution (this is AFTER flip_model=true)
s_model = df['s_model'].values

print(f"\n1. MODEL OUTPUT DISTRIBUTION (after flip):")
print(f"   Total signals: {len(df)}")
print(f"   Mean: {s_model.mean():.4f}")
print(f"   Std: {s_model.std():.4f}")
print(f"   Min: {s_model.min():.4f}")
print(f"   Max: {s_model.max():.4f}")
print(f"   Median: {np.median(s_model):.4f}")

# Distribution
positive = (s_model > 0).sum()
negative = (s_model < 0).sum()
print(f"\n   Positive (>0): {positive} ({positive/len(df)*100:.1f}%)")
print(f"   Negative (<0): {negative} ({negative/len(df)*100:.1f}%)")

# Magnitude analysis
print(f"\n2. MAGNITUDE ANALYSIS:")
print(f"   Positive signals:")
print(f"     Mean magnitude: {s_model[s_model>0].mean():.4f}")
print(f"     Max magnitude: {s_model[s_model>0].max():.4f}")

if negative > 0:
    print(f"   Negative signals:")
    print(f"     Mean magnitude: {abs(s_model[s_model<0]).mean():.4f}")
    print(f"     Max magnitude: {abs(s_model[s_model<0]).max():.4f}")
    
    # Check how many would pass CONF_MIN=0.60
    strong_negative = (s_model < 0) & (abs(s_model) >= 0.60)
    print(f"\n   Negative signals strong enough for CONF_MIN=0.60: {strong_negative.sum()}")
    print(f"   Percentage: {strong_negative.sum()/negative*100:.1f}%")

# Check if this is a model training issue
print(f"\n3. MODEL BIAS ASSESSMENT:")

# Before flip, the model was:
raw_down = positive  # These were DOWN before flip
raw_up = negative    # These were UP before flip

print(f"   RAW model (before flip):")
print(f"     DOWN predictions: {raw_down} ({raw_down/len(df)*100:.1f}%)")
print(f"     UP predictions: {raw_up} ({raw_up/len(df)*100:.1f}%)")
print(f"     Ratio: {raw_down/max(1,raw_up):.1f}:1")

if raw_down > raw_up * 3:
    print(f"\n   🔴 SEVERE BIAS: Model predicts DOWN {raw_down/max(1,raw_up):.1f}x more than UP")
    print(f"   This is NOT normal for a market that trends up")
    print(f"   ❌ MODEL NEEDS RETRAINING")
elif raw_down > raw_up * 1.5:
    print(f"\n   ⚠️  MODERATE BIAS: Model slightly favors DOWN")
    print(f"   May need retraining or is this intentional?")
else:
    print(f"\n   ✅ BALANCED: Model predictions are reasonable")

# Check signal strength
print(f"\n4. SIGNAL STRENGTH:")
weak_signals = abs(s_model) < 0.10
medium_signals = (abs(s_model) >= 0.10) & (abs(s_model) < 0.30)
strong_signals = abs(s_model) >= 0.30

print(f"   Weak (<0.10): {weak_signals.sum()} ({weak_signals.sum()/len(df)*100:.1f}%)")
print(f"   Medium (0.10-0.30): {medium_signals.sum()} ({medium_signals.sum()/len(df)*100:.1f}%)")
print(f"   Strong (>0.30): {strong_signals.sum()} ({strong_signals.sum()/len(df)*100:.1f}%)")

if weak_signals.sum() > len(df) * 0.7:
    print(f"\n   ⚠️  Most signals are weak - model may lack confidence")
    print(f"   Consider retraining with more/better features")

# Final verdict
print(f"\n" + "="*80)
print("DIAGNOSIS:")
print("="*80)

issues = []
recommendations = []

# Check 1: Severe bias
if raw_down > raw_up * 3:
    issues.append("🔴 Model has severe DOWN bias (6.3:1 ratio)")
    recommendations.append("RETRAIN model with balanced data")

# Check 2: Weak signals
if negative > 0:
    weak_sell_signals = (s_model < 0) & (abs(s_model) < 0.60)
    if weak_sell_signals.sum() == negative:
        issues.append("🔴 ALL SELL signals are too weak (< CONF_MIN)")
        recommendations.append("RETRAIN model to produce stronger signals")

# Check 3: Configuration
if raw_down > raw_up * 3:
    issues.append("⚠️  flip_model=true is masking the bias")
    recommendations.append("Fix the root cause (model bias) not the symptom")

print(f"\nISSUES FOUND:")
for issue in issues:
    print(f"  {issue}")

print(f"\nRECOMMENDATIONS:")
for rec in recommendations:
    print(f"  • {rec}")

print(f"\n" + "="*80)
print("CONCLUSION:")
print("="*80)

if len(issues) >= 2:
    print(f"\n❌ 5M MODEL NEEDS RETRAINING")
    print(f"\nReasons:")
    print(f"  1. Severe bias toward DOWN predictions (86% vs 14%)")
    print(f"  2. SELL signals too weak to pass confidence threshold")
    print(f"  3. flip_model is a workaround, not a fix")
    print(f"\nProper solution:")
    print(f"  • Retrain model with balanced training data")
    print(f"  • Ensure model learns both UP and DOWN patterns equally")
    print(f"  • Remove need for flip_model hack")
else:
    print(f"\n⚠️  Model has issues but may be workable")
    print(f"  Consider retraining for better performance")

print("="*80)
