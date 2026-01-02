"""
COMPREHENSIVE FINAL CHECK
Check everything - signals, trades, performance
"""

import pandas as pd
import json
from datetime import datetime

print("="*80)
print(f"FINAL VERIFICATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# Load data
signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')

# Overall counts
total_signals = len(signals_df)
total_down = (signals_df['s_model'] < 0).sum()
total_sell_signals = (signals_df['dir'] == -1).sum()
total_sell_trades = (exec_df['side'] == 'SELL').sum()
total_buy_trades = (exec_df['side'] == 'BUY').sum()

print(f"\n📊 OVERALL STATISTICS:")
print(f"   Total signals: {total_signals}")
print(f"   Model DOWN predictions: {total_down}")
print(f"   SELL signals (dir=-1): {total_sell_signals}")
print(f"   BUY trades: {total_buy_trades}")
print(f"   SELL trades: {total_sell_trades}")

# Recent activity (last 20 signals - since restart)
recent = signals_df.tail(20)
recent_down = (recent['s_model'] < 0).sum()
recent_sell = (recent['dir'] == -1).sum()

print(f"\n📈 RECENT ACTIVITY (Last 20 signals ~since restart):")
print(f"   DOWN predictions: {recent_down}")
print(f"   SELL signals: {recent_sell}")

# Show last 10 signals with detail
print(f"\n📋 LAST 10 SIGNALS (Most Recent):")
for idx, row in signals_df.tail(10).iterrows():
    s_model = row['s_model']
    direction = row['dir']
    
    dir_str = "SELL" if direction == -1 else ("BUY" if direction == 1 else "NEUT")
    
    # Check if conversion is correct
    if s_model < 0:
        status = "✅ WORKING!" if direction == -1 else "❌ BLOCKED"
        marker = "***" if direction == -1 else ""
    elif s_model > 0:
        status = "✅" if direction == 1 else "?"
        marker = ""
    else:
        status = ""
        marker = ""
    
    ts = row['ts_iso'][-8:] if 'ts_iso' in row and len(str(row['ts_iso'])) > 8 else ""
    print(f"   {ts}: s_model={s_model:+.4f} → {dir_str:4s} {status} {marker}")

# Calculate performance
total_pnl = 0
wins = 0
losses = 0

for _, row in exec_df.iterrows():
    try:
        raw = json.loads(row['raw'])
        pnl = raw.get('realized_pnl', 0)
        total_pnl += pnl
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
    except:
        pass

win_rate = (wins / len(exec_df) * 100) if len(exec_df) > 0 else 0

print(f"\n💰 PERFORMANCE:")
print(f"   Total executions: {len(exec_df)}")
print(f"   Win rate: {win_rate:.1f}%")
print(f"   Wins: {wins}, Losses: {losses}")
print(f"   Total P&L: ${total_pnl:.2f}")

# FINAL VERDICT
print(f"\n" + "="*80)
print("FINAL VERDICT:")
print("="*80)

if total_sell_signals > 0:
    conversion_rate = (total_sell_signals / max(1, total_down)) * 100
    print(f"\n🎉 🎉 🎉 SUCCESS! FIX IS WORKING! 🎉 🎉 🎉")
    print(f"\n   ✅ {total_sell_signals} SELL signals generated")
    print(f"   ✅ Conversion rate: {conversion_rate:.1f}% (DOWN → SELL)")
    print(f"   ✅ System is now bidirectional")
    
    if total_sell_trades > 0:
        print(f"   ✅ {total_sell_trades} SELL trades executed")
        print(f"\n   🏆 COMPLETE SUCCESS - System fully operational!")
    else:
        print(f"   ⏳ SELL trades: {total_sell_trades} (waiting for execution)")
        
elif recent_down > 0 and recent_sell == 0:
    print(f"\n❌ FIX STILL NOT WORKING")
    print(f"\n   Problem: {recent_down} DOWN predictions but 0 SELL signals")
    print(f"   Cache may still be an issue or different problem")
    
elif recent_down == 0:
    print(f"\n⏳ INCONCLUSIVE - Need more time")
    print(f"\n   Model hasn't predicted DOWN since restart")
    print(f"   Wait for market conditions to trigger DOWN prediction")
    print(f"   Check again in 30-60 minutes")
    
else:
    print(f"\n⏳ WAITING FOR DATA")

print("="*80)
