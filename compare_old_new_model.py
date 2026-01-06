"""
Compare OLD MODEL (before retraining) vs NEW MODEL (after retraining)
"""
import pandas as pd
from pathlib import Path

print("="*80)
print("OLD MODEL vs NEW MODEL COMPARISON")
print("="*80)

# Load archived (old model) data
old_exec = Path("paper_trading_outputs/5m/sheets_fallback/executions_paper_ARCHIVED_MODEL_V1.csv")
new_exec = Path("paper_trading_outputs/5m/sheets_fallback/executions_paper.csv")

print("\n--- OLD MODEL (Before Retraining on Jan 5, 16:01) ---")
if old_exec.exists():
    df_old = pd.read_csv(old_exec)
    print(f"Total trades: {len(df_old)}")
    
    if len(df_old) > 0:
        side_counts = df_old['side'].value_counts()
        for side, count in side_counts.items():
            print(f"  {side}: {count} ({count/len(df_old)*100:.1f}%)")
        
        total_pnl = df_old['realized_pnl'].sum()
        win_rate = (df_old['realized_pnl'] > 0).sum() / len(df_old) * 100
        
        print(f"\nPerformance:")
        print(f"  Total PnL: ${total_pnl:.2f}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Avg PnL per trade: ${total_pnl/len(df_old):.2f}")
else:
    print("  File not found")

print("\n--- NEW MODEL (After Retraining on Jan 5, 16:01) ---")
if new_exec.exists():
    df_new = pd.read_csv(new_exec)
    print(f"Total trades: {len(df_new)}")
    
    if len(df_new) > 0:
        side_counts = df_new['side'].value_counts()
        for side, count in side_counts.items():
            print(f"  {side}: {count} ({count/len(df_new)*100:.1f}%)")
        
        total_pnl = df_new['realized_pnl'].sum()
        win_rate = (df_new['realized_pnl'] > 0).sum() / len(df_new) * 100
        
        print(f"\nPerformance:")
        print(f"  Total PnL: ${total_pnl:.2f}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Avg PnL per trade: ${total_pnl/len(df_new):.2f}")

# Check if there's a signals archive
print("\n" + "="*80)
print("CHECKING SIGNAL ARCHIVES")
print("="*80)

signals_dir = Path("paper_trading_outputs/5m/sheets_fallback")
signal_files = list(signals_dir.glob("signals*.csv"))

print(f"\nFound {len(signal_files)} signal files:")
for f in signal_files:
    print(f"  {f.name}")

# Load current signals and check when they started
signals = pd.read_csv("paper_trading_outputs/5m/sheets_fallback/signals.csv")
signals['datetime'] = pd.to_datetime(signals['ts_iso'].str.split('.').str[0])

print(f"\nCurrent signals file:")
print(f"  First signal: {signals['datetime'].min()}")
print(f"  Last signal: {signals['datetime'].max()}")
print(f"  Total: {len(signals)}")

# Check signals around the retraining time (Jan 5, 16:01)
retrain_time = pd.to_datetime('2026-01-05 16:01')
before_retrain = signals[signals['datetime'] < retrain_time]
after_retrain = signals[signals['datetime'] >= retrain_time]

if len(before_retrain) > 0:
    print(f"\n--- BEFORE RETRAINING (before Jan 5, 16:01) ---")
    print(f"  Signals: {len(before_retrain)}")
    print(f"  Neutral: {(before_retrain['dir']==0).sum()} ({(before_retrain['dir']==0).sum()/len(before_retrain)*100:.1f}%)")
    print(f"  Mean confidence: {before_retrain[['p_up', 'p_down']].max(axis=1).mean():.3f}")
    print(f"  Mean p_neutral: {before_retrain['p_neutral'].mean():.3f}")

if len(after_retrain) > 0:
    print(f"\n--- AFTER RETRAINING (after Jan 5, 16:01) ---")
    print(f"  Signals: {len(after_retrain)}")
    print(f"  Neutral: {(after_retrain['dir']==0).sum()} ({(after_retrain['dir']==0).sum()/len(after_retrain)*100:.1f}%)")
    print(f"  Mean confidence: {after_retrain[['p_up', 'p_down']].max(axis=1).mean():.3f}")
    print(f"  Mean p_neutral: {after_retrain['p_neutral'].mean():.3f}")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if len(before_retrain) > 0 and len(after_retrain) > 0:
    neutral_before = (before_retrain['dir']==0).sum()/len(before_retrain)*100
    neutral_after = (after_retrain['dir']==0).sum()/len(after_retrain)*100
    conf_before = before_retrain[['p_up', 'p_down']].max(axis=1).mean()
    conf_after = after_retrain[['p_up', 'p_down']].max(axis=1).mean()
    
    print(f"\nNeutral rate change: {neutral_before:.1f}% -> {neutral_after:.1f}% ({neutral_after-neutral_before:+.1f}%)")
    print(f"Confidence change: {conf_before:.3f} -> {conf_after:.3f} ({conf_after-conf_before:+.3f})")
    
    if neutral_after > neutral_before + 10:
        print("\n*** NEW MODEL IS WORSE - More neutral predictions! ***")
    if conf_after > conf_before + 0.05:
        print("*** NEW MODEL has HIGHER confidence (good) ***")
    elif conf_after < conf_before - 0.05:
        print("*** NEW MODEL has LOWER confidence (bad) ***")

print("\n" + "="*80)
