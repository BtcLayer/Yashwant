"""
Check what the RAW model output looks like
To determine if we need flip or not
"""

import pandas as pd

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

# The 's_model' column in signals.csv is AFTER any flipping
# We need to check the distribution to understand the model

print("="*80)
print("MODEL OUTPUT ANALYSIS")
print("="*80)

# Current distribution in signals.csv (this is AFTER flip_model was applied)
positive = (df['s_model'] > 0).sum()
negative = (df['s_model'] < 0).sum()
zero = (df['s_model'] == 0).sum()

print(f"\nCurrent s_model distribution (WITH flip_model=true):")
print(f"  Positive (>0): {positive} ({positive/len(df)*100:.1f}%)")
print(f"  Negative (<0): {negative} ({negative/len(df)*100:.1f}%)")
print(f"  Zero (=0): {zero}")

print(f"\nSample values:")
print(df['s_model'].describe())

print(f"\n" + "="*80)
print("INTERPRETATION:")
print("="*80)

print(f"\nWith flip_model=true, we saw:")
print(f"  - {positive} positive values (model predicted UP after flip)")
print(f"  - {negative} negative values (model predicted DOWN after flip)")

print(f"\nThis means the RAW model (before flip) was:")
print(f"  - Predicting DOWN {positive} times (got flipped to UP)")
print(f"  - Predicting UP {negative} times (got flipped to DOWN)")

print(f"\n🔍 CONCLUSION:")
if positive > negative * 2:
    print(f"  The RAW model is predicting DOWN most of the time")
    print(f"  flip_model=true was flipping these to UP")
    print(f"  Setting flip_model=false will give us SELL signals")
    print(f"\n  ✅ flip_model=false is CORRECT")
elif negative > positive * 2:
    print(f"  The RAW model is predicting UP most of the time")
    print(f"  flip_model=true was flipping these to DOWN")
    print(f"  Setting flip_model=false will give us BUY signals")
    print(f"\n  ⚠️  flip_model=false might cause only BUYs")
else:
    print(f"  The RAW model is balanced")
    print(f"  flip_model setting determines direction mapping")
    print(f"\n  Need to check which way is correct")

print("="*80)
