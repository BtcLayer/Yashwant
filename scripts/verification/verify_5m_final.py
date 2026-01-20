import pandas as pd

signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
execs = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')

print("="*60)
print("5M TIMEFRAME - FINAL VERIFICATION")
print("="*60)

print("\nMODEL PREDICTIONS:")
up_preds = (signals['s_model'] > 0).sum()
down_preds = (signals['s_model'] < 0).sum()
print(f"  UP (s_model > 0): {up_preds}")
print(f"  DOWN (s_model < 0): {down_preds}")

print("\nEXECUTIONS:")
buy_execs = (execs['side'] == 'BUY').sum()
sell_execs = (execs['side'] == 'SELL').sum()
print(f"  BUY: {buy_execs}")
print(f"  SELL: {sell_execs}")

print("\n" + "="*60)
print("CONCLUSION:")
print("="*60)

if down_preds > 0 and sell_execs == 0:
    print("\n🔴 CRITICAL BUG CONFIRMED:")
    print(f"  - Model predicts DOWN {down_preds} times")
    print(f"  - But system NEVER executes SELL trades")
    print(f"  - Same bug as 24h timeframe")
    print(f"\n❌ 5M IS BROKEN - Execution logic bug")
elif sell_execs > 0:
    print("\n✅ 5M IS WORKING:")
    print(f"  - Model predicts both directions")
    print(f"  - System executes both BUY and SELL")
    print(f"\n✅ 5M IS FINE AND GOOD")
else:
    print("\n⚠️  UNCLEAR - Need more investigation")

print("="*60)
