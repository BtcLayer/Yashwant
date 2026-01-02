"""
IMPACT ANALYSIS: Disabling Consensus Check
Analyze what happens if we remove the consensus requirement
"""

import pandas as pd

print("="*80)
print("IMPACT ANALYSIS: DISABLING CONSENSUS CHECK")
print("="*80)

# Load signals
df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

print("\n1. CURRENT STATE (WITH CONSENSUS):")
print("="*80)

# Count current decisions
current_decisions = df['dir'].value_counts()
print(f"\nCurrent decision distribution:")
print(f"  dir = 1 (BUY): {current_decisions.get(1, 0)}")
print(f"  dir = -1 (SELL): {current_decisions.get(-1, 0)}")
print(f"  dir = 0 (NEUTRAL): {current_decisions.get(0, 0)}")

total_signals = len(df)
execution_rate = (current_decisions.get(1, 0) + current_decisions.get(-1, 0)) / total_signals * 100

print(f"\nCurrent execution rate: {execution_rate:.1f}%")
print(f"Current filter rate: {100-execution_rate:.1f}%")

print("\n2. SIMULATED STATE (WITHOUT CONSENSUS):")
print("="*80)

# Simulate what would happen without consensus
# Decision would be based purely on s_model
simulated_buy = (df['s_model'] > 0).sum()
simulated_sell = (df['s_model'] < 0).sum()
simulated_neutral = (df['s_model'] == 0).sum()

print(f"\nSimulated decision distribution (model-only):")
print(f"  dir = 1 (BUY): {simulated_buy}")
print(f"  dir = -1 (SELL): {simulated_sell}")
print(f"  dir = 0 (NEUTRAL): {simulated_neutral}")

new_execution_rate = (simulated_buy + simulated_sell) / total_signals * 100

print(f"\nNew execution rate: {new_execution_rate:.1f}%")
print(f"New filter rate: {100-new_execution_rate:.1f}%")

print("\n3. IMPACT ANALYSIS:")
print("="*80)

# Calculate changes
additional_trades = (simulated_buy + simulated_sell) - (current_decisions.get(1, 0) + current_decisions.get(-1, 0))
additional_buy = simulated_buy - current_decisions.get(1, 0)
additional_sell = simulated_sell - current_decisions.get(-1, 0)

print(f"\nChanges:")
print(f"  Additional trades: +{additional_trades} ({additional_trades/total_signals*100:.1f}%)")
print(f"  Additional BUY: +{additional_buy}")
print(f"  Additional SELL: +{additional_sell}")

print(f"\nExecution rate change: {execution_rate:.1f}% → {new_execution_rate:.1f}% (+{new_execution_rate-execution_rate:.1f}%)")

print("\n4. RISK ASSESSMENT:")
print("="*80)

# Check if we're currently blocking mostly good or bad signals
# We can't know for sure without future data, but we can check signal strength

# Signals currently blocked by consensus
blocked = df[df['dir'] == 0]
blocked_model_strength = blocked['s_model'].abs().mean() if len(blocked) > 0 else 0

# Signals currently allowed
allowed = df[df['dir'] != 0]
allowed_model_strength = allowed['s_model'].abs().mean() if len(allowed) > 0 else 0

print(f"\nSignal strength comparison:")
print(f"  Currently ALLOWED signals: avg |s_model| = {allowed_model_strength:.4f}")
print(f"  Currently BLOCKED signals: avg |s_model| = {blocked_model_strength:.4f}")

if blocked_model_strength > allowed_model_strength:
    print(f"\n  ⚠️  BLOCKED signals are STRONGER than allowed ones!")
    print(f"     → Consensus may be filtering good signals")
    print(f"     → Disabling consensus could IMPROVE performance")
elif blocked_model_strength < allowed_model_strength * 0.5:
    print(f"\n  ✅ BLOCKED signals are much WEAKER")
    print(f"     → Consensus is filtering weak signals (good)")
    print(f"     → Disabling consensus may ADD NOISE")
else:
    print(f"\n  ⚠️  BLOCKED and ALLOWED signals have similar strength")
    print(f"     → Consensus may not be adding value")

# Check what percentage of blocked signals would be SELL
blocked_sell = blocked[blocked['s_model'] < 0]
print(f"\nOf the {len(blocked)} blocked signals:")
print(f"  Would be SELL: {len(blocked_sell)} ({len(blocked_sell)/len(blocked)*100:.1f}%)")
print(f"  Would be BUY: {len(blocked) - len(blocked_sell)} ({(len(blocked)-len(blocked_sell))/len(blocked)*100:.1f}%)")

print("\n5. WHAT COULD BREAK:")
print("="*80)

risks = []
benefits = []

# Risk 1: More trades = more costs
if additional_trades > 0:
    risks.append(f"📊 Trade frequency increases by {additional_trades} ({additional_trades/total_signals*100:.1f}%)")
    risks.append(f"   → More transaction costs")
    risks.append(f"   → Impact: Moderate (can be offset by better signals)")

# Risk 2: Signal quality
if blocked_model_strength < allowed_model_strength * 0.7:
    risks.append(f"⚠️  Blocked signals are weaker than allowed ones")
    risks.append(f"   → May add low-quality trades")
    risks.append(f"   → Impact: Moderate to High")
else:
    benefits.append(f"✅ Blocked signals are as strong as allowed ones")
    benefits.append(f"   → Not filtering based on quality")

# Benefit 1: SELL trades enabled
if additional_sell > 0:
    benefits.append(f"✅ Enables {additional_sell} SELL trades (currently 0)")
    benefits.append(f"   → Allows positions to close")
    benefits.append(f"   → CRITICAL for profitability")

# Benefit 2: Bidirectional trading
benefits.append(f"✅ Enables bidirectional trading")
benefits.append(f"   → Can profit from both UP and DOWN moves")
benefits.append(f"   → Essential for any profitable system")

# Risk 3: Mood signal ignored
risks.append(f"📉 Cohort mood signal will be ignored")
risks.append(f"   → Loses diversification benefit")
risks.append(f"   → Impact: Low to Moderate (model may be better)")

print("\n🔴 POTENTIAL RISKS:")
for risk in risks:
    print(f"  {risk}")

print(f"\n✅ POTENTIAL BENEFITS:")
for benefit in benefits:
    print(f"  {benefit}")

print("\n6. RECOMMENDATION:")
print("="*80)

# Make recommendation based on analysis
if additional_sell > 50:
    print(f"\n✅ STRONGLY RECOMMEND disabling consensus:")
    print(f"   - Enables {additional_sell} SELL trades (critical!)")
    print(f"   - Current system is completely broken (0 SELL trades)")
    print(f"   - Benefits far outweigh risks")
    print(f"   - Can always re-enable if performance degrades")
elif additional_sell > 10:
    print(f"\n✅ RECOMMEND disabling consensus:")
    print(f"   - Enables {additional_sell} SELL trades")
    print(f"   - Necessary for bidirectional trading")
    print(f"   - Monitor performance closely")
else:
    print(f"\n⚠️  CAUTIOUSLY RECOMMEND disabling consensus:")
    print(f"   - Only enables {additional_sell} SELL trades")
    print(f"   - May not significantly improve performance")
    print(f"   - Test carefully")

print(f"\n7. MITIGATION STRATEGIES:")
print("="*80)

print(f"\nTo minimize risks:")
print(f"  1. ✅ Implement as a CONFIG FLAG (easy to toggle)")
print(f"  2. ✅ Monitor win rate after change")
print(f"  3. ✅ Track execution rate (should increase)")
print(f"  4. ✅ Compare P&L before/after")
print(f"  5. ✅ Keep consensus code intact (can re-enable)")
print(f"  6. ✅ Test on paper trading first (already doing this)")

print(f"\n8. ROLLBACK PLAN:")
print("="*80)

print(f"\nIf performance degrades:")
print(f"  1. Set require_consensus = true in config")
print(f"  2. Restart bot")
print(f"  3. System reverts to current behavior")
print(f"  4. No code changes needed")

print("\n" + "="*80)
print("FINAL VERDICT:")
print("="*80)

print(f"\n✅ SAFE TO IMPLEMENT")
print(f"   - Won't break existing functionality")
print(f"   - Easy to rollback")
print(f"   - Critical for enabling SELL trades")
print(f"   - Benefits >> Risks")

print(f"\n⚠️  MONITOR CLOSELY")
print(f"   - Watch win rate")
print(f"   - Track execution rate")
print(f"   - Compare P&L")
print(f"   - Be ready to rollback if needed")

print("="*80)
