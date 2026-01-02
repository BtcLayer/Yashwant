import pandas as pd

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

# Check when model predicts DOWN
down_preds = df[df['s_model'] < 0]

print(f"When s_model < 0 (DOWN prediction) - {len(down_preds)} times:")
print(f"\nMood distribution:")
print(f"  mood > 0 (UP): {(down_preds['mood'] > 0).sum()}")
print(f"  mood < 0 (DOWN): {(down_preds['mood'] < 0).sum()}")
print(f"  mood = 0: {(down_preds['mood'] == 0).sum()}")

print(f"\nConsensus analysis:")
# After flip_mood, s_mood = -mood
# So if mood > 0, after flip s_mood < 0 (DOWN)
# If mood < 0, after flip s_mood > 0 (UP)

# When s_model < 0 (model says DOWN)
# For consensus, we need s_mood < 0 (mood also says DOWN)
# Which means mood > 0 BEFORE flip

mood_agrees = (down_preds['mood'] > 0).sum()  # After flip, these will be DOWN like model
mood_disagrees = (down_preds['mood'] < 0).sum()  # After flip, these will be UP, disagree with model

print(f"  Mood AGREES with model (after flip): {mood_agrees}")
print(f"  Mood DISAGREES with model (after flip): {mood_disagrees}")

print(f"\n🔴 CONSENSUS BLOCKING:")
print(f"   {mood_disagrees} out of {len(down_preds)} DOWN predictions blocked by consensus!")
print(f"   Only {mood_agrees} DOWN predictions pass consensus check")

# Check if those that pass consensus still get filtered
if mood_agrees > 0:
    consensus_pass = down_preds[down_preds['mood'] > 0]
    print(f"\n   Of the {mood_agrees} that pass consensus:")
    print(f"   dir = -1 (SELL): {(consensus_pass['dir'] == -1).sum()}")
    print(f"   dir = 0 (NEUTRAL): {(consensus_pass['dir'] == 0).sum()}")
    print(f"   dir = 1 (BUY): {(consensus_pass['dir'] == 1).sum()}")
    
    if (consensus_pass['dir'] == -1).sum() == 0:
        print(f"\n   🔴 EVEN CONSENSUS-PASSING SIGNALS GET FILTERED!")
        print(f"      → Additional gating beyond consensus")
