"""
ROOT CAUSE ANALYSIS: 0% Win Rate Investigation
Deep diagnostic to identify why ALL timeframes are losing
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

print("="*80)
print("ROOT CAUSE ANALYSIS: 0% WIN RATE INVESTIGATION")
print("="*80)
print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Focus on 24h (most data)
print("Analyzing 24h timeframe (most complete data)...\n")

# Load data
exec_df = pd.read_csv('paper_trading_outputs/24h/sheets_fallback/executions_paper.csv')
signals_df = pd.read_csv('paper_trading_outputs/24h/sheets_fallback/signals.csv')

print(f"Loaded {len(exec_df)} executions and {len(signals_df)} signals\n")

# Parse timestamps
exec_df['ts_dt'] = pd.to_datetime(exec_df['ts_iso'], errors='coerce')
signals_df['ts_dt'] = pd.to_datetime(signals_df['ts_iso'], errors='coerce')

# Extract detailed trade data
print("="*80)
print("HYPOTHESIS 1: SIGNAL INVERSION (BUY/SELL REVERSED)")
print("="*80)

trades = []
for idx, row in exec_df.iterrows():
    try:
        raw = json.loads(row['raw'])
        trades.append({
            'ts': row['ts_dt'],
            'side': row['side'],
            'qty': row['qty'],
            'entry_price': row['mid_price'],
            'realized_pnl': raw.get('realized_pnl', 0),
            'fee': raw.get('fee', 0),
            'impact': raw.get('impact', 0)
        })
    except:
        pass

trades_df = pd.DataFrame(trades)

# Analyze if BUY trades lose when price goes up (signal inversion)
print("\nAnalyzing trade direction vs P&L correlation...\n")

buy_trades = trades_df[trades_df['side'] == 'BUY']
sell_trades = trades_df[trades_df['side'] == 'SELL']

print(f"BUY Trades:  {len(buy_trades)}")
print(f"  Avg P&L: ${buy_trades['realized_pnl'].mean():.2f}")
print(f"  Total P&L: ${buy_trades['realized_pnl'].sum():.2f}")

print(f"\nSELL Trades: {len(sell_trades)}")
print(f"  Avg P&L: ${sell_trades['realized_pnl'].mean():.2f}")
print(f"  Total P&L: ${sell_trades['realized_pnl'].sum():.2f}")

# Check if one direction is significantly worse
if len(buy_trades) > 0 and len(sell_trades) > 0:
    buy_avg = buy_trades['realized_pnl'].mean()
    sell_avg = sell_trades['realized_pnl'].mean()
    
    if buy_avg < 0 and sell_avg < 0:
        print("\n⚠️  BOTH DIRECTIONS LOSING - Not simple signal inversion")
    elif abs(buy_avg) > abs(sell_avg) * 2:
        print(f"\n🔴 BUY trades losing {abs(buy_avg/sell_avg):.1f}x worse than SELL")
        print("   Possible directional bias or BUY signal issue")
    elif abs(sell_avg) > abs(buy_avg) * 2:
        print(f"\n🔴 SELL trades losing {abs(sell_avg/buy_avg):.1f}x worse than BUY")
        print("   Possible directional bias or SELL signal issue")

# HYPOTHESIS 2: COST ANALYSIS
print("\n" + "="*80)
print("HYPOTHESIS 2: TRANSACTION COSTS DESTROYING EDGE")
print("="*80)

total_pnl = trades_df['realized_pnl'].sum()
total_fees = trades_df['fee'].sum()
total_impact = trades_df['impact'].sum()
total_costs = total_fees + total_impact

gross_pnl = total_pnl + total_costs

print(f"\nGross P&L (before costs): ${gross_pnl:.2f}")
print(f"Total Fees:               ${total_fees:.2f}")
print(f"Total Impact:             ${total_impact:.2f}")
print(f"Total Costs:              ${total_costs:.2f}")
print(f"Net P&L (after costs):    ${total_pnl:.2f}")

if gross_pnl > 0:
    print(f"\n✅ GROSS P&L IS POSITIVE!")
    print(f"   Costs eating {(total_costs/gross_pnl)*100:.1f}% of gross profits")
    print(f"   🎯 SOLUTION: Reduce trading frequency or lower costs")
else:
    print(f"\n🔴 GROSS P&L IS NEGATIVE (${gross_pnl:.2f})")
    print(f"   System has no edge even before costs")
    print(f"   🎯 SOLUTION: Fix signal quality, not just costs")

avg_cost_per_trade = total_costs / len(trades_df)
avg_gross_per_trade = gross_pnl / len(trades_df)

print(f"\nPer Trade Analysis:")
print(f"  Avg Gross P&L: ${avg_gross_per_trade:.2f}")
print(f"  Avg Cost:      ${avg_cost_per_trade:.2f}")
print(f"  Avg Net P&L:   ${(avg_gross_per_trade - avg_cost_per_trade):.2f}")

# HYPOTHESIS 3: SIGNAL QUALITY
print("\n" + "="*80)
print("HYPOTHESIS 3: SIGNAL QUALITY ANALYSIS")
print("="*80)

# Try to extract confidence/alpha from signals
print("\nAnalyzing signal metadata...")

signal_data = []
for idx, row in signals_df.iterrows():
    try:
        ts = row['ts_dt']
        # Try to find matching execution
        matching_exec = exec_df[exec_df['ts_dt'] == ts]
        
        if len(matching_exec) > 0:
            exec_row = matching_exec.iloc[0]
            raw = json.loads(exec_row['raw'])
            
            signal_data.append({
                'ts': ts,
                'side': exec_row['side'],
                'realized_pnl': raw.get('realized_pnl', 0)
            })
    except:
        pass

if len(signal_data) > 0:
    sig_df = pd.DataFrame(signal_data)
    print(f"\nMatched {len(sig_df)} signals to executions")
    print(f"Avg P&L per matched signal: ${sig_df['realized_pnl'].mean():.2f}")
else:
    print("\n⚠️  Could not match signals to executions")

# HYPOTHESIS 4: HOLDING PERIOD ANALYSIS
print("\n" + "="*80)
print("HYPOTHESIS 4: HOLDING PERIOD ANALYSIS")
print("="*80)

# Sort trades by time
trades_df = trades_df.sort_values('ts')

# Calculate time between trades (proxy for holding period)
if len(trades_df) > 1:
    trades_df['time_to_next'] = trades_df['ts'].diff().shift(-1)
    trades_df['hours_held'] = trades_df['time_to_next'].dt.total_seconds() / 3600
    
    avg_hold = trades_df['hours_held'].mean()
    print(f"\nAverage holding period: {avg_hold:.1f} hours ({avg_hold/24:.1f} days)")
    
    # Analyze P&L by holding period
    short_holds = trades_df[trades_df['hours_held'] < avg_hold]
    long_holds = trades_df[trades_df['hours_held'] >= avg_hold]
    
    if len(short_holds) > 0:
        print(f"\nShort holds (<{avg_hold:.1f}h): {len(short_holds)} trades")
        print(f"  Avg P&L: ${short_holds['realized_pnl'].mean():.2f}")
    
    if len(long_holds) > 0:
        print(f"\nLong holds (>={avg_hold:.1f}h): {len(long_holds)} trades")
        print(f"  Avg P&L: ${long_holds['realized_pnl'].mean():.2f}")

# SUMMARY AND DIAGNOSIS
print("\n" + "="*80)
print("ROOT CAUSE DIAGNOSIS")
print("="*80)

findings = []

# Finding 1: Cost vs Edge
if gross_pnl > 0:
    findings.append("1. 🟡 COSTS DESTROYING EDGE")
    findings.append(f"   Gross P&L: ${gross_pnl:.2f} → Net P&L: ${total_pnl:.2f}")
    findings.append(f"   Costs consuming {abs(total_costs/gross_pnl)*100:.1f}% of gross profits")
    findings.append(f"   ACTION: Reduce trade frequency or negotiate lower fees")
else:
    findings.append("1. 🔴 NO EDGE EVEN BEFORE COSTS")
    findings.append(f"   Gross P&L: ${gross_pnl:.2f} (negative)")
    findings.append(f"   System predictions are not working")
    findings.append(f"   ACTION: Fix model or signal generation logic")

# Finding 2: Directional bias
if len(buy_trades) > 0 and len(sell_trades) > 0:
    buy_pnl = buy_trades['realized_pnl'].sum()
    sell_pnl = sell_trades['realized_pnl'].sum()
    
    if abs(buy_pnl) > abs(sell_pnl) * 1.5:
        findings.append("2. 🔴 DIRECTIONAL BIAS DETECTED")
        findings.append(f"   BUY P&L: ${buy_pnl:.2f} vs SELL P&L: ${sell_pnl:.2f}")
        findings.append(f"   ACTION: Investigate BUY signal quality")
    elif abs(sell_pnl) > abs(buy_pnl) * 1.5:
        findings.append("2. 🔴 DIRECTIONAL BIAS DETECTED")
        findings.append(f"   SELL P&L: ${sell_pnl:.2f} vs BUY P&L: ${buy_pnl:.2f}")
        findings.append(f"   ACTION: Investigate SELL signal quality")

# Finding 3: Win rate
findings.append("3. 🔴 ZERO WIN RATE")
findings.append(f"   0 wins out of {len(trades_df)} trades")
findings.append(f"   This is statistically impossible for a random system")
findings.append(f"   ACTION: Check for systematic execution errors")

print()
for finding in findings:
    print(finding)

# Save results
results = {
    'analysis_time': datetime.now().isoformat(),
    'total_trades': len(trades_df),
    'gross_pnl': float(gross_pnl),
    'total_costs': float(total_costs),
    'net_pnl': float(total_pnl),
    'costs_as_pct_of_gross': float(abs(total_costs/gross_pnl)*100) if gross_pnl != 0 else None,
    'buy_trades': len(buy_trades),
    'buy_pnl': float(buy_trades['realized_pnl'].sum()) if len(buy_trades) > 0 else 0,
    'sell_trades': len(sell_trades),
    'sell_pnl': float(sell_trades['realized_pnl'].sum()) if len(sell_trades) > 0 else 0,
    'avg_cost_per_trade': float(avg_cost_per_trade),
    'avg_gross_per_trade': float(avg_gross_per_trade),
    'diagnosis': findings
}

with open('root_cause_analysis.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n" + "="*80)
print("Analysis saved to: root_cause_analysis.json")
print("="*80)
