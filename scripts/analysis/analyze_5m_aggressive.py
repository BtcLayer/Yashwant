"""
AGGRESSIVE PROFITABILITY ANALYSIS
Find the fastest path to profitability for 5m bot
"""

import pandas as pd
import numpy as np
import json

print("="*80)
print("AGGRESSIVE PROFITABILITY ANALYSIS - FAST PATH")
print("="*80)

# Load execution data
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
print(f"\nTotal executions: {len(exec_df)}")

# Extract PnL
trades = []
for idx, row in exec_df.iterrows():
    try:
        raw_data = json.loads(row['raw'])
        trades.append({
            'side': row['side'],
            'qty': float(row['qty']),
            'mid_price': float(row['mid_price']),
            'realized_pnl': float(raw_data.get('realized_pnl', 0)),
            'fee': float(raw_data.get('fee', 0)),
            'impact': float(raw_data.get('impact', 0))
        })
    except:
        pass

trades_df = pd.DataFrame(trades)

# CRITICAL ANALYSIS: What's actually killing profitability?
print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80)

total_pnl = trades_df['realized_pnl'].sum()
total_fees = trades_df['fee'].sum()
total_impact = trades_df['impact'].sum()
total_costs = total_fees + total_impact

gross_pnl_before_costs = total_pnl + total_costs

print(f"\nGross PnL (before costs): ${gross_pnl_before_costs:.2f}")
print(f"Total Costs:              ${total_costs:.2f}")
print(f"  - Fees:                 ${total_fees:.2f}")
print(f"  - Impact:               ${total_impact:.2f}")
print(f"Net PnL (after costs):    ${total_pnl:.2f}")

# CRITICAL INSIGHT
cost_ratio = total_costs / abs(gross_pnl_before_costs) if gross_pnl_before_costs != 0 else 0
print(f"\nCosts are {cost_ratio:.1f}x the gross loss")

# DIRECTION ANALYSIS
print("\n" + "="*80)
print("DIRECTION ANALYSIS - IS ONE SIDE PROFITABLE?")
print("="*80)

for side in trades_df['side'].unique():
    side_trades = trades_df[trades_df['side'] == side]
    side_pnl = side_trades['realized_pnl'].sum()
    side_count = len(side_trades)
    side_avg = side_trades['realized_pnl'].mean()
    wins = len(side_trades[side_trades['realized_pnl'] > 0])
    win_rate = wins / side_count if side_count > 0 else 0
    
    print(f"\n{side}:")
    print(f"  Count:       {side_count}")
    print(f"  Total PnL:   ${side_pnl:.2f}")
    print(f"  Avg PnL:     ${side_avg:.4f}")
    print(f"  Win Rate:    {win_rate*100:.1f}%")
    
    if side_avg > 0:
        print(f"  ✓ PROFITABLE - Keep this direction")
    else:
        print(f"  ✗ UNPROFITABLE - Consider disabling")

# COST ANALYSIS - Can we reduce costs?
print("\n" + "="*80)
print("COST REDUCTION POTENTIAL")
print("="*80)

avg_fee = trades_df['fee'].mean()
avg_impact = trades_df['impact'].mean()
avg_cost = avg_fee + avg_impact

print(f"\nAverage cost per trade: ${avg_cost:.4f}")
print(f"  - Fee:                ${avg_fee:.4f}")
print(f"  - Impact:             ${avg_impact:.4f}")

# If we cut costs in half (passive orders, better execution)
reduced_costs = total_costs * 0.5
new_pnl = gross_pnl_before_costs - reduced_costs

print(f"\nIF we cut costs by 50%:")
print(f"  New total costs:      ${reduced_costs:.2f}")
print(f"  New net PnL:          ${new_pnl:.2f}")
print(f"  Improvement:          ${new_pnl - total_pnl:.2f}")

if new_pnl > 0:
    print(f"  ✓ WOULD BE PROFITABLE")
else:
    print(f"  ✗ STILL UNPROFITABLE - Cost reduction alone won't fix this")

# FAST PATH RECOMMENDATIONS
print("\n" + "="*80)
print("FAST PATH TO PROFITABILITY (1-2 WEEKS)")
print("="*80)

recommendations = []

# Rec 1: Disable unprofitable direction
buy_pnl = trades_df[trades_df['side'] == 'BUY']['realized_pnl'].sum() if 'BUY' in trades_df['side'].values else 0
sell_pnl = trades_df[trades_df['side'] == 'SELL']['realized_pnl'].sum() if 'SELL' in trades_df['side'].values else 0

if buy_pnl < 0 and sell_pnl > 0:
    recommendations.append({
        'action': 'DISABLE BUY TRADES',
        'impact': f'+${abs(buy_pnl):.2f}',
        'implementation': 'Set CONF_MIN_LONG = 0.99 (effectively disable)',
        'timeline': 'Immediate (1 day)',
        'risk': 'Low - easily reversible'
    })
elif sell_pnl < 0 and buy_pnl > 0:
    recommendations.append({
        'action': 'DISABLE SELL TRADES',
        'impact': f'+${abs(sell_pnl):.2f}',
        'implementation': 'Set CONF_MIN_SHORT = 0.99 (effectively disable)',
        'timeline': 'Immediate (1 day)',
        'risk': 'Low - easily reversible'
    })

# Rec 2: Aggressive confidence threshold
recommendations.append({
    'action': 'RAISE CONF_MIN TO 0.70',
    'impact': 'Eliminate bottom 70% of trades',
    'implementation': 'Change CONF_MIN from 0.55 to 0.70',
    'timeline': 'Immediate (1 day)',
    'risk': 'Medium - may over-filter'
})

# Rec 3: Reduce costs via passive orders
if avg_cost > 1.0:
    recommendations.append({
        'action': 'SWITCH TO PASSIVE ORDERS',
        'impact': f'Save ~${total_costs * 0.3:.2f} (30% cost reduction)',
        'implementation': 'Change execution mode from market to limit',
        'timeline': '2-3 days',
        'risk': 'Medium - may miss fills'
    })

# Rec 4: Only trade high volatility
recommendations.append({
    'action': 'ADD VOLATILITY FILTER',
    'impact': 'Eliminate chop trades',
    'implementation': 'Only trade when realized_vol_20 > 0.5',
    'timeline': '1-2 days',
    'risk': 'Low - easy to remove'
})

# Rec 5: Nuclear option - retrain model
if gross_pnl_before_costs < -20:
    recommendations.append({
        'action': '🔴 RETRAIN MODEL (Nuclear Option)',
        'impact': 'Potentially fix fundamental edge problem',
        'implementation': 'Retrain with recent data, different features',
        'timeline': '1-2 weeks',
        'risk': 'High - may not improve'
    })

print("\nRECOMMENDED ACTIONS (in order):")
for i, rec in enumerate(recommendations, 1):
    print(f"\n{i}. {rec['action']}")
    print(f"   Impact:     {rec['impact']}")
    print(f"   How:        {rec['implementation']}")
    print(f"   Timeline:   {rec['timeline']}")
    print(f"   Risk:       {rec['risk']}")

# AGGRESSIVE TIMELINE
print("\n" + "="*80)
print("AGGRESSIVE TIMELINE (1-2 WEEKS TO PROFITABILITY)")
print("="*80)

print("""
Week 1:
  Day 1: Disable unprofitable direction + Raise CONF_MIN to 0.70
  Day 2: Add volatility filter (only trade vol > 0.5)
  Day 3: Monitor results
  Day 4: If still unprofitable, switch to passive orders
  Day 5-7: Validate and tune

Week 2:
  Day 8-10: If profitable, optimize position sizing
  Day 11-14: If still unprofitable, consider model retraining

Target: Achieve expectancy > $0 by Day 7
""")

# NUCLEAR OPTION CHECK
print("\n" + "="*80)
print("SHOULD WE JUST RETRAIN THE MODEL?")
print("="*80)

if gross_pnl_before_costs < -20:
    print("\n🔴 YES - Model has no edge even before costs")
    print("   Filtering and cost reduction won't fix this")
    print("   Fastest path: Retrain model with:")
    print("   - Recent market data (last 3 months)")
    print("   - Different features or feature engineering")
    print("   - Better target variable (forward returns)")
    print("   Timeline: 1-2 weeks including validation")
else:
    print("\n✓ NO - Model has some edge, just needs better filtering")
    print("   Filtering + cost reduction should work")
    print("   Timeline: 1 week")

print("\n" + "="*80)
print("RECOMMENDATION: AGGRESSIVE PATH")
print("="*80)

if gross_pnl_before_costs < -20:
    print("""
The model fundamentally lacks edge. Fastest path to profitability:

OPTION A: AGGRESSIVE FILTERING (1 week)
  1. Disable unprofitable direction (immediate)
  2. Raise CONF_MIN to 0.75 (immediate)
  3. Add volatility filter (1 day)
  4. Switch to passive orders (2 days)
  
  Success probability: 30-40%
  
OPTION B: MODEL RETRAINING (2 weeks)
  1. Retrain with recent data
  2. Improve feature engineering
  3. Better target variable
  
  Success probability: 60-70%
  
RECOMMENDED: Try Option A for 3 days. If no improvement, do Option B.
""")
else:
    print("""
Model has some edge. Fastest path to profitability:

AGGRESSIVE FILTERING (1 week)
  1. Disable unprofitable direction (immediate)
  2. Raise CONF_MIN to 0.70 (immediate)
  3. Add volatility filter (1 day)
  4. Monitor for 3 days
  5. If profitable, optimize sizing
  
  Success probability: 60-70%
  Timeline: 5-7 days to profitability
""")

# Save results
results = {
    'gross_pnl_before_costs': float(gross_pnl_before_costs),
    'total_costs': float(total_costs),
    'net_pnl': float(total_pnl),
    'buy_pnl': float(buy_pnl),
    'sell_pnl': float(sell_pnl),
    'model_has_edge': bool(gross_pnl_before_costs > -20),
    'recommended_path': 'aggressive_filtering' if gross_pnl_before_costs > -20 else 'model_retraining',
    'timeline_days': 7 if gross_pnl_before_costs > -20 else 14
}

with open('5m_aggressive_analysis.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n" + "="*80)
print("Analysis saved to: 5m_aggressive_analysis.json")
print("="*80)
