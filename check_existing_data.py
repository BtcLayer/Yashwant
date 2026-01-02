"""
Check if live bot has enough historical data for retraining
"""
import os
import pandas as pd
from datetime import datetime

print("=" * 80)
print("CHECKING FOR EXISTING BOT DATA")
print("=" * 80)
print()

# Check various possible locations for 5m data
possible_locations = [
    'live_demo/ohlc_btc_5m.csv',
    'live_demo/data/ohlc_btc_5m.csv',
    'paper_trading_outputs/ohlc_btc_5m.csv',
    'paper_trading_outputs/5m/ohlc_btc_5m.csv',
]

found_data = None
best_file = None
max_rows = 0

for location in possible_locations:
    if os.path.exists(location):
        try:
            df = pd.read_csv(location)
            print(f"✅ Found: {location}")
            print(f"   Rows: {len(df)}")
            
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
                
                # Calculate days of data
                days = (df['timestamp'].max() - df['timestamp'].min()).days
                print(f"   Days of data: {days}")
            
            print()
            
            if len(df) > max_rows:
                max_rows = len(df)
                best_file = location
                found_data = df
                
        except Exception as e:
            print(f"⚠️ Error reading {location}: {e}")
            print()

if found_data is not None and len(found_data) >= 10000:
    print("=" * 80)
    print("✅ SUFFICIENT DATA FOUND!")
    print("=" * 80)
    print()
    print(f"Best file: {best_file}")
    print(f"Rows: {len(found_data)}")
    print(f"Date range: {found_data['timestamp'].min()} to {found_data['timestamp'].max()}")
    
    days = (found_data['timestamp'].max() - found_data['timestamp'].min()).days
    print(f"Days of data: {days}")
    print()
    print("✅ This is enough data for retraining!")
    print(f"   Minimum needed: 10,000 rows")
    print(f"   We have: {len(found_data):,} rows")
    print()
    print("Next step: Use this data for retraining")
    
elif found_data is not None:
    print("=" * 80)
    print("⚠️ INSUFFICIENT DATA")
    print("=" * 80)
    print()
    print(f"Best file: {best_file}")
    print(f"Rows: {len(found_data)}")
    print(f"Need: 10,000+ rows")
    print(f"Short by: {10000 - len(found_data)} rows")
    print()
    print("Next step: Need to fetch more data via API")
    
else:
    print("=" * 80)
    print("❌ NO DATA FOUND")
    print("=" * 80)
    print()
    print("Checked locations:")
    for loc in possible_locations:
        print(f"   - {loc}")
    print()
    print("Next step: Must fetch data from Hyperliquid API")

print()
print("=" * 80)
