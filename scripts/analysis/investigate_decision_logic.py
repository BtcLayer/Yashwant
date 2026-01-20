"""
Step 2: Investigate Decision Logic and Cohort Signals
"""
import pandas as pd
import json

print("="*80)
print("STEP 2: DECISION LOGIC & COHORT ANALYSIS")
print("="*80)

# Load signals
signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

print("\n--- COHORT SIGNAL ANALYSIS ---")
print(f"\nS_top (Pros/Top cohort):")
print(f"  Mean: {signals['S_top'].mean():.8f}")
print(f"  Std: {signals['S_top'].std():.8f}")
print(f"  Non-zero: {(signals['S_top'] != 0).sum()} ({(signals['S_top'] != 0).sum()/len(signals)*100:.1f}%)")
print(f"  Positive: {(signals['S_top'] > 0).sum()}")
print(f"  Negative: {(signals['S_top'] < 0).sum()}")

print(f"\nS_bot (Amateurs/Bottom cohort):")
print(f"  Mean: {signals['S_bot'].mean():.8f}")
print(f"  Std: {signals['S_bot'].std():.8f}")
print(f"  Non-zero: {(signals['S_bot'] != 0).sum()} ({(signals['S_bot'] != 0).sum()/len(signals)*100:.1f}%)")
print(f"  Positive: {(signals['S_bot'] > 0).sum()}")
print(f"  Negative: {(signals['S_bot'] < 0).sum()}")

print(f"\nS_mood:")
print(f"  Mean: {signals['S_mood'].mean():.8f}")
print(f"  Std: {signals['S_mood'].std():.8f}")
print(f"  Non-zero: {(signals['S_mood'] != 0).sum()} ({(signals['S_mood'] != 0).sum()/len(signals)*100:.1f}%)")

# Check model signals
print(f"\ns_model:")
print(f"  Mean: {signals['s_model'].mean():.8f}")
print(f"  Std: {signals['s_model'].std():.8f}")
print(f"  Positive: {(signals['s_model'] > 0).sum()}")
print(f"  Negative: {(signals['s_model'] < 0).sum()}")

print(f"\ns_model_bma:")
print(f"  Mean: {signals['s_model_bma'].mean():.8f}")
print(f"  Std: {signals['s_model_bma'].std():.8f}")
print(f"  Positive: {(signals['s_model_bma'] > 0).sum()}")
print(f"  Negative: {(signals['s_model_bma'] < 0).sum()}")

# Check probabilities
print("\n--- MODEL PROBABILITIES ---")
print(f"\np_up:")
print(f"  Mean: {signals['p_up'].mean():.4f}")
print(f"  > 0.5: {(signals['p_up'] > 0.5).sum()}")

print(f"\np_down:")
print(f"  Mean: {signals['p_down'].mean():.4f}")
print(f"  > 0.5: {(signals['p_down'] > 0.5).sum()}")

print(f"\np_neutral:")
print(f"  Mean: {signals['p_neutral'].mean():.4f}")
print(f"  > 0.5: {(signals['p_neutral'] > 0.5).sum()}")

# Calculate confidence and alpha manually
signals['conf_calc'] = signals[['p_up', 'p_down']].max(axis=1)
signals['alpha_calc'] = (signals['p_up'] - signals['p_down']).abs()

print("\n--- CALCULATED THRESHOLDS ---")
print(f"Confidence (max(p_up, p_down)):")
print(f"  Mean: {signals['conf_calc'].mean():.4f}")
print(f"  >= 0.60: {(signals['conf_calc'] >= 0.60).sum()} ({(signals['conf_calc'] >= 0.60).sum()/len(signals)*100:.1f}%)")

print(f"\nAlpha (|p_up - p_down|):")
print(f"  Mean: {signals['alpha_calc'].mean():.4f}")
print(f"  >= 0.10: {(signals['alpha_calc'] >= 0.10).sum()} ({(signals['alpha_calc'] >= 0.10).sum()/len(signals)*100:.1f}%)")
print(f"  >= 0.02: {(signals['alpha_calc'] >= 0.02).sum()} ({(signals['alpha_calc'] >= 0.02).sum()/len(signals)*100:.1f}%)")

# Check eligibility
print("\n--- ELIGIBILITY CHECK ---")
eligible_model = (signals['conf_calc'] >= 0.60) & (signals['alpha_calc'] >= 0.10)
print(f"Model eligible (conf>=0.60 AND alpha>=0.10): {eligible_model.sum()} ({eligible_model.sum()/len(signals)*100:.1f}%)")

# With lower alpha threshold
eligible_model_low = (signals['conf_calc'] >= 0.60) & (signals['alpha_calc'] >= 0.02)
print(f"Model eligible (conf>=0.60 AND alpha>=0.02): {eligible_model_low.sum()} ({eligible_model_low.sum()/len(signals)*100:.1f}%)")

# Check recent signals
print("\n--- RECENT 10 SIGNALS DETAIL ---")
recent = signals.tail(10)
cols = ['ts_iso', 'p_up', 'p_down', 'p_neutral', 'conf_calc', 'alpha_calc', 'dir', 'alpha']
print(recent[cols].to_string(index=False))

print("\n" + "="*80)
print("DIAGNOSIS - STEP 2")
print("="*80)

# Key findings
print(f"\n1. S_bot is ALL ZEROS - Bottom cohort not working!")
print(f"2. Model eligibility with ALPHA_MIN=0.10: {eligible_model.sum()} signals")
print(f"3. Model eligibility with ALPHA_MIN=0.02: {eligible_model_low.sum()} signals")
print(f"4. p_neutral is dominating (mean={signals['p_neutral'].mean():.3f})")

# Check if p_neutral > both p_up and p_down
neutral_dominant = (signals['p_neutral'] > signals['p_up']) & (signals['p_neutral'] > signals['p_down'])
print(f"5. Neutral dominant: {neutral_dominant.sum()} ({neutral_dominant.sum()/len(signals)*100:.1f}%)")

print("\n" + "="*80)
