import pandas as pd
from datetime import datetime

print("="*80)
print(f"QUICK STATUS - {datetime.now().strftime('%H:%M:%S')}")
print("="*80)

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

total = len(df)
down_preds = (df['s_model'] < 0).sum()
sell_signals = (df['dir'] == -1).sum()

print(f"\nTotal signals: {total}")
print(f"DOWN predictions: {down_preds}")
print(f"SELL signals: {sell_signals}")

if sell_signals > 0:
    print(f"\n✅ SUCCESS! {sell_signals} SELL signals generated!")
    print(f"Conversion rate: {sell_signals/max(1,down_preds)*100:.1f}%")
else:
    print(f"\n⏳ No SELL signals yet")
    print(f"   {down_preds} DOWN predictions waiting to convert")

# Check last 10 signals
recent = df.tail(10)
print(f"\nLast 10 signals:")
for idx, row in recent.iterrows():
    s = row['s_model']
    d = row['dir']
    dir_str = "SELL" if d == -1 else ("BUY" if d == 1 else "NEUT")
    match = "✅" if (s < 0 and d == -1) or (s > 0 and d == 1) else ("❌" if s < 0 and d != -1 else "")
    print(f"  s_model={s:+.4f} → {dir_str} {match}")

print("="*80)
