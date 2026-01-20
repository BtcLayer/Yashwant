"""
Quick status check for all timeframes
Shows current equity, last trade, signal counts
"""

import pandas as pd
import json
from datetime import datetime

print("="*80)
print("MULTI-TIMEFRAME TRADING STATUS")
print("="*80)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

timeframes = {
    '1h': {
        'equity': 'paper_trading_outputs/1h/sheets_fallback/equity_1h.csv',
        'executions': 'paper_trading_outputs/1h/sheets_fallback/executions_from_5m_agg.csv',
        'signals': 'paper_trading_outputs/1h/sheets_fallback/signals_1h.csv'
    },
    '12h': {
        'equity': 'paper_trading_outputs/12h/sheets_fallback/equity_12h.csv',
        'executions': 'paper_trading_outputs/12h/sheets_fallback/executions_from_5m_agg.csv',
        'signals': 'paper_trading_outputs/12h/sheets_fallback/signals_12h.csv'
    },
    '24h': {
        'equity': 'paper_trading_outputs/24h/sheets_fallback/equity_24h.csv',
        'executions': 'paper_trading_outputs/24h/sheets_fallback/executions_paper.csv',
        'signals': 'paper_trading_outputs/24h/sheets_fallback/signals.csv'
    }
}

for tf, paths in timeframes.items():
    print(f"\n{'='*80}")
    print(f"{tf.upper()} TIMEFRAME STATUS")
    print(f"{'='*80}")
    
    try:
        # Load equity
        equity_df = pd.read_csv(paths['equity'])
        if len(equity_df) > 0:
            latest_equity = equity_df.iloc[-1]
            print(f"\n📊 EQUITY STATUS:")
            print(f"  Current Equity:    ${latest_equity.get('equity', 10000):.2f}")
            print(f"  Starting Equity:   ${equity_df.iloc[0].get('equity', 10000):.2f}")
            print(f"  Total Return:      {((latest_equity.get('equity', 10000) / equity_df.iloc[0].get('equity', 10000)) - 1) * 100:.2f}%")
            print(f"  Last Update:       {latest_equity.get('ts_iso', 'N/A')}")
            print(f"  Equity Records:    {len(equity_df)}")
        else:
            print(f"\n⚠️  No equity data available")
    except Exception as e:
        print(f"\n❌ Error loading equity: {e}")
    
    try:
        # Load executions
        exec_df = pd.read_csv(paths['executions'])
        print(f"\n📈 EXECUTION STATUS:")
        print(f"  Total Executions:  {len(exec_df)}")
        
        if len(exec_df) > 0:
            latest_exec = exec_df.iloc[-1]
            print(f"  Last Trade:        {latest_exec.get('ts_iso', 'N/A')}")
            print(f"  Last Side:         {latest_exec.get('side', 'N/A')}")
            print(f"  Last Qty:          {latest_exec.get('qty', 0):.6f} BTC")
            print(f"  Last Price:        ${latest_exec.get('mid_price', 0):.2f}")
            
            # Try to extract PnL from raw field
            try:
                if 'raw' in exec_df.columns:
                    raw_data = json.loads(latest_exec['raw'])
                    realized_pnl = raw_data.get('realized_pnl', 0)
                    print(f"  Last Trade PnL:    ${realized_pnl:.2f}")
            except:
                pass
        else:
            print(f"  ⚠️  No executions yet")
    except Exception as e:
        print(f"\n❌ Error loading executions: {e}")
    
    try:
        # Load signals
        signals_df = pd.read_csv(paths['signals'])
        print(f"\n🎯 SIGNAL STATUS:")
        print(f"  Total Signals:     {len(signals_df)}")
        
        if len(signals_df) > 0:
            exec_count = len(exec_df) if 'exec_df' in locals() else 0
            exec_rate = (exec_count / len(signals_df)) * 100 if len(signals_df) > 0 else 0
            print(f"  Execution Rate:    {exec_rate:.1f}%")
            print(f"  Rejection Rate:    {100 - exec_rate:.1f}%")
            
            latest_signal = signals_df.iloc[-1]
            print(f"  Last Signal:       {latest_signal.get('ts_iso', 'N/A')}")
        else:
            print(f"  ⚠️  No signals generated")
    except Exception as e:
        print(f"\n❌ Error loading signals: {e}")

print(f"\n{'='*80}")
print("STATUS CHECK COMPLETE")
print(f"{'='*80}\n")

# Summary comparison
print("\n" + "="*80)
print("CROSS-TIMEFRAME SUMMARY")
print("="*80)
print(f"\n{'Timeframe':<12} {'Equity':<12} {'Return':<10} {'Trades':<8} {'Signals':<10} {'Exec Rate':<10}")
print("-" * 80)

for tf, paths in timeframes.items():
    try:
        equity_df = pd.read_csv(paths['equity'])
        exec_df = pd.read_csv(paths['executions'])
        signals_df = pd.read_csv(paths['signals'])
        
        current_equity = equity_df.iloc[-1].get('equity', 10000) if len(equity_df) > 0 else 10000
        start_equity = equity_df.iloc[0].get('equity', 10000) if len(equity_df) > 0 else 10000
        ret = ((current_equity / start_equity) - 1) * 100
        trades = len(exec_df)
        signals = len(signals_df)
        exec_rate = (trades / signals * 100) if signals > 0 else 0
        
        print(f"{tf:<12} ${current_equity:<11.2f} {ret:>8.2f}% {trades:<8} {signals:<10} {exec_rate:>8.1f}%")
    except:
        print(f"{tf:<12} {'ERROR':<12} {'N/A':<10} {'N/A':<8} {'N/A':<10} {'N/A':<10}")

print("\n")
