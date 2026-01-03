"""
DIAGNOSE: Why is 5m bot not producing trades after 6 hours?
Check configuration, thresholds, signals, and model predictions
"""
import json
import os
import pandas as pd
from datetime import datetime

print("=" * 80)
print("DIAGNOSIS: WHY NO TRADES AFTER 6 HOURS?")
print("=" * 80)
print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================
# CHECK 1: CONFIGURATION THRESHOLDS
# ============================================
print("🔍 CHECK 1: CONFIGURATION THRESHOLDS")
print("-" * 80)

with open('live_demo/config.json', 'r') as f:
    config = json.load(f)

print("Trading Thresholds:")
thresholds = config.get('thresholds', {})

conf_min = thresholds.get('CONF_MIN', 'N/A')
alpha_min = thresholds.get('ALPHA_MIN', 'N/A')
s_min = thresholds.get('S_MIN', 'N/A')
m_min = thresholds.get('M_MIN', 'N/A')

print(f"  CONF_MIN: {conf_min}")
print(f"  ALPHA_MIN: {alpha_min}")
print(f"  S_MIN: {s_min}")
print(f"  M_MIN: {m_min}")
print()

# Check if thresholds are too high
issues = []

if isinstance(conf_min, (int, float)) and conf_min > 0.7:
    issues.append(f"⚠️ CONF_MIN is very high ({conf_min}) - may block trades")
elif isinstance(conf_min, (int, float)) and conf_min > 0.6:
    issues.append(f"⚠️ CONF_MIN is high ({conf_min}) - reduces trade frequency")

if isinstance(alpha_min, (int, float)) and alpha_min > 0.7:
    issues.append(f"⚠️ ALPHA_MIN is very high ({alpha_min}) - may block trades")

if isinstance(s_min, (int, float)) and s_min > 0.5:
    issues.append(f"⚠️ S_MIN is high ({s_min}) - reduces trade frequency")

if issues:
    print("Threshold Issues:")
    for issue in issues:
        print(f"  {issue}")
else:
    print("✅ Thresholds appear reasonable")

print()

# Check require_consensus
require_consensus = thresholds.get('require_consensus', True)
print(f"Require Consensus: {require_consensus}")
if require_consensus:
    print("  ⚠️ WARNING: Consensus required - may block SELL trades")
else:
    print("  ✅ Consensus disabled - both directions allowed")

print()

# ============================================
# CHECK 2: SIGNAL GENERATION
# ============================================
print("🔍 CHECK 2: SIGNAL GENERATION")
print("-" * 80)

signal_file = 'paper_trading_outputs/5m/logs/signals/date=2026-01-02/signals.csv'

if os.path.exists(signal_file):
    try:
        df_signals = pd.read_csv(signal_file)
        print(f"✅ Signals file exists: {len(df_signals)} signals generated today")
        print()
        
        # Check recent signals
        if len(df_signals) > 0:
            recent_signals = df_signals.tail(20)
            
            # Check if model is predicting
            if 's_model' in recent_signals.columns:
                s_model_values = recent_signals['s_model'].dropna()
                
                if len(s_model_values) > 0:
                    print(f"Recent Model Predictions (last 20 signals):")
                    print(f"  Min: {s_model_values.min():.4f}")
                    print(f"  Max: {s_model_values.max():.4f}")
                    print(f"  Mean: {s_model_values.mean():.4f}")
                    print(f"  Std: {s_model_values.std():.4f}")
                    print()
                    
                    # Check if predictions are too weak
                    if abs(s_model_values).max() < 0.3:
                        print("  🔴 PROBLEM: All predictions are VERY WEAK (<0.3)")
                        print("     Model is not confident about any direction")
                    elif abs(s_model_values).max() < 0.5:
                        print("  ⚠️ WARNING: Predictions are weak (<0.5)")
                        print("     Model needs stronger signals to trade")
                    else:
                        print("  ✅ Some predictions are strong enough")
                    
                    # Check direction distribution
                    up_signals = sum(s_model_values > 0)
                    down_signals = sum(s_model_values < 0)
                    neutral_signals = sum(s_model_values == 0)
                    
                    print()
                    print(f"Signal Directions:")
                    print(f"  UP: {up_signals}")
                    print(f"  DOWN: {down_signals}")
                    print(f"  NEUTRAL: {neutral_signals}")
                    
                    if down_signals == 0:
                        print("  ⚠️ WARNING: No DOWN signals - model may be one-directional")
                    elif up_signals == 0:
                        print("  ⚠️ WARNING: No UP signals - model may be one-directional")
                else:
                    print("  ⚠️ No s_model values found in recent signals")
            else:
                print("  ⚠️ s_model column not found in signals")
        else:
            print("  ⚠️ No signals generated yet")
            
    except Exception as e:
        print(f"  ❌ Error reading signals: {e}")
else:
    print(f"❌ Signals file not found: {signal_file}")

print()

# ============================================
# CHECK 3: WARMUP PERIOD
# ============================================
print("🔍 CHECK 3: WARMUP PERIOD")
print("-" * 80)

warmup_bars = config.get('warmup_bars', 0)
print(f"Warmup Bars: {warmup_bars}")

if warmup_bars > 100:
    print(f"  ⚠️ WARNING: Warmup is very long ({warmup_bars} bars = {warmup_bars*5} minutes)")
    print(f"     Bot needs {warmup_bars*5/60:.1f} hours of data before trading")
elif warmup_bars > 50:
    print(f"  ⚠️ Warmup is moderate ({warmup_bars} bars = {warmup_bars*5} minutes)")
else:
    print(f"  ✅ Warmup is reasonable ({warmup_bars} bars = {warmup_bars*5} minutes)")

print()

# ============================================
# CHECK 4: DRY RUN MODE
# ============================================
print("🔍 CHECK 4: DRY RUN MODE")
print("-" * 80)

dry_run = config.get('dry_run', True)
print(f"Dry Run: {dry_run}")

if dry_run:
    print("  ✅ Paper trading mode (safe)")
else:
    print("  ⚠️ LIVE TRADING MODE")

print()

# ============================================
# DIAGNOSIS SUMMARY
# ============================================
print("=" * 80)
print("🎯 DIAGNOSIS SUMMARY")
print("=" * 80)
print()

problems = []
warnings = []

# Analyze findings
if isinstance(conf_min, (int, float)) and conf_min > 0.7:
    problems.append("CONF_MIN too high - blocking trades")
elif isinstance(conf_min, (int, float)) and conf_min > 0.6:
    warnings.append("CONF_MIN is high - reducing trade frequency")

if require_consensus:
    warnings.append("Consensus required - may block SELL trades")

if warmup_bars > 100:
    problems.append(f"Warmup too long ({warmup_bars} bars) - bot still warming up")

if os.path.exists(signal_file):
    df_signals = pd.read_csv(signal_file)
    if len(df_signals) > 0 and 's_model' in df_signals.columns:
        s_model_values = df_signals['s_model'].dropna()
        if len(s_model_values) > 0 and abs(s_model_values).max() < 0.3:
            problems.append("Model predictions too weak - not confident")

print("Problems Found:")
if problems:
    for p in problems:
        print(f"  🔴 {p}")
else:
    print("  ✅ No critical problems")

print()

print("Warnings:")
if warnings:
    for w in warnings:
        print(f"  ⚠️ {w}")
else:
    print("  ✅ No warnings")

print()

# ============================================
# ROOT CAUSE
# ============================================
print("=" * 80)
print("🔍 MOST LIKELY ROOT CAUSE")
print("=" * 80)
print()

if warmup_bars > 100:
    print("🔴 ROOT CAUSE: WARMUP PERIOD TOO LONG")
    print()
    print(f"Bot needs {warmup_bars} bars ({warmup_bars*5/60:.1f} hours) before trading")
    print(f"Runtime: 6 hours")
    print(f"Warmup needed: {warmup_bars*5/60:.1f} hours")
    print()
    if warmup_bars * 5 / 60 > 6:
        print("⚠️ Bot is STILL in warmup period!")
        print("   It won't trade until warmup is complete")
    
elif isinstance(conf_min, (int, float)) and conf_min > 0.7:
    print("🔴 ROOT CAUSE: CONFIDENCE THRESHOLD TOO HIGH")
    print()
    print(f"CONF_MIN = {conf_min}")
    print("Model predictions are not reaching this threshold")
    print("No trades can execute")
    
elif os.path.exists(signal_file):
    df_signals = pd.read_csv(signal_file)
    if len(df_signals) > 0 and 's_model' in df_signals.columns:
        s_model_values = df_signals['s_model'].dropna()
        if len(s_model_values) > 0 and abs(s_model_values).max() < 0.5:
            print("🔴 ROOT CAUSE: MODEL PREDICTIONS TOO WEAK")
            print()
            print(f"Max prediction strength: {abs(s_model_values).max():.4f}")
            print(f"Threshold needed: {conf_min if isinstance(conf_min, (int, float)) else 'Unknown'}")
            print()
            print("Model is not confident enough to trade")
            print("This could be due to:")
            print("  1. Market conditions (low volatility, unclear trends)")
            print("  2. Model needs more diverse training data")
            print("  3. Thresholds are too conservative")
else:
    print("⚠️ UNKNOWN: Need more data to diagnose")

print()
print("=" * 80)
