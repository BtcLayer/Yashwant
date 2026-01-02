"""
Final diagnostic - trace exactly where SELL signals are blocked
"""

import pandas as pd

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

# After flip, negative s_model values would become SELL signals
# Let's find where they are in the current data

# With flip_model=true:
# Raw model DOWN (negative) → flipped to UP (positive) → s_model positive
# Raw model UP (positive) → flipped to DOWN (negative) → s_model negative

# So in signals.csv with flip=true:
# s_model < 0 means raw model predicted UP, got flipped to DOWN
# These SHOULD become SELL signals

down_after_flip = df[df['s_model'] < 0]

print(f"Signals that should be SELL (s_model < 0 after flip): {len(down_after_flip)}")
print(f"\nTheir dir values:")
print(down_after_flip['dir'].value_counts())

print(f"\nSample of these signals:")
for idx, row in down_after_flip.head(10).iterrows():
    s_model = row['s_model']
    direction = row['dir']
    s_mood = row.get('S_mood', 0)
    
    dir_str = "SELL" if direction == -1 else ("BUY" if direction == 1 else "NEUT")
    
    # Check thresholds
    model_ok = abs(s_model) >= 0.05  # S_MIN
    mood_ok = abs(s_mood) >= 0.12    # M_MIN
    conf = abs(s_model)  # Simplified
    conf_ok = conf >= 0.60  # CONF_MIN
    
    print(f"\n  s_model={s_model:.4f}, S_mood={s_mood:.4f}")
    print(f"  model_ok={model_ok}, mood_ok={mood_ok}, conf_ok={conf_ok}")
    print(f"  → dir={dir_str}")
    
    if direction == 0:
        if not model_ok:
            print(f"  ❌ Blocked by: S_MIN threshold")
        elif not mood_ok and not conf_ok:
            print(f"  ❌ Blocked by: CONF_MIN threshold (model-only path)")
        elif not mood_ok:
            print(f"  ❌ Blocked by: mood not OK, model-only path failed")
        else:
            print(f"  ❌ Blocked by: consensus or other gate")

print(f"\n" + "="*80)
print("CONCLUSION:")
if len(down_after_flip[down_after_flip['dir'] == -1]) == 0:
    print("NO SELL signals generated despite DOWN predictions")
    print("Likely blocked by CONF_MIN (0.60) threshold")
    print("\nSOLUTION: Lower CONF_MIN to allow weaker signals")
