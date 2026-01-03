"""
Quick status check after restart
"""
import pandas as pd
import json
import os
from datetime import datetime, timedelta

print("=" * 80)
print("5M BOT STATUS CHECK - POST RESTART")
print("=" * 80)
print(f"Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Check config
print("📋 CONFIGURATION:")
print("-" * 80)
with open('live_demo/config.json', 'r') as f:
    config = json.load(f)

print(f"CONF_MIN: {config['thresholds']['CONF_MIN']}")
print(f"ALPHA_MIN: {config['thresholds']['ALPHA_MIN']}")
print(f"S_MIN: {config['thresholds']['S_MIN']}")
print(f"Require Consensus: {config['thresholds']['require_consensus']}")
print()

# Check for recent signals
print("🎯 SIGNAL STATUS:")
print("-" * 80)

signal_file = 'paper_trading_outputs/5m/logs/signals/date=2026-01-02/signals.csv'
if os.path.exists(signal_file):
    try:
        df = pd.read_csv(signal_file)
        print(f"✅ Signals file exists: {len(df)} total signals today")
        
        if len(df) > 0 and 's_model' in df.columns:
            recent = df.tail(10)
            s_model = recent['s_model'].dropna()
            
            if len(s_model) > 0:
                print(f"\nLast 10 Predictions:")
                print(f"  Min: {s_model.min():+.4f}")
                print(f"  Max: {s_model.max():+.4f}")
                print(f"  Mean: {s_model.mean():+.4f}")
                print(f"  Above 0.40: {sum(abs(s_model) >= 0.40)}/10")
                
                latest = s_model.iloc[-1]
                print(f"\n  Latest: {latest:+.4f} ({'UP' if latest > 0 else 'DOWN'})")
                if abs(latest) >= 0.40:
                    print(f"  ✅ TRADEABLE!")
                else:
                    print(f"  ⏳ Below threshold")
    except Exception as e:
        print(f"⚠️ Error: {e}")
else:
    print("⏳ No signals file yet (bot may be starting)")

print()

# Check for trades
print("📈 TRADE STATUS:")
print("-" * 80)

exec_file = 'paper_trading_outputs/executions_paper.csv'
if os.path.exists(exec_file):
    try:
        df = pd.read_csv(exec_file)
        df['ts_ist'] = pd.to_datetime(df['ts_ist'])
        
        # Trades in last hour
        recent = df[df['ts_ist'] > (datetime.now() - timedelta(hours=1))]
        
        if len(recent) > 0:
            print(f"✅ Trades in last hour: {len(recent)}")
            print(f"   BUY: {sum(recent['side']=='BUY')}")
            print(f"   SELL: {sum(recent['side']=='SELL')}")
            
            if 'pnl' in recent.columns:
                print(f"   P&L: ${recent['pnl'].sum():+.2f}")
        else:
            print("⏳ No trades in last hour")
            
    except Exception as e:
        print(f"⚠️ Error: {e}")
else:
    print("⏳ No execution file yet")

print()
print("=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print()
print("1. Make sure bot is restarted: python run_5m_debug.py")
print("2. Start monitor: python monitor_5m_realtime.py")
print("3. Wait 30 minutes for first trade")
print()
print("=" * 80)
