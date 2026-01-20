"""
DIAGNOSTIC: Find why SELL signals aren't being executed
Check the decision logic to see if DOWN predictions are being converted to SELL signals
"""

import pandas as pd
import json

print("="*80)
print("TRACING SIGNAL FLOW: Model → Decision → Execution")
print("="*80)

# Load data
signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')

print(f"\n1. MODEL OUTPUT (s_model):")
print(f"   UP predictions (s_model > 0): {(signals_df['s_model'] > 0).sum()}")
print(f"   DOWN predictions (s_model < 0): {(signals_df['s_model'] < 0).sum()}")

# Check if there's a 'dir' or 'direction' column in signals
print(f"\n2. DECISION DIRECTION:")
if 'dir' in signals_df.columns:
    print(f"   Signals with dir column found!")
    dir_counts = signals_df['dir'].value_counts()
    print(f"   dir = +1 (BUY): {dir_counts.get(1, 0)}")
    print(f"   dir = -1 (SELL): {dir_counts.get(-1, 0)}")
    print(f"   dir = 0 (NEUTRAL): {dir_counts.get(0, 0)}")
    
    # Check correlation between s_model and dir
    down_preds = signals_df[signals_df['s_model'] < 0]
    if len(down_preds) > 0:
        print(f"\n   When s_model < 0 (DOWN prediction):")
        print(f"   dir = +1: {(down_preds['dir'] == 1).sum()}")
        print(f"   dir = -1: {(down_preds['dir'] == -1).sum()}")
        print(f"   dir = 0: {(down_preds['dir'] == 0).sum()}")
        
        if (down_preds['dir'] == -1).sum() == 0:
            print(f"\n   🔴 BUG FOUND: DOWN predictions NEVER converted to dir=-1!")
            print(f"      → Decision logic is broken")
        elif (down_preds['dir'] == 0).sum() == len(down_preds):
            print(f"\n   🔴 BUG FOUND: All DOWN predictions filtered to NEUTRAL!")
            print(f"      → Gating logic is too strict")
else:
    print(f"   No 'dir' column in signals - checking execution_resp")

# Check position column
print(f"\n3. TARGET POSITION:")
if 'position' in signals_df.columns:
    positions = signals_df['position'].dropna()
    print(f"   Positive positions (LONG): {(positions > 0).sum()}")
    print(f"   Negative positions (SHORT): {(positions < 0).sum()}")
    print(f"   Zero positions (FLAT): {(positions == 0).sum()}")
    
    if (positions < 0).sum() == 0:
        print(f"\n   🔴 POSITION BUG: System NEVER targets SHORT positions!")

# Check raw execution responses
print(f"\n4. EXECUTION RESPONSES:")
print(f"   Checking raw execution data...")

# Sample some executions to see the decision that led to them
print(f"\n   Last 5 executions:")
for idx in range(max(0, len(exec_df)-5), len(exec_df)):
    exec_row = exec_df.iloc[idx]
    ts = exec_row['ts_iso']
    side = exec_row['side']
    
    # Find matching signal
    matching_signal = signals_df[signals_df['ts_iso'] == ts]
    
    if len(matching_signal) > 0:
        sig = matching_signal.iloc[0]
        s_model = sig.get('s_model', 'N/A')
        direction = sig.get('dir', 'N/A')
        position = sig.get('position', 'N/A')
        
        print(f"\n   {ts}:")
        print(f"     s_model: {s_model}")
        print(f"     dir: {direction}")
        print(f"     position: {position}")
        print(f"     → Executed: {side}")
        
        # Check if there's a mismatch
        if s_model != 'N/A':
            expected_dir = 1 if float(s_model) > 0 else -1
            if direction != 'N/A' and int(direction) != expected_dir:
                print(f"     🔴 MISMATCH: s_model suggests dir={expected_dir}, but dir={direction}")

print(f"\n{'='*80}")
print("DIAGNOSIS:")
print("="*80)

# Check the config for any filters
print(f"\nChecking config.json for clues...")
with open('live_demo/config.json', 'r') as f:
    config = json.load(f)

# Check if there's a one_shot or force_validation setting
one_shot = config.get('execution', {}).get('one_shot', False)
force_val = config.get('execution', {}).get('force_validation_trade', False)

print(f"\nConfig settings:")
print(f"  one_shot: {one_shot}")
print(f"  force_validation_trade: {force_val}")

# Check thresholds
thresholds = config.get('thresholds', {})
print(f"\nThresholds:")
print(f"  CONF_MIN: {thresholds.get('CONF_MIN')}")
print(f"  ALPHA_MIN: {thresholds.get('ALPHA_MIN')}")
print(f"  flip_model: {thresholds.get('flip_model')}")
print(f"  flip_mood: {thresholds.get('flip_mood')}")

print(f"\n{'='*80}")
print("CONCLUSION:")
print("="*80)

# Determine if it's a code bug or model bug
down_predictions = (signals_df['s_model'] < 0).sum()

if down_predictions > 0:
    print(f"\n✅ Model IS predicting DOWN ({down_predictions} times)")
    print(f"🔴 But system NEVER executes SELL")
    print(f"\n→ This is a CODE/LOGIC BUG, NOT a model issue")
    print(f"→ Can be fixed locally without retraining")
    print(f"\nPossible causes:")
    print(f"  1. Decision logic always converts to dir=+1")
    print(f"  2. Gating logic filters all DOWN signals")
    print(f"  3. Position management only allows LONG positions")
    print(f"  4. Execution logic has a bug preventing SELL orders")
else:
    print(f"\n🔴 Model NEVER predicts DOWN")
    print(f"\n→ This is a MODEL issue")
    print(f"→ Needs model retraining")

print("="*80)
