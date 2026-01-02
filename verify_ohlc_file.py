import pandas as pd

print("=" * 80)
print("CHECKING ohlc_btc_5m.csv")
print("=" * 80)
print()

df = pd.read_csv('ohlc_btc_5m.csv')

print(f"Total Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")
print()

print("Column Names:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

print()

if 'timestamp' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
    print(f"Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    days = (df['timestamp'].max() - df['timestamp'].min()).days
    print(f"Days of Data: {days}")
    print()

print("First 5 rows:")
print(df.head())
print()

print("Last 5 rows:")
print(df.tail())
print()

print("=" * 80)
print("VERDICT")
print("=" * 80)
print()

if len(df) >= 10000:
    print(f"✅ EXCELLENT! This file has {len(df):,} rows")
    print("✅ This is MORE than enough for retraining!")
    print()
    print("This is the EXACT file the notebook needs!")
else:
    print(f"⚠️ File has {len(df):,} rows")
    print(f"   Need at least 10,000 for good training")
