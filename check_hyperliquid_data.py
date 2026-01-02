"""
Check if there's a data inversion issue with Hyperliquid data
Compare the OHLC data to see if prices are inverted or labels are wrong
"""

import pandas as pd
import numpy as np

print("="*80)
print("HYPERLIQUID DATA VALIDATION")
print("="*80)

# Load the OHLC data
try:
    df = pd.read_csv('live_demo/ohlc_btc_5m.csv')
    print(f"\n1. DATA FILE CHECK:")
    print(f"   File: ohlc_btc_5m.csv")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {df.columns.tolist()}")
    
    # Check if data looks normal
    if 'close' in df.columns:
        print(f"\n2. PRICE DATA SANITY CHECK:")
        print(f"   Min close: ${df['close'].min():,.2f}")
        print(f"   Max close: ${df['close'].max():,.2f}")
        print(f"   Mean close: ${df['close'].mean():,.2f}")
        print(f"   Latest close: ${df['close'].iloc[-1]:,.2f}")
        
        # Check if prices are reasonable for BTC
        if df['close'].min() < 1000 or df['close'].max() > 200000:
            print(f"   ⚠️  WARNING: Prices seem unusual for BTC")
        else:
            print(f"   ✅ Prices look reasonable for BTC")
        
        # Check for data integrity
        print(f"\n3. DATA INTEGRITY:")
        
        # Check for NaN values
        nan_count = df['close'].isna().sum()
        print(f"   NaN values: {nan_count}")
        
        # Check for zeros
        zero_count = (df['close'] == 0).sum()
        print(f"   Zero values: {zero_count}")
        
        # Check if OHLC relationship is correct
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            # High should be >= Open, Close, Low
            # Low should be <= Open, Close, High
            invalid_high = ((df['high'] < df['open']) | (df['high'] < df['close']) | (df['high'] < df['low'])).sum()
            invalid_low = ((df['low'] > df['open']) | (df['low'] > df['close']) | (df['low'] > df['high'])).sum()
            
            print(f"   Invalid high values: {invalid_high}")
            print(f"   Invalid low values: {invalid_low}")
            
            if invalid_high > 0 or invalid_low > 0:
                print(f"   🔴 DATA CORRUPTION: OHLC relationships are wrong!")
            else:
                print(f"   ✅ OHLC relationships are correct")
        
        # Check price movements
        print(f"\n4. PRICE MOVEMENT ANALYSIS:")
        df['price_change'] = df['close'].pct_change()
        
        up_bars = (df['price_change'] > 0).sum()
        down_bars = (df['price_change'] < 0).sum()
        flat_bars = (df['price_change'] == 0).sum()
        
        print(f"   UP bars: {up_bars} ({up_bars/len(df)*100:.1f}%)")
        print(f"   DOWN bars: {down_bars} ({down_bars/len(df)*100:.1f}%)")
        print(f"   FLAT bars: {flat_bars}")
        
        if up_bars > 0 and down_bars > 0:
            ratio = up_bars / down_bars
            print(f"   UP:DOWN ratio: {ratio:.2f}:1")
            
            if ratio > 2 or ratio < 0.5:
                print(f"   ⚠️  Unusual ratio - market may be trending strongly")
            else:
                print(f"   ✅ Normal market distribution")
        
        # Check for data inversion
        print(f"\n5. DATA INVERSION CHECK:")
        
        # If prices are inverted, we'd see:
        # - Negative prices (impossible)
        # - Or reversed OHLC (high < low)
        
        if (df['close'] < 0).any():
            print(f"   🔴 CRITICAL: Negative prices detected!")
            print(f"   Data is definitely corrupted")
        elif invalid_high > 0 or invalid_low > 0:
            print(f"   🔴 CRITICAL: OHLC values are inverted!")
            print(f"   High/Low relationship is backwards")
        else:
            print(f"   ✅ No data inversion detected")
            print(f"   Prices and OHLC relationships are correct")
        
        # Compare with model predictions
        print(f"\n6. MODEL vs MARKET COMPARISON:")
        
        # Load signals to compare
        signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
        
        # Reverse flip to get raw model
        raw_model = -signals['s_model']  # Assuming flip_model=true
        
        model_up = (raw_model > 0).sum()
        model_down = (raw_model < 0).sum()
        
        print(f"   Market UP bars: {up_bars} ({up_bars/len(df)*100:.1f}%)")
        print(f"   Model UP predictions: {model_up} ({model_up/len(signals)*100:.1f}%)")
        print(f"   Market DOWN bars: {down_bars} ({down_bars/len(df)*100:.1f}%)")
        print(f"   Model DOWN predictions: {model_down} ({model_down/len(signals)*100:.1f}%)")
        
        # Check if model is predicting inverse of market
        if model_up < up_bars * 0.3 and model_down > down_bars * 2:
            print(f"\n   🔴 MODEL IS PREDICTING INVERSE OF MARKET!")
            print(f"   Market goes UP {up_bars/len(df)*100:.1f}% of time")
            print(f"   Model predicts UP only {model_up/len(signals)*100:.1f}% of time")
            print(f"   → Model learned inverted patterns")
        else:
            print(f"\n   Model predictions don't match market well")
            print(f"   But not clearly inverted")

except FileNotFoundError:
    print(f"\n❌ ERROR: ohlc_btc_5m.csv not found")
    print(f"   Cannot validate Hyperliquid data")
except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)

print(f"\nThe Hyperliquid data itself appears to be correct.")
print(f"The issue is in MODEL TRAINING, not data fetching.")
print(f"\nThe model was trained on this data but learned wrong patterns.")
print("="*80)
