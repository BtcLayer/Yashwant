import pandas as pd
import os

if os.path.exists('ohlc_btc_5m_complete.csv'):
    df = pd.read_csv('ohlc_btc_5m_complete.csv')
    print(f"Rows: {len(df)}")
    if len(df) > 0:
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(df.head())
        print()
        if len(df) >= 10000:
            print("✅ ENOUGH DATA FOR RETRAINING!")
        else:
            print(f"⚠️ Need {10000 - len(df)} more rows")
    else:
        print("File is empty!")
else:
    print("File not found: ohlc_btc_5m_complete.csv")
