"""
COMPREHENSIVE 5M VERIFICATION
Check if 5m has SELL trades and is working correctly
"""

import pandas as pd
import json
import numpy as np

print("="*80)
print("5M TIMEFRAME COMPREHENSIVE VERIFICATION")
print("="*80)

# Load data
signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')

print(f"\n📊 DATA SUMMARY:")
print(f"  Total signals: {len(signals_df)}")
print(f"  Total executions: {len(exec_df)}")
print(f"  Execution rate: {len(exec_df)/len(signals_df)*100:.1f}%")

# 1. MODEL OUTPUT ANALYSIS
print(f"\n{'='*80}")
print("1. MODEL OUTPUT ANALYSIS")
print("="*80)

s_model = signals_df['s_model']
print(f"\ns_model statistics:")
print(f"  Mean: {s_model.mean():.4f}")
print(f"  Std: {s_model.std():.4f}")
print(f"  Min: {s_model.min():.4f}")
print(f"  Max: {s_model.max():.4f}")
print(f"  Median: {s_model.median():.4f}")

positive = (s_model > 0).sum()
negative = (s_model < 0).sum()
zero = (s_model == 0).sum()

print(f"\nDirection distribution:")
print(f"  Positive (UP): {positive} ({positive/len(s_model)*100:.1f}%)")
print(f"  Negative (DOWN): {negative} ({negative/len(s_model)*100:.1f}%)")
print(f"  Zero (NEUTRAL): {zero} ({zero/len(s_model)*100:.1f}%)")

if negative > 0 and positive > 0:
    print(f"\n✅ MODEL CAN PREDICT BOTH DIRECTIONS")
else:
    print(f"\n🔴 MODEL IS BROKEN - Can only predict one direction!")

# 2. EXECUTION SIDE ANALYSIS
print(f"\n{'='*80}")
print("2. EXECUTION SIDE ANALYSIS")
print("="*80)

side_counts = exec_df['side'].value_counts()
print(f"\nExecution breakdown:")
print(f"  BUY trades: {side_counts.get('BUY', 0)}")
print(f"  SELL trades: {side_counts.get('SELL', 0)}")

buy_pct = side_counts.get('BUY', 0) / len(exec_df) * 100 if len(exec_df) > 0 else 0
sell_pct = side_counts.get('SELL', 0) / len(exec_df) * 100 if len(exec_df) > 0 else 0

print(f"\nExecution distribution:")
print(f"  BUY: {buy_pct:.1f}%")
print(f"  SELL: {sell_pct:.1f}%")

if side_counts.get('SELL', 0) > 0:
    print(f"\n✅ SYSTEM EXECUTES BOTH BUY AND SELL TRADES")
else:
    print(f"\n🔴 CRITICAL: SYSTEM ONLY EXECUTES BUY TRADES!")
    print(f"   → Same bug as 24h timeframe")
    print(f"   → Position management is broken")

# 3. P&L ANALYSIS
print(f"\n{'='*80}")
print("3. P&L ANALYSIS")
print("="*80)

total_pnl = 0
gross_pnl = 0
total_fees = 0
total_impact = 0
wins = 0
losses = 0
win_pnls = []
loss_pnls = []

for idx, row in exec_df.iterrows():
    try:
        raw = json.loads(row['raw'])
        pnl = raw.get('realized_pnl', 0)
        fee = raw.get('fee', 0)
        impact = raw.get('impact', 0)
        
        total_pnl += pnl
        total_fees += fee
        total_impact += impact
        gross_pnl += (pnl + fee + impact)
        
        if pnl > 0:
            wins += 1
            win_pnls.append(pnl)
        elif pnl < 0:
            losses += 1
            loss_pnls.append(pnl)
    except:
        pass

win_rate = (wins / len(exec_df) * 100) if len(exec_df) > 0 else 0
avg_win = np.mean(win_pnls) if win_pnls else 0
avg_loss = np.mean(loss_pnls) if loss_pnls else 0

print(f"\nP&L Summary:")
print(f"  Gross P&L (before costs): ${gross_pnl:.2f}")
print(f"  Total fees: ${total_fees:.2f}")
print(f"  Total impact: ${total_impact:.2f}")
print(f"  Net P&L (after costs): ${total_pnl:.2f}")

print(f"\nTrade outcomes:")
print(f"  Wins: {wins}")
print(f"  Losses: {losses}")
print(f"  Win rate: {win_rate:.1f}%")

if wins > 0:
    print(f"  Avg win: ${avg_win:.2f}")
if losses > 0:
    print(f"  Avg loss: ${avg_loss:.2f}")

if win_rate == 0:
    print(f"\n🔴 0% WIN RATE - All trades are losses!")
    if gross_pnl > 0:
        print(f"   → Gross P&L is positive (${gross_pnl:.2f})")
        print(f"   → Costs are destroying profitability")
    else:
        print(f"   → Gross P&L is negative (${gross_pnl:.2f})")
        print(f"   → System has no edge even before costs")
elif win_rate < 40:
    print(f"\n🟡 LOW WIN RATE ({win_rate:.1f}%)")
else:
    print(f"\n✅ HEALTHY WIN RATE ({win_rate:.1f}%)")

# 4. SIGNAL-TO-EXECUTION MAPPING
print(f"\n{'='*80}")
print("4. SIGNAL-TO-EXECUTION MAPPING")
print("="*80)

# Sample recent executions and their signals
print(f"\nLast 10 executions with their model predictions:")
print(f"{'Time':<20} {'Side':<6} {'s_model':<10} {'Expected':<10}")
print("-"*50)

exec_df['ts_dt'] = pd.to_datetime(exec_df['ts_iso'], format='mixed')
signals_df['ts_dt'] = pd.to_datetime(signals_df['ts_iso'], format='mixed')

for idx in range(max(0, len(exec_df)-10), len(exec_df)):
    exec_row = exec_df.iloc[idx]
    exec_time = exec_row['ts_dt']
    exec_side = exec_row['side']
    
    # Find matching signal
    matching = signals_df[signals_df['ts_dt'] == exec_time]
    
    if len(matching) > 0:
        sig_row = matching.iloc[0]
        s_model_val = sig_row['s_model']
        expected = "BUY" if s_model_val > 0 else "SELL"
        match = "✅" if expected == exec_side else "🔴"
        
        print(f"{str(exec_time):<20} {exec_side:<6} {s_model_val:>9.4f} {expected:<10} {match}")

# 5. POSITION TRACKING
print(f"\n{'='*80}")
print("5. POSITION TRACKING")
print("="*80)

# Check if positions are being tracked
if 'position' in signals_df.columns:
    positions = signals_df['position'].dropna()
    if len(positions) > 0:
        print(f"\nPosition statistics:")
        print(f"  Mean position: {positions.mean():.4f}")
        print(f"  Min position: {positions.min():.4f}")
        print(f"  Max position: {positions.max():.4f}")
        
        # Check if position ever goes negative (short)
        negative_pos = (positions < 0).sum()
        positive_pos = (positions > 0).sum()
        zero_pos = (positions == 0).sum()
        
        print(f"\nPosition distribution:")
        print(f"  Long (>0): {positive_pos}")
        print(f"  Flat (=0): {zero_pos}")
        print(f"  Short (<0): {negative_pos}")
        
        if negative_pos > 0:
            print(f"\n✅ System can hold SHORT positions")
        else:
            print(f"\n🔴 System NEVER holds SHORT positions")
            print(f"   → Confirms one-directional trading bug")

# 6. FINAL VERDICT
print(f"\n{'='*80}")
print("FINAL VERDICT FOR 5M TIMEFRAME")
print("="*80)

issues = []
working = []

# Check model
if negative > 0 and positive > 0:
    working.append("✅ Model can predict both UP and DOWN")
else:
    issues.append("🔴 Model is broken (one-directional)")

# Check executions
if side_counts.get('SELL', 0) > 0:
    working.append("✅ System executes both BUY and SELL trades")
else:
    issues.append("🔴 System only executes BUY trades (execution bug)")

# Check profitability
if win_rate > 0:
    if win_rate >= 40:
        working.append(f"✅ Healthy win rate ({win_rate:.1f}%)")
    else:
        issues.append(f"🟡 Low win rate ({win_rate:.1f}%)")
else:
    issues.append("🔴 0% win rate (all trades lose)")

# Check P&L
if total_pnl > 0:
    working.append(f"✅ Positive P&L (${total_pnl:.2f})")
elif gross_pnl > 0:
    issues.append(f"🟡 Costs destroying profitability (gross: ${gross_pnl:.2f}, net: ${total_pnl:.2f})")
else:
    issues.append(f"🔴 Negative gross P&L (${gross_pnl:.2f})")

print(f"\n✅ WORKING COMPONENTS:")
for item in working:
    print(f"  {item}")

print(f"\n🔴 ISSUES FOUND:")
for item in issues:
    print(f"  {item}")

print(f"\n{'='*80}")
if len(issues) == 0:
    print("✅ 5M TIMEFRAME IS FULLY OPERATIONAL AND PROFITABLE")
elif "execution bug" in str(issues):
    print("🔴 5M TIMEFRAME HAS SAME BUG AS 24H (BUY-ONLY)")
    print("   → Model works but execution is broken")
    print("   → Needs position management fix")
else:
    print("⚠️  5M TIMEFRAME IS WORKING BUT HAS ISSUES")
    print("   → Needs optimization")
print("="*80)
