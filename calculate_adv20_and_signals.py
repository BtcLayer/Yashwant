"""
Calculate expected ADV20 and cohort signal values
"""
import pandas as pd

# Load 5m data
df = pd.read_csv("ohlc_btc_5m_complete.csv")

# Calculate ADV20 (20-day average volume)
# For 5m data: 20 days = 20 * 288 bars = 5760 bars
window_bars = 12 * 20  # Using 1h window (12 bars * 20)
adv20 = df["volume"].tail(window_bars).mean()

print(f"ADV20 Calculation:")
print(f"  Window: {window_bars} bars")
print(f"  ADV20: {adv20:,.2f}")

# Simulate cohort signal calculation
# From user_fills_poll_debug.csv, we see 0-160 fills per 5m bar
# Average around 50-100 fills per bar

# Typical fill sizes vary, but let's estimate:
# - Small trader: 0.01-0.1 BTC
# - Medium trader: 0.1-1 BTC  
# - Large trader: 1-10 BTC

print(f"\n{'='*60}")
print("Expected Cohort Signal Calculation:")
print(f"{'='*60}")

# Example scenarios
scenarios = [
    ("Low activity (20 fills, 0.1 BTC avg)", 20, 0.1),
    ("Medium activity (50 fills, 0.3 BTC avg)", 50, 0.3),
    ("High activity (100 fills, 0.5 BTC avg)", 100, 0.5),
]

for desc, num_fills, avg_size in scenarios:
    # Net signed impact assuming 50% buy, 50% sell (net=0)
    # But cohort traders are NOT balanced - they have directional bias
    
    # Pros cohort (bullish bias): 60% buy, 40% sell
    pros_buys = num_fills * 0.6
    pros_sells = num_fills * 0.4
    pros_net_size = (pros_buys - pros_sells) * avg_size
    pros_impact = pros_net_size / adv20
    
    # Amateurs cohort (contrarian - opposite of pros): 40% buy, 60% sell
    am_buys = num_fills * 0.4
    am_sells = num_fills * 0.6
    am_net_size = (am_buys - am_sells) * avg_size
    am_impact = am_net_size / adv20
    
    print(f"\n{desc}:")
    print(f"  Pros impact (S_top): {pros_impact:+.6f}")
    print(f"  Amateurs impact (S_bot): {am_impact:+.6f}")
    print(f"  |S_top|: {abs(pros_impact):.6f}")
    print(f"  |S_bot|: {abs(am_impact):.6f}")

print(f"\n{'='*60}")
print("PROBLEM DIAGNOSIS:")
print(f"{'='*60}")

# Current observed values from investigation
observed_s_top = 0.00135
observed_s_bot = 0.00342

# Expected range based on scenarios
expected_min = 0.001
expected_max = 0.05

print(f"\nObserved:")
print(f"  S_top: {observed_s_top:.6f}")
print(f"  S_bot: {observed_s_bot:.6f}")

print(f"\nExpected range: {expected_min:.6f} - {expected_max:.6f}")

print(f"\nPotential Issues:")

# Check if ADV20 is too large
realistic_adv20 = 1000  # Example: 1000 BTC per bar average
if adv20 > realistic_adv20 * 10:
    print(f"  ⚠️  ADV20 too large! {adv20:,.0f} vs expected ~{realistic_adv20:,.0f}")
    print(f"      This would dilute signals by {adv20/realistic_adv20:.1f}x")

# Check if fill sizes are too small
typical_impact_per_fill = 0.1 / adv20
print(f"  Impact per 0.1 BTC fill: {typical_impact_per_fill:.8f}")

# Calculate how many fills needed to reach S_MIN=0.09
fills_needed_for_s_min = 0.09 * adv20 / 0.1  # Assuming 0.1 BTC avg size
print(f"  Fills needed to reach S_MIN (0.09): {fills_needed_for_s_min:,.0f}")

print(f"\n{'='*60}")
print("SOLUTION:")
print(f"{'='*60}")

# If signals are consistently 100x too small, either:
# 1. ADV20 is 100x too large
# 2. Fill sizes are 100x too small
# 3. Fill counts are 100x too small
# 4. Rolling window is wrong (should be shorter for 5m)

# Check what ADV20 would make current signals reasonable
target_s_top = 0.05  # Target signal strength
current_s_top = observed_s_top
adjusted_adv20 = adv20 * (current_s_top / target_s_top)

print(f"\nIf ADV20 is the issue:")
print(f"  Current ADV20: {adv20:,.0f}")
print(f"  Adjusted ADV20 (for S_top={target_s_top}): {adjusted_adv20:,.0f}")
print(f"  Ratio: {adv20/adjusted_adv20:.1f}x too large")

print(f"\nRecommended fixes:")
print(f"  1. Check ADV20 calculation - should use BTC volume, not contract volume")
print(f"  2. For 5m timeframe, use shorter window: 12 bars (1h) not 240 bars (20h)")
print(f"  3. Verify fill sizes are in BTC, not contracts/USDT")
print(f"  4. Consider using larger smoothing window for cohort signals")
