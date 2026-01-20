"""
Verification Script: Check if SELL trades fix is working
Run this AFTER restarting the bot to verify SELL trades are being generated
"""

import pandas as pd
import time
from datetime import datetime

print("="*80)
print("SELL TRADES FIX - VERIFICATION SCRIPT")
print("="*80)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Load current execution data
try:
    exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
    
    print(f"\n📊 CURRENT EXECUTION STATUS:")
    print(f"  Total executions: {len(exec_df)}")
    
    side_counts = exec_df['side'].value_counts()
    buy_count = side_counts.get('BUY', 0)
    sell_count = side_counts.get('SELL', 0)
    
    print(f"  BUY trades: {buy_count}")
    print(f"  SELL trades: {sell_count}")
    
    if sell_count > 0:
        print(f"\n✅ SUCCESS: SELL trades are happening!")
        print(f"   Fix is working correctly")
        
        # Show recent SELL trades
        sell_trades = exec_df[exec_df['side'] == 'SELL'].tail(5)
        if len(sell_trades) > 0:
            print(f"\n   Recent SELL trades:")
            for idx, row in sell_trades.iterrows():
                print(f"     {row['ts_iso']}: SELL {row['qty']:.6f} @ ${row['mid_price']:.2f}")
    else:
        print(f"\n⚠️  NO SELL TRADES YET")
        print(f"   Either:")
        print(f"   1. Bot hasn't generated DOWN signals yet (wait)")
        print(f"   2. Fix didn't work (check logs)")
        print(f"   3. Bot not restarted yet (restart required)")
        
except FileNotFoundError:
    print(f"\n❌ ERROR: Execution file not found")
    print(f"   Bot may not be running")

# Check signals to see if dir=-1 is being generated
try:
    signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
    
    print(f"\n📊 SIGNAL ANALYSIS:")
    dir_counts = signals_df['dir'].value_counts()
    
    print(f"  dir = +1 (BUY): {dir_counts.get(1, 0)}")
    print(f"  dir = -1 (SELL): {dir_counts.get(-1, 0)}")
    print(f"  dir = 0 (NEUTRAL): {dir_counts.get(0, 0)}")
    
    if dir_counts.get(-1, 0) > 0:
        print(f"\n✅ SELL signals are being generated!")
        print(f"   Fix is working at the decision level")
    else:
        print(f"\n⚠️  No SELL signals yet")
        print(f"   Model may not have predicted DOWN yet")
        
except FileNotFoundError:
    print(f"\n⚠️  Signals file not found")

print(f"\n{'='*80}")
print("NEXT STEPS:")
print("="*80)

if sell_count > 0:
    print(f"\n✅ Fix is working! Monitor performance:")
    print(f"   1. Check win rate (should improve from 0%)")
    print(f"   2. Monitor P&L")
    print(f"   3. Watch execution rate")
    print(f"   4. Compare before/after metrics")
else:
    print(f"\n⏳ Waiting for SELL trades:")
    print(f"   1. Ensure bot is restarted")
    print(f"   2. Wait for model to predict DOWN")
    print(f"   3. Run this script again in 1 hour")
    print(f"   4. Check logs for errors")

print("="*80)
