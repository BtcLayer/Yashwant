"""
Fetch 200 5-minute candles from Hyperliquid and save to snapshot.csv
"""
import requests
import csv
from datetime import datetime

def fetch_hyperliquid_candles(symbol="SOL", num_candles=200):
    """
    Fetch historical candles from Hyperliquid API
    
    Args:
        symbol: Trading symbol (default: SOL)
        num_candles: Number of candles to fetch (default: 200)
    
    Returns:
        List of candle data
    """
    url = "https://api.hyperliquid.xyz/info"
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": "5m",
            "startTime": 0,  # Will get most recent candles
            "endTime": int(datetime.now().timestamp() * 1000)
        }
    }
    
    print(f"Fetching {num_candles} 5-minute candles for {symbol}...")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print("Error: No data returned from API")
            return []
        
        # Get the most recent N candles
        candles = data[-num_candles:] if len(data) > num_candles else data
        
        print(f"Successfully fetched {len(candles)} candles")
        return candles
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []

def save_to_csv(candles, filename="snapshot.csv"):
    """
    Save candle data to CSV file
    
    Args:
        candles: List of candle data from Hyperliquid
        filename: Output CSV filename
    """
    if not candles:
        print("No candles to save")
        return
    
    result = []
    for candle in candles:
        result.append([
            int(candle["t"]),    # timestamp (start time)
            float(candle["o"]),  # open
            float(candle["h"]),  # high
            float(candle["l"]),  # low
            float(candle["c"]),  # close
            float(candle["v"]),  # volume
            int(candle["T"]),    # close time (end time)
        ])
    
    # Write to CSV with bot-compatible column names
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        # Write header - bot expects: ts, open, high, low, close, volume
        writer.writerow(['ts', 'open', 'high', 'low', 'close', 'volume'])
        # Write data (only first 6 columns, skip timestamp_end)
        for row in result:
            writer.writerow(row[:6])  # ts, open, high, low, close, volume
    
    print(f"Saved {len(result)} candles to {filename}")
    
    # Print first and last candle for verification
    if result:
        print(f"\nFirst candle: {datetime.fromtimestamp(result[0][0]/1000)} UTC")
        print(f"Last candle:  {datetime.fromtimestamp(result[-1][0]/1000)} UTC")

def main():
    # Fetch 200 5-minute candles for SOL
    candles = fetch_hyperliquid_candles(symbol="SOL", num_candles=200)
    
    # Save to snapshot.csv
    if candles:
        save_to_csv(candles, filename="snapshot.csv")
        print("\n✅ Done! snapshot.csv created successfully")
    else:
        print("\n❌ Failed to fetch candles")

if __name__ == "__main__":
    main()
