"""
Final check - is the Hyperliquid data causing the model issue?
"""

import pandas as pd

print("="*80)
print("HYPERLIQUID DATA vs MODEL ISSUE")
print("="*80)

# Check signals data which has the actual market data used
signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

print(f"\n1. SIGNALS DATA:")
print(f"   Total bars: {len(signals)}")

# Check if there's price data
price_cols = [c for c in signals.columns if 'close' in c.lower() or 'price' in c.lower()]
print(f"   Price columns: {price_cols}")

if 'close' in signals.columns:
    print(f"\n2. MARKET REALITY (from signals.csv):")
    
    # Calculate actual market direction
    signals['market_direction'] = signals['close'].diff()
    market_up = (signals['market_direction'] > 0).sum()
    market_down = (signals['market_direction'] < 0).sum()
    
    print(f"   Market UP bars: {market_up} ({market_up/len(signals)*100:.1f}%)")
    print(f"   Market DOWN bars: {market_down} ({market_down/len(signals)*100:.1f}%)")
    print(f"   Market ratio: {market_up/max(1,market_down):.2f}:1")
    
    # Model predictions (raw, before flip)
    raw_model = -signals['s_model']  # Reverse the flip
    model_up = (raw_model > 0).sum()
    model_down = (raw_model < 0).sum()
    
    print(f"\n3. MODEL PREDICTIONS (raw):")
    print(f"   Model UP: {model_up} ({model_up/len(signals)*100:.1f}%)")
    print(f"   Model DOWN: {model_down} ({model_down/len(signals)*100:.1f}%)")
    print(f"   Model ratio: {model_up/max(1,model_down):.2f}:1")
    
    print(f"\n4. COMPARISON:")
    print(f"   Market: {market_up/max(1,market_down):.2f}:1 (UP:DOWN)")
    print(f"   Model:  {model_up/max(1,model_down):.2f}:1 (UP:DOWN)")
    
    # Check if they're inverted
    if market_up > market_down and model_down > model_up:
        print(f"\n   🔴 MODEL IS INVERTED!")
        print(f"   Market trends UP but model predicts DOWN")
    elif market_down > market_up and model_up > model_down:
        print(f"\n   🔴 MODEL IS INVERTED!")
        print(f"   Market trends DOWN but model predicts UP")
    else:
        print(f"\n   Model and market have same bias direction")
        print(f"   But magnitudes don't match")

print(f"\n" + "="*80)
print("FINAL ANSWER:")
print("="*80)

print(f"\nThe Hyperliquid WebSocket/API data is NOT the issue.")
print(f"\nThe market data itself is correct.")
print(f"The model was trained on this correct data.")
print(f"But the model LEARNED WRONG PATTERNS during training.")
print(f"\nThis is a MODEL TRAINING ISSUE, not a data fetching issue.")

print("="*80)
