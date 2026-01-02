"""
DIAGNOSTIC: Check signal distribution to identify why only BUY trades occur
"""

import pandas as pd
import json
import numpy as np

print("="*80)
print("SIGNAL DISTRIBUTION DIAGNOSTIC")
print("="*80)

# Load 24h signals (most data)
signals_df = pd.read_csv('paper_trading_outputs/24h/sheets_fallback/signals.csv')

print(f"\nTotal signals: {len(signals_df)}")

# Check if we have the necessary columns
print(f"\nColumns: {signals_df.columns.tolist()}")

# Analyze S_top, S_bot, mood
if 'S_top' in signals_df.columns:
    print(f"\nS_top (pros):")
    print(f"  Mean: {signals_df['S_top'].mean():.4f}")
    print(f"  Positive: {(signals_df['S_top'] > 0).sum()}")
    print(f"  Negative: {(signals_df['S_top'] < 0).sum()}")
    print(f"  Neutral: {(signals_df['S_top'] == 0).sum()}")

if 'S_bot' in signals_df.columns:
    print(f"\nS_bot (amateurs):")
    print(f"  Mean: {signals_df['S_bot'].mean():.4f}")
    print(f"  Positive: {(signals_df['S_bot'] > 0).sum()}")
    print(f"  Negative: {(signals_df['S_bot'] < 0).sum()}")
    print(f"  Neutral: {(signals_df['S_bot'] == 0).sum()}")

# Check model predictions
if 's_model' in signals_df.columns:
    print(f"\ns_model:")
    print(f"  Mean: {signals_df['s_model'].mean():.4f}")
    print(f"  Positive: {(signals_df['s_model'] > 0).sum()}")
    print(f"  Negative: {(signals_df['s_model'] < 0).sum()}")
    print(f"  Neutral: {(signals_df['s_model'] == 0).sum()}")
    print(f"  Min: {signals_df['s_model'].min():.4f}")
    print(f"  Max: {signals_df['s_model'].max():.4f}")

# Check executed trades
exec_df = pd.read_csv('paper_trading_outputs/24h/sheets_fallback/executions_paper.csv')

print(f"\n" + "="*80)
print("EXECUTION DISTRIBUTION")
print("="*80)

print(f"\nTotal executions: {len(exec_df)}")
print(f"\nSide distribution:")
print(exec_df['side'].value_counts())

# Match executions to signals
print(f"\n" + "="*80)
print("SIGNAL-TO-EXECUTION MAPPING")
print("="*80)

# Try to find signals that led to executions
exec_times = pd.to_datetime(exec_df['ts_iso'], format='mixed')
signal_times = pd.to_datetime(signals_df['ts_iso'], format='mixed')

print(f"\nFirst 5 executions with their signals:")
for idx in range(min(5, len(exec_df))):
    exec_time = exec_times.iloc[idx]
    exec_side = exec_df.iloc[idx]['side']
    
    # Find matching signal
    matching_signal = signals_df[signal_times == exec_time]
    
    if len(matching_signal) > 0:
        sig = matching_signal.iloc[0]
        print(f"\n{exec_time} - {exec_side}:")
        if 's_model' in sig:
            print(f"  s_model: {sig['s_model']:.4f}")
        if 'S_top' in sig:
            print(f"  S_top: {sig['S_top']:.4f}")
        if 'S_bot' in sig:
            print(f"  S_bot: {sig['S_bot']:.4f}")

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)

# Check if model is always positive
if 's_model' in signals_df.columns:
    always_positive = (signals_df['s_model'] >= 0).all()
    mostly_positive = (signals_df['s_model'] > 0).sum() / len(signals_df)
    
    if always_positive:
        print("\n🔴 FOUND THE BUG: s_model is ALWAYS >= 0!")
        print("   This explains why we only see BUY trades.")
        print("   The model never predicts DOWN movements.")
    elif mostly_positive > 0.9:
        print(f"\n🟡 WARNING: s_model is {mostly_positive*100:.1f}% positive")
        print("   Model is heavily biased towards UP predictions.")
    else:
        print(f"\n✅ s_model distribution looks normal:")
        print(f"   {mostly_positive*100:.1f}% positive, {(1-mostly_positive)*100:.1f}% negative")

# Check if flip_model flag might be the issue
print("\n" + "="*80)
print("CHECKING CONFIG")
print("="*80)

import json
with open('live_demo_24h/config.json', 'r') as f:
    config = json.load(f)

flip_model = config.get('thresholds', {}).get('flip_model', None)
flip_mood = config.get('thresholds', {}).get('flip_mood', None)

print(f"\nConfig settings:")
print(f"  flip_model: {flip_model}")
print(f"  flip_mood: {flip_mood}")

if flip_model == False:
    print("\n🔴 POTENTIAL ISSUE: flip_model is False")
    print("   If the model was trained with flipped labels, this could cause")
    print("   the system to always trade in one direction.")
