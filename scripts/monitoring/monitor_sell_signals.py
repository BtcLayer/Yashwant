"""
Real-time SELL Signal Monitor
Tracks when model predicts DOWN and if SELL signals are generated
"""

import pandas as pd
import time
from datetime import datetime

def check_sell_signals():
    """Check if SELL signals are being generated"""
    try:
        df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
        
        # Get recent signals (last 20)
        recent = df.tail(20)
        
        # Count DOWN predictions and SELL signals
        down_preds = (recent['s_model'] < 0).sum()
        sell_signals = (recent['dir'] == -1).sum()
        
        # Overall stats
        total_down = (df['s_model'] < 0).sum()
        total_sell = (df['dir'] == -1).sum()
        
        return {
            'recent_down': down_preds,
            'recent_sell': sell_signals,
            'total_down': total_down,
            'total_sell': total_sell,
            'total_signals': len(df),
            'recent_signals': recent,
            'timestamp': datetime.now()
        }
    except Exception as e:
        return {'error': str(e)}

def print_status(data, iteration):
    """Print monitoring status"""
    print("\n" + "="*80)
    print(f"SELL SIGNAL MONITOR - Update #{iteration}")
    print(f"Time: {data['timestamp'].strftime('%H:%M:%S')}")
    print("="*80)
    
    if 'error' in data:
        print(f"ERROR: {data['error']}")
        return
    
    print(f"\n📊 OVERALL STATS:")
    print(f"   Total signals: {data['total_signals']}")
    print(f"   DOWN predictions: {data['total_down']}")
    print(f"   SELL signals: {data['total_sell']}")
    
    if data['total_sell'] > 0:
        conversion = data['total_sell'] / max(1, data['total_down']) * 100
        print(f"   Conversion rate: {conversion:.1f}%")
        print(f"\n   ✅ FIX IS WORKING! SELL signals are being generated!")
    
    print(f"\n📈 RECENT ACTIVITY (Last 20 signals):")
    print(f"   DOWN predictions: {data['recent_down']}")
    print(f"   SELL signals: {data['recent_sell']}")
    
    if data['recent_down'] > 0:
        if data['recent_sell'] > 0:
            print(f"   ✅ DOWN predictions → SELL signals (FIX WORKING!)")
        else:
            print(f"   ❌ DOWN predictions but NO SELL signals (FIX NOT WORKING)")
    
    # Show last 5 signals
    print(f"\n📋 LAST 5 SIGNALS:")
    for idx, row in data['recent_signals'].tail(5).iterrows():
        s_model = row['s_model']
        direction = row['dir']
        dir_str = "BUY" if direction == 1 else ("SELL" if direction == -1 else "NEUT")
        
        # Check if conversion is correct
        expected = "SELL" if s_model < 0 else "BUY"
        status = "✅" if (s_model < 0 and direction == -1) or (s_model > 0 and direction == 1) else "❌"
        
        ts = row['ts_iso'][-8:] if len(row['ts_iso']) > 8 else row['ts_iso']
        print(f"   {ts}: s_model={s_model:+.4f} → {dir_str} {status}")
    
    print("\n" + "="*80)

# Initial baseline
print("Starting SELL Signal Monitor...")
print("Checking every 30 seconds for SELL signals...")
print("Press Ctrl+C to stop\n")

baseline = check_sell_signals()
if 'error' not in baseline:
    print(f"Baseline: {baseline['total_sell']} SELL signals out of {baseline['total_down']} DOWN predictions")

iteration = 0
try:
    while True:
        time.sleep(30)
        iteration += 1
        
        data = check_sell_signals()
        print_status(data, iteration)
        
        # Check if we got our first SELL signal
        if 'total_sell' in data and baseline and 'total_sell' in baseline:
            if data['total_sell'] > baseline['total_sell']:
                new_sells = data['total_sell'] - baseline['total_sell']
                print(f"\n🎉 NEW SELL SIGNALS DETECTED: +{new_sells}")
                print(f"✅ FIX IS CONFIRMED WORKING!")
                
except KeyboardInterrupt:
    print("\n\nMonitoring stopped")
    final = check_sell_signals()
    if 'total_sell' in final:
        print(f"\nFinal: {final['total_sell']} SELL signals")
        if final['total_sell'] > baseline.get('total_sell', 0):
            print("✅ Fix is working - SELL signals appeared!")
        else:
            print("⏳ No new SELL signals yet - keep monitoring")
