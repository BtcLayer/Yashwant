import pandas as pd
import numpy as np

# Load signals
df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

print("=" * 80)
print("SIGNALS ANALYSIS")
print("=" * 80)

print(f"\nTotal signals: {len(df)}")
print(f"\nColumns: {list(df.columns)}")

# Check for direction/prediction columns
if 'dir' in df.columns:
    print(f"\n=== DIRECTION DISTRIBUTION ===")
    print(df['dir'].value_counts())
    
    recent = df.tail(50)
    print(f"\n=== RECENT 50 SIGNALS ===")
    print(recent['dir'].value_counts())
    
    # Check if there are any SELL signals
    sell_count = (df['dir'] == 'SELL').sum()
    buy_count = (df['dir'] == 'BUY').sum()
    neutral_count = (df['dir'] == 'NEUTRAL').sum()
    
    print(f"\n=== OVERALL STATS ===")
    print(f"BUY signals:     {buy_count} ({buy_count/len(df)*100:.1f}%)")
    print(f"SELL signals:    {sell_count} ({sell_count/len(df)*100:.1f}%)")
    print(f"NEUTRAL signals: {neutral_count} ({neutral_count/len(df)*100:.1f}%)")

# Check alpha values
if 'alpha' in df.columns:
    print(f"\n=== ALPHA STATISTICS ===")
    print(f"Mean alpha: {df['alpha'].mean():.6f}")
    print(f"Mean alpha (bps): {df['alpha'].mean() * 10000:.2f}")
    print(f"Positive alpha count: {(df['alpha'] > 0).sum()}")
    print(f"Negative alpha count: {(df['alpha'] < 0).sum()}")

# Check confidence
if 'conf' in df.columns:
    print(f"\n=== CONFIDENCE STATISTICS ===")
    print(f"Mean confidence: {df['conf'].mean():.4f}")
    print(f"Above 0.60: {(df['conf'] > 0.60).sum()}")

# Show last 10 signals
print(f"\n=== LAST 10 SIGNALS ===")
cols_to_show = ['ts_iso', 'dir', 'alpha', 'conf'] if 'conf' in df.columns else ['ts_iso', 'dir', 'alpha']
if all(c in df.columns for c in cols_to_show):
    print(df[cols_to_show].tail(10).to_string())
else:
    print("Some columns missing")
    print(df[['ts_iso', 'dir', 'alpha']].tail(10).to_string())
