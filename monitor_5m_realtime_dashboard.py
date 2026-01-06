"""
Real-time 5m Bot Monitor
Continuously monitors the bot and displays key metrics
"""

import time
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_bot_stats():
    """Get current bot statistics"""
    stats = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_trades': 0,
        'buy_trades': 0,
        'sell_trades': 0,
        'neutral_trades': 0,
        'win_rate': 0.0,
        'total_pnl': 0.0,
        'current_equity': 0.0,
        'total_return': 0.0,
        'last_trade_time': 'N/A',
        'last_trade_side': 'N/A',
        'signals_count': 0,
        'last_signal_time': 'N/A'
    }
    
    # Check executions
    exec_file = Path("paper_trading_outputs/5m/sheets_fallback/executions_paper.csv")
    if exec_file.exists():
        try:
            df = pd.read_csv(exec_file)
            if len(df) > 0:
                stats['total_trades'] = len(df)
                stats['buy_trades'] = (df['side'] == 'BUY').sum()
                stats['sell_trades'] = (df['side'] == 'SELL').sum()
                stats['neutral_trades'] = stats['total_trades'] - stats['buy_trades'] - stats['sell_trades']
                stats['win_rate'] = (df['realized_pnl'] > 0).sum() / len(df) * 100
                stats['total_pnl'] = df['realized_pnl'].sum()
                stats['current_equity'] = df['equity'].iloc[-1]
                initial_equity = df['equity'].iloc[0]
                stats['total_return'] = (stats['current_equity'] - initial_equity) / initial_equity * 100
                stats['last_trade_time'] = df['ts_iso'].iloc[-1]
                stats['last_trade_side'] = df['side'].iloc[-1]
        except Exception as e:
            pass
    
    # Check signals
    sig_file = Path("paper_trading_outputs/5m/sheets_fallback/signals.csv")
    if sig_file.exists():
        try:
            df_sig = pd.read_csv(sig_file)
            stats['signals_count'] = len(df_sig)
            if len(df_sig) > 0 and 'ts_ist' in df_sig.columns:
                stats['last_signal_time'] = df_sig['ts_ist'].iloc[-1]
        except Exception as e:
            pass
    
    return stats

def print_dashboard(stats):
    """Print formatted dashboard"""
    clear_screen()
    
    print("=" * 80)
    print(" " * 25 + "5M BOT LIVE MONITOR")
    print("=" * 80)
    print(f"\n⏰ Current Time: {stats['timestamp']}\n")
    
    print("─" * 80)
    print("📊 TRADE STATISTICS")
    print("─" * 80)
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  ├─ BUY:     {stats['buy_trades']:>4} ({stats['buy_trades']/max(stats['total_trades'],1)*100:>5.1f}%)")
    print(f"  ├─ SELL:    {stats['sell_trades']:>4} ({stats['sell_trades']/max(stats['total_trades'],1)*100:>5.1f}%)")
    print(f"  └─ NEUTRAL: {stats['neutral_trades']:>4} ({stats['neutral_trades']/max(stats['total_trades'],1)*100:>5.1f}%)")
    
    # Balance warning
    if stats['total_trades'] > 0:
        if stats['sell_trades'] == 0:
            print(f"\n  ⚠️  WARNING: NO SELL TRADES DETECTED!")
        elif stats['buy_trades'] > 0:
            ratio = stats['buy_trades'] / max(stats['sell_trades'], 1)
            if ratio > 2.0 or ratio < 0.5:
                print(f"\n  ⚠️  WARNING: IMBALANCED (BUY/SELL ratio: {ratio:.2f})")
            else:
                print(f"\n  ✓ BALANCED (BUY/SELL ratio: {ratio:.2f})")
    
    print("\n" + "─" * 80)
    print("💰 PROFITABILITY")
    print("─" * 80)
    print(f"  Win Rate:       {stats['win_rate']:>6.1f}%")
    print(f"  Total PnL:      ${stats['total_pnl']:>8.2f}")
    print(f"  Current Equity: ${stats['current_equity']:>8.2f}")
    print(f"  Total Return:   {stats['total_return']:>6.2f}%")
    
    print("\n" + "─" * 80)
    print("🔄 RECENT ACTIVITY")
    print("─" * 80)
    print(f"  Last Trade:  {stats['last_trade_time']} ({stats['last_trade_side']})")
    print(f"  Last Signal: {stats['last_signal_time']}")
    print(f"  Total Signals: {stats['signals_count']}")
    
    print("\n" + "=" * 80)
    print("Press Ctrl+C to stop monitoring...")
    print("=" * 80)

def main():
    """Main monitoring loop"""
    print("Starting 5m Bot Monitor...")
    print("Refreshing every 10 seconds...")
    time.sleep(2)
    
    try:
        while True:
            stats = get_bot_stats()
            print_dashboard(stats)
            time.sleep(10)  # Update every 10 seconds
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")

if __name__ == "__main__":
    main()
