import pandas as pd
import time
import os
import sys

def get_latest_file(pattern, directory):
    import glob
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

EXECUTIONS_FILE = r'c:\Users\yashw\MetaStackerBandit\paper_trading_outputs\5m\sheets_fallback\executions_paper.csv'

print("=" * 60)
print("PROFITABILITY MONITOR - 5M BOT (NEW MODEL)")
print("=" * 60)

while True:
    try:
        if not os.path.exists(EXECUTIONS_FILE):
            print(f"Waiting for execution file: {EXECUTIONS_FILE}...")
            time.sleep(10)
            continue

        try:
            df = pd.read_csv(EXECUTIONS_FILE)
        except pd.errors.EmptyDataError:
            print("File empty, waiting for trades...")
            time.sleep(10)
            continue
        
        if len(df) == 0:
            print("No trades found yet.")
            time.sleep(10)
            continue
            
        # Calculate key metrics
        total_trades = len(df)
        
        if 'realized_pnl' in df.columns:
            total_pnl = df['realized_pnl'].sum()
            winning_trades = len(df[df['realized_pnl'] > 0])
        else:
            total_pnl = 0.0
            winning_trades = 0

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Clear screen (simulated with newlines)
        print("\n" * 5)
        print("=" * 60)
        print(f"PROFITABILITY MONITOR - 5M BOT (Updated: {time.strftime('%H:%M:%S')})")
        print("=" * 60)
        
        print(f"Total Trades:      {total_trades}")
        if 'realized_pnl' in df.columns:
            print(f"Total PnL (USDT):  {total_pnl:.2f}")
            print(f"Win Rate:          {win_rate:.1f}%")
        else:
            print("PnL:               (Not calculated in CSV)")
            
        print("\nLast 5 Trades:")
        cols_to_show = [c for c in ['timestamp', 'side', 'price', 'quantity', 'realized_pnl'] if c in df.columns]
        if not cols_to_show:
             cols_to_show = df.columns[:5]
        print(df[cols_to_show].tail(5).to_string(index=False))
        
        print("\n" + "-" * 60)
        print("Monitoring... (Ctrl+C to stop)")
        
        time.sleep(30)
        
    except KeyboardInterrupt:
        print("\nStopped.")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
