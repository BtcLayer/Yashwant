"""
5m Trading System - Simplified Profitability Analysis
Focus on actionable insights for profitability improvement
"""

import pandas as pd
import numpy as np
import json

print("="*80)
print("5M TRADING SYSTEM PROFITABILITY ANALYSIS")
print("="*80)

# Load execution data
print("\nLoading execution data...")
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
print(f"Total executions: {len(exec_df)}")

# Extract PnL from raw JSON
print("\nExtracting PnL data...")
pnl_list = []
for idx, row in exec_df.iterrows():
    try:
        raw_data = json.loads(row['raw'])
        pnl_list.append({
            'realized_pnl': float(raw_data.get('realized_pnl', 0)),
            'fee': float(raw_data.get('fee', 0)),
            'impact': float(raw_data.get('impact', 0)),
            'side': row['side'],
            'qty': float(row['qty']),
            'mid_price': float(row['mid_price'])
        })
    except Exception as e:
        print(f"  Warning: Could not parse row {idx}: {e}")
        
pnl_df = pd.DataFrame(pnl_list)

# BASELINE METRICS
print("\n" + "="*80)
print("BASELINE PERFORMANCE METRICS")
print("="*80)

total_trades = len(pnl_df)
wins = pnl_df[pnl_df['realized_pnl'] > 0]
losses = pnl_df[pnl_df['realized_pnl'] < 0]

win_count = len(wins)
loss_count = len(losses)
win_rate = win_count / total_trades if total_trades > 0 else 0

avg_win = wins['realized_pnl'].mean() if win_count > 0 else 0
avg_loss = losses['realized_pnl'].mean() if loss_count > 0 else 0
payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

total_pnl = pnl_df['realized_pnl'].sum()
avg_pnl_per_trade = pnl_df['realized_pnl'].mean()

# Expectancy
expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

# Profit factor
gross_profit = wins['realized_pnl'].sum() if win_count > 0 else 0
gross_loss = abs(losses['realized_pnl'].sum()) if loss_count > 0 else 0
profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

# Costs
total_fees = pnl_df['fee'].sum()
total_impact = pnl_df['impact'].sum()
total_costs = total_fees + total_impact

print(f"\nTrade Count:         {total_trades}")
print(f"Wins:                {win_count} ({win_rate*100:.1f}%)")
print(f"Losses:              {loss_count} ({(1-win_rate)*100:.1f}%)")
print(f"\nAverage Win:         ${avg_win:.4f}")
print(f"Average Loss:        ${avg_loss:.4f}")
print(f"Payoff Ratio:        {payoff_ratio:.2f}x")
print(f"\nExpectancy/Trade:    ${expectancy:.4f}")
print(f"Total PnL:           ${total_pnl:.2f}")
print(f"Avg PnL/Trade:       ${avg_pnl_per_trade:.4f}")
print(f"Profit Factor:       {profit_factor:.2f}")
print(f"\nTotal Costs:         ${total_costs:.2f}")
print(f"  Fees:              ${total_fees:.2f}")
print(f"  Impact:            ${total_impact:.2f}")
print(f"Avg Cost/Trade:      ${total_costs/total_trades:.4f}")

# DIAGNOSIS
print("\n" + "="*80)
print("PROFITABILITY DIAGNOSIS")
print("="*80)

# Calculate what PnL would be without costs
gross_pnl_before_costs = total_pnl + total_costs

print(f"\nGross PnL (before costs):  ${gross_pnl_before_costs:.2f}")
print(f"Costs:                     ${total_costs:.2f}")
print(f"Net PnL (after costs):     ${total_pnl:.2f}")

if gross_pnl_before_costs > 0 and total_pnl < 0:
    print(f"\n🔴 CRITICAL: System is PROFITABLE before costs but UNPROFITABLE after costs")
    print(f"   Costs are eating {(total_costs/gross_pnl_before_costs)*100:.1f}% of gross profits")
elif total_pnl < 0:
    print(f"\n🔴 CRITICAL: System has NEGATIVE edge even before costs")
    print(f"   Need to improve signal quality, not just reduce costs")

# Win rate vs payoff analysis
print(f"\n{'WIN RATE vs PAYOFF ANALYSIS':-^80}")
print(f"Current: {win_rate*100:.1f}% win rate × {payoff_ratio:.2f}x payoff")

# Calculate break-even requirements
if avg_loss != 0:
    breakeven_win_rate = abs(avg_loss) / (abs(avg_loss) + avg_win)
    print(f"Break-even win rate (at current payoff): {breakeven_win_rate*100:.1f}%")
    
if win_rate > 0:
    breakeven_payoff = (1 - win_rate) / win_rate
    print(f"Break-even payoff (at current win rate): {breakeven_payoff:.2f}x")

# Expectancy analysis
print(f"\n{'EXPECTANCY ANALYSIS':-^80}")
if expectancy < 0:
    print(f"🔴 NEGATIVE expectancy: ${expectancy:.4f} per trade")
    print(f"   Every trade loses ${abs(expectancy):.4f} on average")
    print(f"   System has NO EDGE")
elif expectancy < 0.5:
    print(f"⚠️  VERY LOW expectancy: ${expectancy:.4f} per trade")
    print(f"   Edge too small to overcome variance")
else:
    print(f"✓ Positive expectancy: ${expectancy:.4f} per trade")

# Cost efficiency
print(f"\n{'COST EFFICIENCY':-^80}")
cost_per_trade = total_costs / total_trades
print(f"Average cost per trade: ${cost_per_trade:.4f}")
print(f"Average PnL per trade:  ${avg_pnl_per_trade:.4f}")

if abs(cost_per_trade) > abs(avg_pnl_per_trade):
    print(f"🔴 Costs ({cost_per_trade:.4f}) > Avg PnL ({avg_pnl_per_trade:.4f})")
    print(f"   Costs are {(cost_per_trade/abs(avg_pnl_per_trade)):.1f}x larger than average profit")

# KEY FINDINGS
print("\n" + "="*80)
print("KEY FINDINGS")
print("="*80)

findings = []

# Finding 1: Overall profitability
if total_pnl < 0:
    findings.append("1. SYSTEM IS UNPROFITABLE")
    findings.append(f"   Total loss: ${total_pnl:.2f} over {total_trades} trades")
    
# Finding 2: Win rate
if win_rate < 0.45:
    findings.append(f"2. LOW WIN RATE ({win_rate*100:.1f}%)")
    findings.append(f"   Need either higher win rate OR much higher payoff")
elif win_rate > 0.55:
    findings.append(f"2. GOOD WIN RATE ({win_rate*100:.1f}%)")
    
# Finding 3: Payoff
if payoff_ratio < 1.2:
    findings.append(f"3. LOW PAYOFF RATIO ({payoff_ratio:.2f}x)")
    findings.append(f"   Wins barely larger than losses")
elif payoff_ratio > 2.0:
    findings.append(f"3. STRONG PAYOFF RATIO ({payoff_ratio:.2f}x)")

# Finding 4: Costs
cost_ratio = total_costs / abs(gross_pnl_before_costs) if gross_pnl_before_costs != 0 else 0
if cost_ratio > 0.5:
    findings.append(f"4. COSTS EATING PROFITS")
    findings.append(f"   Costs = {cost_ratio*100:.1f}% of gross PnL")
    
# Finding 5: Expectancy
if expectancy < 0:
    findings.append(f"5. NEGATIVE EXPECTANCY (${expectancy:.4f})")
    findings.append(f"   No statistical edge")
elif expectancy < 0.5:
    findings.append(f"5. WEAK EXPECTANCY (${expectancy:.4f})")
    findings.append(f"   Edge exists but very small")

for finding in findings:
    print(finding)

# Save results
results = {
    'total_trades': int(total_trades),
    'win_rate': float(win_rate),
    'payoff_ratio': float(payoff_ratio),
    'expectancy': float(expectancy),
    'profit_factor': float(profit_factor),
    'total_pnl': float(total_pnl),
    'total_costs': float(total_costs),
    'avg_cost_per_trade': float(cost_per_trade),
    'gross_pnl_before_costs': float(gross_pnl_before_costs)
}

with open('5m_profitability_baseline.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n" + "="*80)
print("Analysis complete. Results saved to: 5m_profitability_baseline.json")
print("="*80)
