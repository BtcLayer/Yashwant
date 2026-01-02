"""
Fetch historical OHLCV data from Hyperliquid for model training
Supports 1h, 12h, and 24h (1d) timeframes
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def fetch_hyperliquid_candles(symbol="BTC", interval="1h", days_back=180):
    """
    Fetch historical candle data from Hyperliquid
    
    Args:
        symbol: Trading symbol (default: "BTC")
        interval: Candle interval - "1h", "4h", "1d" 
        days_back: How many days of history to fetch
    
    Returns:
        DataFrame with OHLCV data
    """
    url = "https://api.hyperliquid.xyz/info"
    
    # Calculate timestamps
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    print(f"Fetching {symbol} {interval} data from Hyperliquid...")
    print(f"Period: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    print(f"Requesting ~{days_back} days of data...")
    print()
    
    # Hyperliquid API request
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print("❌ No data returned from API")
            return None
        
        # Parse the data
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
        
        df = pd.DataFrame(candles)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"✅ Successfully fetched {len(df)} candles")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print()
        print("Data preview:")
        print(df.head())
        print()
        print(df.tail())
        
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return None
    except Exception as e:
        print(f"❌ Error parsing data: {e}")
        return None

def save_data(df, filename):
    """Save DataFrame to CSV"""
    if df is not None and not df.empty:
        df.to_csv(filename, index=False)
        print(f"\n✅ Data saved to: {filename}")
        print(f"File size: {len(df)} rows")
        return True
    else:
        print("❌ No data to save")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Hyperliquid Historical Data Fetcher")
    print("=" * 60)
    print()
    
    # Fetch 1h data (for 1h model training)
    print("📊 Fetching 1h data...")
    print("-" * 60)
    df_1h = fetch_hyperliquid_candles(symbol="BTC", interval="1h", days_back=180)
    if df_1h is not None:
        save_data(df_1h, "ohlc_btc_1h.csv")
    
    print("\n" + "=" * 60)
    
    # Wait a bit to avoid rate limiting
    time.sleep(2)
    
    # Fetch 1d data (for 24h model training)
    print("\n📊 Fetching 1d (24h) data...")
    print("-" * 60)
    df_1d = fetch_hyperliquid_candles(symbol="BTC", interval="1d", days_back=730)  # 2 years
    if df_1d is not None:
        save_data(df_1d, "ohlc_btc_24h.csv")
    
    print("\n" + "=" * 60)
    print("✅ Data fetching complete!")
    print("=" * 60)
    print()
    print("Files created:")
    if df_1h is not None:
        print(f"  ✓ ohlc_btc_1h.csv ({len(df_1h)} rows)")
    if df_1d is not None:
        print(f"  ✓ ohlc_btc_24h.csv ({len(df_1d)} rows)")
    print()
    print("Next steps:")
    print("1. Check the CSV files to verify data looks correct")
    print("2. Start Jupyter: jupyter notebook")
    print("3. Open BanditV3.ipynb in the notebooks folder")
    print("4. Follow the training guide to train models")
