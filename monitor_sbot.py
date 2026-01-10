"""
Monitor S_bot signal to verify it becomes active
Run this after restarting the bot
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import time

print("="*80)
print("S_BOT MONITORING")
print("="*80)

signals_path = Path("paper_trading_outputs/5m/sheets_fallback/signals.csv")

if not signals_path.exists():
    print("[ERROR] Signals file not found!")
    print(f"  Path: {signals_path}")
    exit(1)

print(f"Monitoring: {signals_path}")
print(f"Started: {datetime.now()}")
print("\nPress Ctrl+C to stop\n")

try:
    while True:
        df = pd.read_csv(signals_path)
        
        # Get latest 100 signals
        recent = df.tail(100)
        
        # Calculate statistics
        s_bot_nonzero = (recent['S_bot'] != 0).sum()
        s_bot_pct = s_bot_nonzero / len(recent) * 100
        s_bot_mean = recent['S_bot'].mean()
        s_bot_std = recent['S_bot'].std()
        
        # Also check other signals for comparison
        s_top_nonzero = (recent['S_top'] != 0).sum()
        s_mood_nonzero = (recent['S_mood'] != 0).sum()
        funding_nonzero = (recent['funding'] != 0).sum()
        
        # Clear screen and print status
        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] " +
              f"S_bot: {s_bot_pct:.1f}% active ({s_bot_nonzero}/100) | " +
              f"Mean: {s_bot_mean:.6f} | " +
              f"S_top: {s_top_nonzero}/100 | " +
              f"S_mood: {s_mood_nonzero}/100", end='', flush=True)
        
        # Check if S_bot is working
        if s_bot_nonzero > 0:
            print(f"\n\n[SUCCESS] S_bot is ACTIVE!")
            print(f"  Non-zero signals: {s_bot_nonzero} out of 100 ({s_bot_pct:.1f}%)")
            print(f"  Mean value: {s_bot_mean:.6f}")
            print(f"  Std dev: {s_bot_std:.6f}")
            print(f"\nAll signals status:")
            print(f"  S_top: {s_top_nonzero}/100 ({s_top_nonzero/len(recent)*100:.1f}%)")
            print(f"  S_bot: {s_bot_nonzero}/100 ({s_bot_pct:.1f}%)")
            print(f"  S_mood: {s_mood_nonzero}/100 ({s_mood_nonzero/len(recent)*100:.1f}%)")
            print(f"  funding: {funding_nonzero}/100 ({funding_nonzero/len(recent)*100:.1f}%)")
            break
        
        time.sleep(10)  # Check every 10 seconds

except KeyboardInterrupt:
    print("\n\nMonitoring stopped by user")
    
print("\n" + "="*80)
