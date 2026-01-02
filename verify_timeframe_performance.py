"""
Comprehensive timeframe performance comparison
Verifies which timeframe is truly performing best
"""

import pandas as pd
import json
import numpy as np

print("="*80)
print("TIMEFRAME PERFORMANCE VERIFICATION")
print("="*80)

timeframes = ['5m', '1h', '12h', '24h']
results = {}

for tf in timeframes:
    print(f"\n{'='*80}")
    print(f"ANALYZING {tf.upper()} TIMEFRAME")
    print(f"{'='*80}")
    
    try:
        # Determine file paths
        if tf == '5m':
            equity_path = 'paper_trading_outputs/5m/sheets_fallback/equity.csv'
            exec_path = 'paper_trading_outputs/5m/sheets_fallback/executions_paper.csv'
            signals_path = 'paper_trading_outputs/5m/sheets_fallback/signals.csv'
        elif tf == '1h':
            equity_path = 'paper_trading_outputs/1h/sheets_fallback/equity_1h.csv'
            exec_path = 'paper_trading_outputs/1h/sheets_fallback/executions_from_5m_agg.csv'
            signals_path = 'paper_trading_outputs/1h/sheets_fallback/signals_1h.csv'
        elif tf == '12h':
            equity_path = 'paper_trading_outputs/12h/sheets_fallback/equity_12h.csv'
            exec_path = 'paper_trading_outputs/12h/sheets_fallback/executions_from_5m_agg.csv'
            signals_path = 'paper_trading_outputs/12h/sheets_fallback/signals_12h.csv'
        else:  # 24h
            equity_path = 'paper_trading_outputs/24h/sheets_fallback/equity_24h.csv'
            exec_path = 'paper_trading_outputs/24h/sheets_fallback/executions_paper.csv'
            signals_path = 'paper_trading_outputs/24h/sheets_fallback/signals.csv'
        
        # Load equity
        equity_df = pd.read_csv(equity_path)
        start_equity = equity_df.iloc[0]['equity']
        current_equity = equity_df.iloc[-1]['equity']
        total_return = ((current_equity / start_equity) - 1) * 100
        
        # Load executions
        exec_df = pd.read_csv(exec_path)
        num_trades = len(exec_df)
        
        # Extract PnL data
        pnls = []
        for idx, row in exec_df.iterrows():
            try:
                raw_data = json.loads(row['raw'])
                pnl = raw_data.get('realized_pnl', 0)
                pnls.append(pnl)
            except:
                pass
        
        # Calculate metrics
        total_pnl = sum(pnls) if pnls else 0
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        win_rate = len(wins) / len(pnls) * 100 if pnls else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        expectancy = np.mean(pnls) if pnls else 0
        
        # Load signals
        signals_df = pd.read_csv(signals_path)
        num_signals = len(signals_df)
        exec_rate = (num_trades / num_signals * 100) if num_signals > 0 else 0
        
        # Store results
        results[tf] = {
            'start_equity': start_equity,
            'current_equity': current_equity,
            'total_return_pct': total_return,
            'total_pnl': total_pnl,
            'num_trades': num_trades,
            'num_signals': num_signals,
            'exec_rate_pct': exec_rate,
            'win_rate_pct': win_rate,
            'num_wins': len(wins),
            'num_losses': len(losses),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expectancy': expectancy
        }
        
        # Print summary
        print(f"\nEQUITY:")
        print(f"  Start:           ${start_equity:,.2f}")
        print(f"  Current:         ${current_equity:,.2f}")
        print(f"  Total Return:    {total_return:+.2f}%")
        print(f"  Total P&L:       ${total_pnl:+.2f}")
        
        print(f"\nTRADING ACTIVITY:")
        print(f"  Signals:         {num_signals}")
        print(f"  Executions:      {num_trades}")
        print(f"  Execution Rate:  {exec_rate:.1f}%")
        
        print(f"\nPERFORMANCE:")
        print(f"  Wins:            {len(wins)}")
        print(f"  Losses:          {len(losses)}")
        print(f"  Win Rate:        {win_rate:.1f}%")
        print(f"  Avg Win:         ${avg_win:+.2f}")
        print(f"  Avg Loss:        ${avg_loss:+.2f}")
        print(f"  Expectancy:      ${expectancy:+.4f}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results[tf] = None

# FINAL COMPARISON
print(f"\n{'='*80}")
print("FINAL COMPARISON - RANKED BY TOTAL RETURN")
print(f"{'='*80}\n")

# Create comparison table
comparison = []
for tf, data in results.items():
    if data:
        comparison.append({
            'Timeframe': tf,
            'Return %': data['total_return_pct'],
            'P&L $': data['total_pnl'],
            'Trades': data['num_trades'],
            'Win Rate %': data['win_rate_pct'],
            'Expectancy $': data['expectancy'],
            'Exec Rate %': data['exec_rate_pct']
        })

# Sort by return
comparison_df = pd.DataFrame(comparison)
comparison_df = comparison_df.sort_values('Return %', ascending=False)

print(comparison_df.to_string(index=False))

print(f"\n{'='*80}")
print("VERDICT")
print(f"{'='*80}\n")

best_tf = comparison_df.iloc[0]['Timeframe']
best_return = comparison_df.iloc[0]['Return %']
best_pnl = comparison_df.iloc[0]['P&L $']

print(f"🏆 BEST PERFORMING TIMEFRAME: {best_tf.upper()}")
print(f"   Return: {best_return:+.2f}%")
print(f"   Total P&L: ${best_pnl:+.2f}")
print(f"   Trades: {int(comparison_df.iloc[0]['Trades'])}")
print(f"   Win Rate: {comparison_df.iloc[0]['Win Rate %']:.1f}%")
print(f"   Expectancy: ${comparison_df.iloc[0]['Expectancy $']:+.4f}")

print(f"\n{'='*80}\n")

# Save results
with open('timeframe_comparison_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Results saved to: timeframe_comparison_results.json")
