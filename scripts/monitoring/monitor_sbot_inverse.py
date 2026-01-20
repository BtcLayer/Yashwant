"""
Monitor S_bot status after inverse logic fix
"""
import pandas as pd
import time
from datetime import datetime

print("="*80)
print("S_BOT MONITORING - INVERSE LOGIC FIX")
print("="*80)

signals_file = 'paper_trading_outputs/5m/sheets_fallback/signals.csv'

print(f"\nMonitoring: {signals_file}")
print("Checking every 30 seconds for 5 minutes...")
print("\nPress Ctrl+C to stop\n")

start_time = time.time()
check_count = 0

try:
    while time.time() - start_time < 300:  # 5 minutes
        check_count += 1
        
        try:
            # Load signals
            df = pd.read_csv(signals_file)
            
            # Get recent data (last 50 rows)
            recent = df.tail(50)
            
            # Check S_bot status
            s_bot_nonzero = (recent['S_bot'] != 0).sum()
            s_bot_mean = recent['S_bot'].mean()
            s_bot_std = recent['S_bot'].std()
            
            # Check other signals for comparison
            s_top_nonzero = (recent['S_top'] != 0).sum()
            s_mood_nonzero = (recent['S_mood'] != 0).sum()
            
            # Display status
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Check #{check_count}")
            print(f"  Total signals: {len(df)}")
            print(f"  Recent 50 bars:")
            print(f"    S_bot  active: {s_bot_nonzero}/50 ({s_bot_nonzero/50*100:.1f}%)")
            print(f"    S_top  active: {s_top_nonzero}/50 ({s_top_nonzero/50*100:.1f}%)")
            print(f"    S_mood active: {s_mood_nonzero}/50 ({s_mood_nonzero/50*100:.1f}%)")
            print(f"    S_bot  mean: {s_bot_mean:.8f}")
            print(f"    S_bot  std:  {s_bot_std:.8f}")
            
            # Check if S_bot is working
            if s_bot_nonzero > 0:
                print(f"\n  ✓ S_BOT IS ACTIVE! ({s_bot_nonzero} non-zero values)")
                
                # Show sample values
                s_bot_values = recent[recent['S_bot'] != 0]['S_bot'].head(5)
                print(f"  Sample S_bot values:")
                for val in s_bot_values:
                    print(f"    {val:.8f}")
            else:
                print(f"\n  ✗ S_bot still zero")
            
            print()
            
        except FileNotFoundError:
            print(f"[{timestamp}] Waiting for signals file to be created...")
        except Exception as e:
            print(f"[{timestamp}] Error: {e}")
        
        # Wait 30 seconds
        time.sleep(30)
        
except KeyboardInterrupt:
    print("\n\nMonitoring stopped by user")

print("\n" + "="*80)
print("MONITORING COMPLETE")
print("="*80)

# Final summary
try:
    df = pd.read_csv(signals_file)
    recent = df.tail(100)
    
    s_bot_active = (recent['S_bot'] != 0).sum()
    s_top_active = (recent['S_top'] != 0).sum()
    s_mood_active = (recent['S_mood'] != 0).sum()
    
    print(f"\nFinal Status (last 100 bars):")
    print(f"  S_bot:  {s_bot_active}/100 ({s_bot_active/100*100:.1f}%) active")
    print(f"  S_top:  {s_top_active}/100 ({s_top_active/100*100:.1f}%) active")
    print(f"  S_mood: {s_mood_active}/100 ({s_mood_active/100*100:.1f}%) active")
    
    if s_bot_active > 0:
        print(f"\n✓ SUCCESS: S_bot is working with inverse logic!")
        print(f"  Ready to proceed with retraining")
    else:
        print(f"\n✗ S_bot still not active")
        print(f"  Need to investigate further")
        
except Exception as e:
    print(f"\nCould not load final status: {e}")

print("="*80)
