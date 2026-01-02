import pandas as pd

df = pd.read_csv('ohlc_btc_5m_fresh.csv')
print(f"Rows: {len(df)}")
if len(df) > 0:
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(df.head())
else:
    print("File is empty!")
