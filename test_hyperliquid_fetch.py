"""
Quick test: Fetch fresh 5m data from Hyperliquid
"""
import requests
from datetime import datetime, timedelta
import pandas as pd

url = "https://api.hyperliquid.xyz/info"

end_time = datetime.now()
start_time = end_time - timedelta(days=7)  # Try just 7 days first

print(f"Testing Hyperliquid API...")
print(f"From: {start_time}")
print(f"To: {end_time}")

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
    print("\nSending request...")
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response type: {type(data)}")
        print(f"Data length: {len(data) if isinstance(data, list) else 'N/A'}")
        
        if isinstance(data, list) and len(data) > 0:
            print(f"\nFirst candle: {data[0]}")
            print(f"Last candle: {data[-1]}")
            print(f"\n✓ SUCCESS! Got {len(data)} candles")
            
            # Convert to DataFrame
            candles = []
            for c in data:
                candles.append({
                    'timestamp': datetime.fromtimestamp(c['t'] / 1000),
                    'open': float(c['o']),
                    'high': float(c['h']),
                    'low': float(c['l']),
                    'close': float(c['c']),
                    'volume': float(c['v'])
                })
            
            df = pd.DataFrame(candles)
            print(f"\nDataFrame shape: {df.shape}")
            print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        else:
            print(f"\n✗ FAILED: Empty or invalid response")
            print(f"Response: {data}")
    else:
        print(f"\n✗ FAILED: HTTP {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
