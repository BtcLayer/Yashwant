"""
Step 1: Investigate Raw Model Predictions
Check if the model is actually predicting both UP and DOWN
"""
import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("STEP 1: RAW MODEL PREDICTION ANALYSIS")
print("="*80)

# Load signals file
signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

print(f"\nTotal signals: {len(signals)}")
print(f"\nAvailable columns: {list(signals.columns)}")

# Check for prediction columns
pred_cols = [col for col in signals.columns if 'pred' in col.lower() or 'forecast' in col.lower()]
print(f"\nPrediction columns found: {pred_cols}")

# Analyze each prediction column
for col in pred_cols:
    if col in signals.columns:
        print(f"\n--- {col} ---")
        print(f"Mean: {signals[col].mean():.6f}")
        print(f"Std: {signals[col].std():.6f}")
        print(f"Min: {signals[col].min():.6f}")
        print(f"Max: {signals[col].max():.6f}")
        print(f"Positive: {(signals[col] > 0).sum()} ({(signals[col] > 0).sum()/len(signals)*100:.1f}%)")
        print(f"Negative: {(signals[col] < 0).sum()} ({(signals[col] < 0).sum()/len(signals)*100:.1f}%)")
        print(f"Zero: {(signals[col] == 0).sum()} ({(signals[col] == 0).sum()/len(signals)*100:.1f}%)")
        
        # Show distribution
        print(f"\nRecent 20 values:")
        print(signals[col].tail(20).values)

# Check S_top and S_bot (cohort signals)
if 'S_top' in signals.columns and 'S_bot' in signals.columns:
    print("\n" + "="*80)
    print("COHORT SIGNALS (S_top, S_bot)")
    print("="*80)
    
    print("\nS_top statistics:")
    print(f"Mean: {signals['S_top'].mean():.6f}")
    print(f"Non-zero: {(signals['S_top'] != 0).sum()} ({(signals['S_top'] != 0).sum()/len(signals)*100:.1f}%)")
    
    print("\nS_bot statistics:")
    print(f"Mean: {signals['S_bot'].mean():.6f}")
    print(f"Non-zero: {(signals['S_bot'] != 0).sum()} ({(signals['S_bot'] != 0).sum()/len(signals)*100:.1f}%)")
    
    print("\nRecent 10 cohort signals:")
    print(signals[['ts_iso', 'S_top', 'S_bot']].tail(10).to_string(index=False))

# Check ensemble predictions
if 'bandit_arm' in signals.columns:
    print("\n" + "="*80)
    print("BANDIT ARM SELECTION")
    print("="*80)
    print(signals['bandit_arm'].value_counts())

# Check IC (information coefficient)
if 'ic_200' in signals.columns:
    print("\n" + "="*80)
    print("INFORMATION COEFFICIENT (IC_200)")
    print("="*80)
    print(f"Mean IC: {signals['ic_200'].mean():.6f}")
    print(f"Recent IC values:")
    print(signals[['ts_iso', 'ic_200']].tail(10).to_string(index=False))

print("\n" + "="*80)
print("DIAGNOSIS:")
print("="*80)

# Check if predictions exist and are varying
has_predictions = False
for col in pred_cols:
    if col in signals.columns:
        std = signals[col].std()
        if std > 0.0001:
            has_predictions = True
            print(f"✓ {col} has varying predictions (std={std:.6f})")
        else:
            print(f"✗ {col} has constant/near-zero predictions (std={std:.6f})")

if not has_predictions:
    print("\n⚠️ WARNING: No varying predictions found! Model may not be working.")
else:
    print("\n✓ Model is generating predictions")

print("="*80)
