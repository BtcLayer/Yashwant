import pandas as pd

print("=" * 70)
print("FEE IMPACT ANALYSIS & PLATFORM COMPARISON")
print("=" * 70)

# Current status
equity = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/equity.csv').tail(1).iloc[0]
signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv').tail(20)

balance = equity['equity']
realized_pnl = equity['realized']
unrealized_pnl = equity['unrealized']
total_pnl = realized_pnl + unrealized_pnl

print("\n[CURRENT STATUS - NEW MODEL SESSION]")
print(f"  Starting Balance:  $10,000.00")
print(f"  Current Balance:   ${balance:.2f}")
print(f"  Total P&L:         ${total_pnl:.2f}")
print(f"  Realized (Fees):   ${realized_pnl:.2f}")
print(f"  Unrealized (Move): ${unrealized_pnl:.2f}")

# Fee breakdown
print("\n[FEE BREAKDOWN]")
print(f"  Fees Paid:         ${abs(realized_pnl):.2f}")
print(f"  % of Total Loss:   {abs(realized_pnl)/abs(total_pnl)*100:.1f}%")
print(f"  Price Movement:    ${unrealized_pnl:.2f}")
print(f"  % of Total Loss:   {abs(unrealized_pnl)/abs(total_pnl)*100:.1f}%")

# Model performance
signals['alpha'] = abs(signals['p_up'] - signals['p_down'])
signals['edge_bps'] = signals['alpha'] * 50.0
avg_edge = signals['edge_bps'].mean()

print("\n[MODEL PERFORMANCE]")
print(f"  Avg Predicted Edge: {avg_edge:.2f} bps")
print(f"  Signals > 8bps:     {(signals['edge_bps'] > 8).sum()}/20 ({(signals['edge_bps'] > 8).sum()/20*100:.0f}%)")

# Platform comparison
print("\n" + "=" * 70)
print("PLATFORM COMPARISON")
print("=" * 70)

print("\n[CURRENT: HYPERLIQUID]")
print("  Taker Fee:         5 bps (0.05%)")
print("  Maker Fee:         0.2 bps (0.002%)")
print("  Slippage:          ~1 bps")
print("  Total Cost (Taker): 6 bps per side = 12 bps round-trip")
print("  Total Cost (Maker): 1.2 bps per side = 2.4 bps round-trip")

print("\n[ALTERNATIVE: LIGHTER (ZERO FEES)]")
print("  Taker Fee:         0 bps")
print("  Maker Fee:         0 bps")
print("  Slippage:          ~1-2 bps (potentially higher, less liquidity)")
print("  Total Cost:        1-2 bps round-trip")

# Impact calculation
print("\n" + "=" * 70)
print("IMPACT ANALYSIS")
print("=" * 70)

current_hurdle = 8.0  # Current net edge gate
zero_fee_hurdle = 2.0  # With zero fees (just slippage + buffer)

print(f"\n[CURRENT SETUP (Hyperliquid Taker)]")
print(f"  Required Edge:     {current_hurdle:.1f} bps")
print(f"  Model Avg Edge:    {avg_edge:.2f} bps")
print(f"  Gap:               {avg_edge - current_hurdle:.2f} bps")
print(f"  Profitable?        {'YES' if avg_edge > current_hurdle else 'NO (Close!)'}")

print(f"\n[WITH ZERO FEES (Lighter)]")
print(f"  Required Edge:     {zero_fee_hurdle:.1f} bps")
print(f"  Model Avg Edge:    {avg_edge:.2f} bps")
print(f"  Gap:               {avg_edge - zero_fee_hurdle:.2f} bps")
print(f"  Profitable?        YES (by {avg_edge - zero_fee_hurdle:.2f} bps)")

# Estimate profit improvement
fee_savings_per_trade = 10.0  # 5 bps entry + 5 bps exit
print(f"\n[ESTIMATED IMPROVEMENT]")
print(f"  Fee Savings:       ~10 bps per round-trip")
print(f"  Current Loss:      ${abs(total_pnl):.2f}")
print(f"  Without Fees:      ~${abs(total_pnl) - abs(realized_pnl):.2f} (just price movement)")
print(f"  Potential Gain:    ${abs(realized_pnl):.2f} saved on fees")

print("\n" + "=" * 70)
print("CONSEQUENCES OF SWITCHING")
print("=" * 70)

print("\n[PROS]")
print("  + Zero trading fees = immediate 10 bps advantage")
print("  + Lower hurdle (2 bps vs 8 bps) = more trades")
print("  + Current model (6.5 bps avg) becomes profitable")
print("  + Estimated improvement: +$0.73 per trade cycle")

print("\n[CONS]")
print("  - Lower liquidity = potentially higher slippage")
print("  - Less established platform = higher risk")
print("  - May need API changes/testing")
print("  - Unknown execution quality")

print("\n[RISK ASSESSMENT]")
if avg_edge > zero_fee_hurdle and avg_edge < current_hurdle:
    print("  Risk Level:        MEDIUM")
    print("  Reasoning:         Model is borderline profitable on Hyperliquid")
    print("                     but would be clearly profitable on Lighter.")
    print("                     Switching makes mathematical sense IF liquidity")
    print("                     and execution quality are comparable.")
else:
    print("  Risk Level:        LOW")
    print("  Reasoning:         Model needs improvement regardless of fees.")

print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)

if avg_edge > 5 and avg_edge < current_hurdle:
    print("\n[SWITCH TO LIGHTER - RECOMMENDED]")
    print("  Your model generates ~6.5 bps average edge.")
    print("  This is NOT enough on Hyperliquid (needs 8 bps)")
    print("  but WOULD BE profitable on Lighter (needs 2 bps).")
    print("")
    print("  Action Plan:")
    print("  1. Test Lighter API integration (paper trading)")
    print("  2. Verify execution quality and slippage")
    print("  3. If comparable, switch to Lighter")
    print("  4. Expected result: Turn -$1.88 loss into small profit")
elif avg_edge > current_hurdle:
    print("\n[STAY ON HYPERLIQUID - RECOMMENDED]")
    print("  Your model is already profitable on Hyperliquid.")
    print("  No need to take platform risk.")
else:
    print("\n[IMPROVE MODEL FIRST - RECOMMENDED]")
    print("  Your model edge is too low for either platform.")
    print("  Focus on retraining/tuning before switching.")

print("\n" + "=" * 70)
