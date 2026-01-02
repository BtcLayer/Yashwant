import pandas as pd

# Load data
signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')

# Count
total_down = (signals_df['s_model'] < 0).sum()
total_sell_signals = (signals_df['dir'] == -1).sum()
total_sell_trades = (exec_df['side'] == 'SELL').sum()

# Recent
recent = signals_df.tail(50)
recent_down = (recent['s_model'] < 0).sum()
recent_sell = (recent['dir'] == -1).sum()

print("VERIFICATION RESULTS:")
print(f"Total DOWN predictions: {total_down}")
print(f"Total SELL signals: {total_sell_signals}")
print(f"Total SELL trades: {total_sell_trades}")
print(f"\nRecent (50 signals):")
print(f"DOWN predictions: {recent_down}")
print(f"SELL signals: {recent_sell}")

if total_sell_signals > 0:
    print(f"\n✅ SUCCESS! Fix is working!")
    print(f"Conversion: {total_sell_signals}/{total_down} = {total_sell_signals/max(1,total_down)*100:.1f}%")
elif recent_down > 0:
    print(f"\n❌ FAIL! {recent_down} DOWN predictions but 0 SELL signals")
else:
    print(f"\n⏳ WAITING - No DOWN predictions yet")
