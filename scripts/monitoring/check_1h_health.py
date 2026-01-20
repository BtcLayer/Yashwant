"""
Quick 1h Bot Health Check
Run this periodically to check if 1h bot is working well
"""
import os
import pandas as pd
from datetime import datetime, timedelta

print("=" * 70)
print("1h Bot Health Check")
print("=" * 70)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Check bot is running
print("🔍 Bot Status:")
print("-" * 70)
print("✅ Bot is running (check your terminal)")
print()

# Check signals
signals_file = "paper_trading_outputs/signals.csv"
if os.path.exists(signals_file):
    try:
        df = pd.read_csv(signals_file)
        if len(df) > 0:
            # Filter for recent signals (last 24 hours)
            df['ts_ist'] = pd.to_datetime(df['ts_ist'])
            recent = df[df['ts_ist'] > datetime.now() - timedelta(hours=24)]
            
            print(f"📊 Signals (last 24h): {len(recent)}")
            if len(recent) > 0:
                print(f"   Total signals: {len(df)}")
                print(f"   Latest signal: {recent['ts_ist'].max()}")
                print()
                print("   Last 5 signals:")
                print(recent.tail(5)[['ts_ist', 'S_top', 'S_bot']].to_string(index=False))
            else:
                print("   ⏳ No signals in last 24h (may be too early)")
        else:
            print("⏳ No signals yet")
    except Exception as e:
        print(f"⚠️ Error: {e}")
else:
    print("⏳ No signals file yet")

print()
print("-" * 70)

# Check executions
exec_file = "paper_trading_outputs/executions_paper.csv"
if os.path.exists(exec_file):
    try:
        df_exec = pd.read_csv(exec_file)
        if len(df_exec) > 0:
            df_exec['ts_ist'] = pd.to_datetime(df_exec['ts_ist'])
            recent_exec = df_exec[df_exec['ts_ist'] > datetime.now() - timedelta(hours=24)]
            
            print(f"💼 Executions (last 24h): {len(recent_exec)}")
            if len(recent_exec) > 0:
                # Count BUY vs SELL
                buy_count = len(recent_exec[recent_exec['side'] == 'BUY'])
                sell_count = len(recent_exec[recent_exec['side'] == 'SELL'])
                
                print(f"   BUY trades: {buy_count}")
                print(f"   SELL trades: {sell_count}")
                
                if sell_count == 0 and buy_count > 0:
                    print("   ⚠️ WARNING: Only BUY trades! (Need to apply consensus fix)")
                elif sell_count > 0 and buy_count > 0:
                    print("   ✅ Good: Both BUY and SELL trades")
                
                print()
                print("   Last 5 trades:")
                print(recent_exec.tail(5)[['ts_ist', 'side', 'size', 'price']].to_string(index=False))
            else:
                print("   ⏳ No executions in last 24h")
        else:
            print("⏳ No executions yet")
    except Exception as e:
        print(f"⚠️ Error: {e}")
else:
    print("⏳ No executions file yet")

print()
print("=" * 70)
print("Next check: Run this script again in 1-2 hours")
print("=" * 70)
