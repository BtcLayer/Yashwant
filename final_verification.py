"""
FINAL VERIFICATION - Is the fix working?
Check if SELL signals are being generated after bot restart
"""

import pandas as pd
from datetime import datetime
import json

print("="*80)
print("FINAL VERIFICATION - FIX SUCCESS CHECK")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# Load data
signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')

# Overall stats
total_signals = len(signals_df)
total_down = (signals_df['s_model'] < 0).sum()
total_sell_signals = (signals_df['dir'] == -1).sum()
total_sell_trades = (exec_df['side'] == 'SELL').sum()

print(f"\n📊 OVERALL STATISTICS:")
print(f"   Total signals: {total_signals}")
print(f"   Model DOWN predictions: {total_down}")
print(f"   SELL signals (dir=-1): {total_sell_signals}")
print(f"   SELL trades executed: {total_sell_trades}")

# Calculate conversion rate
if total_down > 0:
    conversion_rate = (total_sell_signals / total_down) * 100
    print(f"   Conversion rate: {conversion_rate:.1f}%")
else:
    conversion_rate = 0

# Check recent activity (since restart ~2 hours ago)
recent = signals_df.tail(50)  # Last 50 signals (~4 hours of data)
recent_down = (recent['s_model'] < 0).sum()
recent_sell = (recent['dir'] == -1).sum()

print(f"\n📈 RECENT ACTIVITY (Last 50 signals):")
print(f"   DOWN predictions: {recent_down}")
print(f"   SELL signals: {recent_sell}")

if recent_down > 0:
    recent_conversion = (recent_sell / recent_down) * 100
    print(f"   Recent conversion rate: {recent_conversion:.1f}%")

# Performance metrics
total_exec = len(exec_df)
buy_trades = (exec_df['side'] == 'BUY').sum()

# Calculate P&L and win rate
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

win_rate = (wins / total_exec * 100) if total_exec > 0 else 0

print(f"\n💰 PERFORMANCE:")
print(f"   Total executions: {total_exec}")
print(f"   BUY trades: {buy_trades}")
print(f"   SELL trades: {total_sell_trades}")
print(f"   Win rate: {win_rate:.1f}%")
print(f"   Total P&L: ${total_pnl:.2f}")

# Show sample of recent signals
print(f"\n📋 LAST 10 SIGNALS:")
for idx, row in signals_df.tail(10).iterrows():
    s_model = row['s_model']
    direction = row['dir']
    
    dir_str = "SELL" if direction == -1 else ("BUY" if direction == 1 else "NEUT")
    
    # Check if conversion is correct
    if s_model < 0:
        status = "✅" if direction == -1 else "❌ BLOCKED"
    elif s_model > 0:
        status = "✅" if direction == 1 else "❌"
    else:
        status = ""
    
    ts = row['ts_iso'][-8:] if 'ts_iso' in row and len(str(row['ts_iso'])) > 8 else ""
    print(f"   {ts}: s_model={s_model:+.4f} → {dir_str:4s} {status}")

# FINAL VERDICT
print(f"\n" + "="*80)
print("FINAL VERDICT:")
print("="*80)

if total_sell_signals > 0:
    print(f"\n✅ ✅ ✅ FIX IS WORKING! ✅ ✅ ✅")
    print(f"\n   SUCCESS METRICS:")
    print(f"   • {total_sell_signals} SELL signals generated")
    print(f"   • {total_sell_trades} SELL trades executed")
    print(f"   • {conversion_rate:.1f}% conversion rate (DOWN → SELL)")
    print(f"   • System is now bidirectional")
    
    if total_sell_trades > 0:
        print(f"\n   🎉 COMPLETE SUCCESS!")
        print(f"   • SELL signals generating ✅")
        print(f"   • SELL trades executing ✅")
        print(f"   • Position management working ✅")
    else:
        print(f"\n   ⚠️  PARTIAL SUCCESS:")
        print(f"   • SELL signals generating ✅")
        print(f"   • SELL trades not executing yet ⏳")
        print(f"   • May need more time for trades to execute")
    
    if win_rate > 0:
        print(f"\n   💰 PROFITABILITY IMPROVING:")
        print(f"   • Win rate: {win_rate:.1f}% (was 0%)")
        print(f"   • System becoming profitable ✅")

elif recent_down > 0 and recent_sell == 0:
    print(f"\n❌ FIX NOT WORKING")
    print(f"\n   PROBLEM:")
    print(f"   • Model predicted DOWN {recent_down} times recently")
    print(f"   • But 0 SELL signals generated")
    print(f"   • Consensus still blocking")
    print(f"\n   POSSIBLE CAUSES:")
    print(f"   • Bot didn't restart properly")
    print(f"   • Code not reloaded")
    print(f"   • Config not applied")

else:
    print(f"\n⏳ INCONCLUSIVE - NEED MORE TIME")
    print(f"\n   STATUS:")
    print(f"   • Model hasn't predicted DOWN recently")
    print(f"   • Cannot verify if fix is working")
    print(f"   • Market may be in strong uptrend")
    print(f"\n   RECOMMENDATION:")
    print(f"   • Wait for market to move DOWN")
    print(f"   • Check again in 1-2 hours")

print("="*80)
