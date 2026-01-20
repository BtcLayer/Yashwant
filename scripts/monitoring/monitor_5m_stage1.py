"""
Stage 1 Monitoring Script
Track performance after raising CONF_MIN from 0.55 to 0.60
"""

import pandas as pd
import json
from datetime import datetime, timedelta

print("="*80)
print("STAGE 1 MONITORING: CONF_MIN = 0.60")
print("="*80)

# Load current data
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
exec_df['ts'] = pd.to_datetime(exec_df['ts_iso'], errors='coerce')

# Define Stage 1 start time (now)
stage1_start = datetime.now() - timedelta(hours=48)  # Look back 48 hours

# Filter for Stage 1 trades
stage1_trades = exec_df[exec_df['ts'] > stage1_start].copy()

print(f"\nStage 1 Start Time: {stage1_start}")
print(f"Current Time: {datetime.now()}")
print(f"Trades since Stage 1: {len(stage1_trades)}")

if len(stage1_trades) == 0:
    print("\n⚠️  NO TRADES YET")
    print("   Status: Waiting for first trade with CONF_MIN = 0.60")
    print("   Action: Continue monitoring")
    print("\n   Rollback condition: No trades for 48 hours")
else:
    # Extract PnL
    pnl_list = []
    for idx, row in stage1_trades.iterrows():
        try:
            raw_data = json.loads(row['raw'])
            pnl_list.append({
                'ts': row['ts'],
                'side': row['side'],
                'realized_pnl': float(raw_data.get('realized_pnl', 0)),
                'fee': float(raw_data.get('fee', 0)),
                'impact': float(raw_data.get('impact', 0))
            })
        except:
            pass
    
    if len(pnl_list) > 0:
        pnl_df = pd.DataFrame(pnl_list)
        
        # Calculate metrics
        total_trades = len(pnl_df)
        total_pnl = pnl_df['realized_pnl'].sum()
        avg_pnl = pnl_df['realized_pnl'].mean()
        wins = len(pnl_df[pnl_df['realized_pnl'] > 0])
        win_rate = wins / total_trades if total_trades > 0 else 0
        
        print(f"\n{'STAGE 1 PERFORMANCE':-^80}")
        print(f"Total Trades:        {total_trades}")
        print(f"Win Rate:            {win_rate*100:.1f}%")
        print(f"Total PnL:           ${total_pnl:.2f}")
        print(f"Avg PnL/Trade:       ${avg_pnl:.4f}")
        print(f"Expectancy:          ${avg_pnl:.4f}")
        
        # Compare to baseline
        baseline_expectancy = -5.19
        improvement = avg_pnl - baseline_expectancy
        
        print(f"\n{'COMPARISON TO BASELINE':-^80}")
        print(f"Baseline Expectancy: ${baseline_expectancy:.4f}")
        print(f"Stage 1 Expectancy:  ${avg_pnl:.4f}")
        print(f"Improvement:         ${improvement:.4f}")
        
        if improvement > 0:
            print(f"\n✓ IMPROVEMENT DETECTED")
            print(f"  Expectancy improved by ${improvement:.4f} per trade")
        else:
            print(f"\n⚠️  NO IMPROVEMENT YET")
            print(f"  Expectancy worse by ${abs(improvement):.4f} per trade")
        
        # Decision logic
        print(f"\n{'DECISION LOGIC':-^80}")
        if total_trades < 5:
            print("Status: INSUFFICIENT DATA")
            print("Action: Continue monitoring (need at least 5 trades)")
        elif avg_pnl > -3.00:
            print("Status: ✓ SUCCESS - Expectancy improved")
            print("Action: Continue to Stage 2 after 48 hours")
        elif avg_pnl < baseline_expectancy:
            print("Status: ⚠️  DEGRADATION - Expectancy worse")
            print("Action: Consider rollback if trend continues")
        else:
            print("Status: NEUTRAL - No significant change")
            print("Action: Continue monitoring")

# Save monitoring results
monitoring_data = {
    'stage1_start': stage1_start.isoformat(),
    'current_time': datetime.now().isoformat(),
    'trades_count': int(len(stage1_trades)),
    'baseline_expectancy': -5.19,
    'stage1_expectancy': float(avg_pnl) if len(pnl_list) > 0 else None
}

with open('stage1_monitoring.json', 'w') as f:
    json.dump(monitoring_data, f, indent=2)

print(f"\n{'NEXT STEPS':-^80}")
print("1. Run this script every 12 hours")
print("2. At 48-hour mark, make go/no-go decision")
print("3. If no trades: Rollback to CONF_MIN = 0.55")
print("4. If expectancy improved: Proceed to Stage 2")
print("5. If expectancy worse: Rollback and investigate")

print("\n" + "="*80)
print("Monitoring data saved to: stage1_monitoring.json")
print("="*80)
