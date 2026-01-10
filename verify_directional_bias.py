"""
VERIFY: Do S_top and S_bot cause directional bias?
User's hypothesis: Both take BUY and SELL trades, just with different success rates
"""
import pandas as pd
import numpy as np

print("="*80)
print("VERIFICATION: S_TOP AND S_BOT DIRECTIONAL BIAS")
print("="*80)

# Load signals
signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

print(f"\nAnalyzing {len(signals)} signals")

# Check S_top distribution
print("\n" + "="*80)
print("S_TOP ANALYSIS")
print("="*80)

s_top_nonzero = signals[signals['S_top'] != 0]['S_top']

print(f"Non-zero S_top signals: {len(s_top_nonzero)}")
print(f"\nDistribution:")
print(f"  Positive (indicating BUY pressure): {(s_top_nonzero > 0).sum()} ({(s_top_nonzero > 0).sum()/len(s_top_nonzero)*100:.1f}%)")
print(f"  Negative (indicating SELL pressure): {(s_top_nonzero < 0).sum()} ({(s_top_nonzero < 0).sum()/len(s_top_nonzero)*100:.1f}%)")
print(f"  Mean: {s_top_nonzero.mean():.8f}")
print(f"  Median: {s_top_nonzero.median():.8f}")

# Check S_mood for comparison
print("\n" + "="*80)
print("S_MOOD ANALYSIS (for comparison)")
print("="*80)

s_mood_nonzero = signals[signals['S_mood'] != 0]['S_mood']

print(f"Non-zero S_mood signals: {len(s_mood_nonzero)}")
print(f"\nDistribution:")
print(f"  Positive (BUY pressure): {(s_mood_nonzero > 0).sum()} ({(s_mood_nonzero > 0).sum()/len(s_mood_nonzero)*100:.1f}%)")
print(f"  Negative (SELL pressure): {(s_mood_nonzero < 0).sum()} ({(s_mood_nonzero < 0).sum()/len(s_mood_nonzero)*100:.1f}%)")
print(f"  Mean: {s_mood_nonzero.mean():.8f}")
print(f"  Median: {s_mood_nonzero.median():.8f}")

# Check correlation with direction
print("\n" + "="*80)
print("CORRELATION WITH FINAL DIRECTION")
print("="*80)

if 'dir' in signals.columns:
    # Check how S_top correlates with final direction
    s_top_corr = signals['S_top'].corr(signals['dir'])
    s_mood_corr = signals['S_mood'].corr(signals['dir'])
    
    print(f"S_top correlation with direction: {s_top_corr:.4f}")
    print(f"S_mood correlation with direction: {s_mood_corr:.4f}")
    
    # Check direction distribution
    print(f"\nFinal direction distribution:")
    print(f"  BUY (1): {(signals['dir'] == 1).sum()} ({(signals['dir']==1).sum()/len(signals)*100:.1f}%)")
    print(f"  NEUTRAL (0): {(signals['dir'] == 0).sum()} ({(signals['dir']==0).sum()/len(signals)*100:.1f}%)")
    print(f"  SELL (-1): {(signals['dir'] == -1).sum()} ({(signals['dir']==-1).sum()/len(signals)*100:.1f}%)")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

print("""
USER'S HYPOTHESIS: S_top and S_bot both generate BUY and SELL signals.
The difference is SUCCESS RATE, not direction.

VERIFICATION:
""")

if len(s_top_nonzero) > 0:
    buy_pct = (s_top_nonzero > 0).sum() / len(s_top_nonzero) * 100
    sell_pct = (s_top_nonzero < 0).sum() / len(s_top_nonzero) * 100
    
    print(f"S_top generates:")
    print(f"  {buy_pct:.1f}% BUY signals (positive)")
    print(f"  {sell_pct:.1f}% SELL signals (negative)")
    
    if 40 < buy_pct < 60:
        print(f"\n✓ BALANCED - S_top generates both directions roughly equally")
        print(f"✓ USER IS CORRECT - No directional bias from S_top")
    else:
        print(f"\n✗ IMBALANCED - S_top has directional bias")
        print(f"✗ This could contribute to the BUY-only problem")

print("""
EXPECTED BEHAVIOR:
- Professional traders (S_top): Take both BUY and SELL, but with HIGHER success rate
- Amateur traders (S_bot): Take both BUY and SELL, but with LOWER success rate
- The MODEL learns to:
  * Follow S_top (pros know what they're doing)
  * Fade S_bot (amateurs are usually wrong)

This creates BALANCED predictions, not directional bias.

THE REAL ISSUE:
- S_bot is ZERO (missing signal)
- Model only sees S_top + S_mood
- Missing the contrarian signal from amateurs
- This COULD cause imbalance if amateurs tend to be wrong in a specific direction
""")

print("="*80)
