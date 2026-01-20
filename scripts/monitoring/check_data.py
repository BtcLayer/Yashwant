"""
Quick check of the fetched Hyperliquid data
"""
import pandas as pd

print("=" * 60)
print("Data Quality Check")
print("=" * 60)
print()

# Check 1h data
print("📊 1h Data (ohlc_btc_1h.csv):")
print("-" * 60)
try:
    df_1h = pd.read_csv('ohlc_btc_1h.csv')
    df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
    
    print(f"✅ Rows: {len(df_1h)}")
    print(f"✅ Date range: {df_1h['timestamp'].min()} to {df_1h['timestamp'].max()}")
    print(f"✅ Columns: {list(df_1h.columns)}")
    print()
    print("First 3 rows:")
    print(df_1h.head(3))
    print()
    print("Last 3 rows:")
    print(df_1h.tail(3))
    print()
    
    # Check for missing values
    missing = df_1h.isnull().sum()
    if missing.sum() > 0:
        print("⚠️ Missing values:")
        print(missing[missing > 0])
    else:
        print("✅ No missing values")
    
except FileNotFoundError:
    print("❌ File not found")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 60)
print()

# Check 24h data
print("📊 24h Data (ohlc_btc_24h.csv):")
print("-" * 60)
try:
    df_24h = pd.read_csv('ohlc_btc_24h.csv')
    df_24h['timestamp'] = pd.to_datetime(df_24h['timestamp'])
    
    print(f"✅ Rows: {len(df_24h)}")
    print(f"✅ Date range: {df_24h['timestamp'].min()} to {df_24h['timestamp'].max()}")
    print(f"✅ Columns: {list(df_24h.columns)}")
    print()
    print("First 3 rows:")
    print(df_24h.head(3))
    print()
    
    # Check for missing values
    missing = df_24h.isnull().sum()
    if missing.sum() > 0:
        print("⚠️ Missing values:")
        print(missing[missing > 0])
    else:
        print("✅ No missing values")
    
except FileNotFoundError:
    print("❌ File not found")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 60)
print("✅ Data check complete!")
print("=" * 60)
