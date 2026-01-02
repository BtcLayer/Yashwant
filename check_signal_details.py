import pandas as pd

df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

# Get last signal
last = df.tail(1).iloc[0]

print("Last signal details:")
print(f"  s_model: {last['s_model']}")
print(f"  dir: {last['dir']}")

# Check mood columns
mood_cols = [c for c in df.columns if 'mood' in c.lower() or 'S_' in c]
print(f"\nMood-related columns: {mood_cols}")

if 'S_mood' in df.columns:
    print(f"  S_mood: {last['S_mood']}")

# Find a recent DOWN prediction
down_signals = df[df['s_model'] < 0].tail(5)
print(f"\nLast 5 DOWN predictions:")
for idx, row in down_signals.iterrows():
    print(f"  s_model={row['s_model']:.4f}, dir={row['dir']}, S_mood={row.get('S_mood', 'N/A')}")
