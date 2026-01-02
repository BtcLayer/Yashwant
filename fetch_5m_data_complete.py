"""
Fetch sufficient 5m data from Hyperliquid using multiple API calls
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

print("=" * 80)
print("FETCHING 5M DATA FROM HYPERLIQUID (MULTI-REQUEST)")
print("=" * 80)
print()

def fetch_hyperliquid_chunk(start_time, end_time):
    """Fetch one chunk of data"""
    url = "https://api.hyperliquid.xyz/info"
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "5m",
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return None
        
        candles = []
        for candle in data:
            candles.append({
                'timestamp': datetime.fromtimestamp(candle['t'] / 1000),
                'open': float(candle['o']),
                'high': float(candle['h']),
                'low': float(candle['l']),
                'close': float(candle['c']),
                'volume': float(candle['v'])
            })
        
        return pd.DataFrame(candles)
        
    except Exception as e:
        print(f"   Error: {e}")
        return None

# Fetch data in chunks (Hyperliquid seems to limit to ~5000 candles per request)
print("Fetching data in chunks...")
print()

all_data = []
end_time = datetime.now()

# We need ~50,000 candles for 6 months of 5m data
# Each chunk gets ~5000 candles = ~17 days
# So we need ~10 chunks

chunks_needed = 10
chunk_days = 20  # Slightly more to ensure overlap

for i in range(chunks_needed):
    start_time = end_time - timedelta(days=chunk_days)
    
    print(f"Chunk {i+1}/{chunks_needed}:")
    print(f"  From: {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  To: {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    df_chunk = fetch_hyperliquid_chunk(start_time, end_time)
    
    if df_chunk is not None and len(df_chunk) > 0:
        all_data.append(df_chunk)
        print(f"  ✅ Got {len(df_chunk)} candles")
    else:
        print(f"  ⚠️ No data")
    
    # Move to next chunk
    end_time = start_time
    
    # Sleep to avoid rate limiting
    if i < chunks_needed - 1:
        print(f"  Waiting 2 seconds...")
        time.sleep(2)
    
    print()

# Combine all chunks
if all_data:
    print("=" * 80)
    print("COMBINING DATA")
    print("=" * 80)
    print()
    
    df_combined = pd.concat(all_data, ignore_index=True)
    
    # Remove duplicates
    df_combined = df_combined.drop_duplicates(subset=['timestamp'])
    
    # Sort by timestamp
    df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)
    
    print(f"Total candles: {len(df_combined)}")
    print(f"Date range: {df_combined['timestamp'].min()} to {df_combined['timestamp'].max()}")
    
    days = (df_combined['timestamp'].max() - df_combined['timestamp'].min()).days
    print(f"Days of data: {days}")
    print()
    
    # Save
    output_file = 'ohlc_btc_5m_complete.csv'
    df_combined.to_csv(output_file, index=False)
    
    print(f"✅ Saved to: {output_file}")
    print()
    
    if len(df_combined) >= 10000:
        print("=" * 80)
        print("✅ SUCCESS! Enough data for retraining")
        print("=" * 80)
    else:
        print("=" * 80)
        print("⚠️ WARNING: Still not enough data")
        print(f"   Need: 10,000+ candles")
        print(f"   Have: {len(df_combined)} candles")
        print("=" * 80)
else:
    print("=" * 80)
    print("❌ FAILED: No data fetched")
    print("=" * 80)
