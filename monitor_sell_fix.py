"""
Real-time monitoring script for SELL trades fix
Monitors the bot and reports status every 30 seconds
"""

import pandas as pd
import time
import os
from datetime import datetime

def check_status():
    """Check current status of executions and signals"""
    try:
        # Load data
        exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
        signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
        
        # Execution stats
        total_exec = len(exec_df)
        buy_count = (exec_df['side'] == 'BUY').sum()
        sell_count = (exec_df['side'] == 'SELL').sum()
        
        # Signal stats
        dir_counts = signals_df['dir'].value_counts()
        dir_buy = dir_counts.get(1, 0)
        dir_sell = dir_counts.get(-1, 0)
        dir_neutral = dir_counts.get(0, 0)
        
        # Recent activity
        recent_exec = exec_df.tail(5)
        recent_signals = signals_df.tail(10)
        
        return {
            'total_exec': total_exec,
            'buy_exec': buy_count,
            'sell_exec': sell_count,
            'dir_buy': dir_buy,
            'dir_sell': dir_sell,
            'dir_neutral': dir_neutral,
            'recent_exec': recent_exec,
            'recent_signals': recent_signals,
            'timestamp': datetime.now()
        }
    except Exception as e:
        return {'error': str(e), 'timestamp': datetime.now()}

def print_status(status, iteration):
    """Print formatted status"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("="*80)
    print(f"SELL TRADES FIX - LIVE MONITORING (Update #{iteration})")
    print(f"Time: {status['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    if 'error' in status:
        print(f"\n❌ ERROR: {status['error']}")
        print("   Bot may not be running or data files not accessible")
        return
    
    print(f"\n📊 EXECUTION SUMMARY:")
    print(f"  Total executions: {status['total_exec']}")
    print(f"  BUY trades: {status['buy_exec']}")
    print(f"  SELL trades: {status['sell_exec']} {'✅ FIX WORKING!' if status['sell_exec'] > 0 else '⏳ Waiting...'}")
    
    print(f"\n📊 SIGNAL SUMMARY:")
    print(f"  dir = +1 (BUY signals): {status['dir_buy']}")
    print(f"  dir = -1 (SELL signals): {status['dir_sell']} {'✅ Generating!' if status['dir_sell'] > 0 else '⏳ Waiting...'}")
    print(f"  dir = 0 (NEUTRAL): {status['dir_neutral']}")
    
    if status['sell_exec'] > 0:
        print(f"\n✅ SUCCESS: SELL trades are happening!")
        print(f"\n   Recent SELL trades:")
        sell_trades = status['recent_exec'][status['recent_exec']['side'] == 'SELL']
        for idx, row in sell_trades.iterrows():
            print(f"     {row['ts_iso']}: SELL {row['qty']:.6f}")
    
    print(f"\n📈 RECENT SIGNALS (last 10):")
    for idx, row in status['recent_signals'].tail(5).iterrows():
        direction = "BUY" if row['dir'] == 1 else ("SELL" if row['dir'] == -1 else "NEUTRAL")
        s_model = row['s_model']
        print(f"  {row['ts_iso']}: s_model={s_model:+.4f} → dir={direction}")
    
    print(f"\n{'='*80}")
    print("Press Ctrl+C to stop monitoring")
    print("="*80)

def monitor(interval=30, max_iterations=120):
    """Monitor bot status"""
    print("Starting monitoring...")
    print(f"Will check every {interval} seconds")
    print("Press Ctrl+C to stop\n")
    
    iteration = 0
    try:
        while iteration < max_iterations:
            iteration += 1
            status = check_status()
            print_status(status, iteration)
            
            # Check if we have SELL trades - if so, celebrate and continue monitoring
            if 'sell_exec' in status and status['sell_exec'] > 0:
                # Keep monitoring but less frequently
                time.sleep(interval * 2)
            else:
                time.sleep(interval)
                
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        print("="*80)
        
        # Final status
        final_status = check_status()
        if 'sell_exec' in final_status:
            print(f"\nFINAL STATUS:")
            print(f"  Total executions: {final_status['total_exec']}")
            print(f"  SELL trades: {final_status['sell_exec']}")
            print(f"  SELL signals: {final_status['dir_sell']}")
            
            if final_status['sell_exec'] > 0:
                print(f"\n✅ Fix is working! SELL trades are happening.")
            else:
                print(f"\n⏳ No SELL trades yet. Keep bot running.")

if __name__ == "__main__":
    monitor(interval=30)
