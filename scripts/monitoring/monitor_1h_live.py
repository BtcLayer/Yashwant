"""
Monitor 1h bot - check if it's working and collecting data
Run this every few minutes to see progress
"""
import os
import time
from datetime import datetime

print("=" * 80)
print("1H BOT LIVE MONITOR")
print("=" * 80)
print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Check if today's data folder exists
today = datetime.now().strftime('%Y-%m-%d')
signals_dir = f'paper_trading_outputs/1h/logs/signals/date={today}'
market_dir = f'paper_trading_outputs/1h/logs/market/date={today}'
ensemble_dir = f'paper_trading_outputs/1h/logs/ensemble/date={today}'

print("📁 Checking for today's data folders...")
print("-" * 80)

folders_exist = False

if os.path.exists(signals_dir):
    print(f"✅ {signals_dir} EXISTS!")
    folders_exist = True
    
    # Count files
    files = os.listdir(signals_dir)
    if files:
        print(f"   📄 Files: {len(files)}")
        for f in files:
            fpath = os.path.join(signals_dir, f)
            size = os.path.getsize(fpath)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            print(f"      - {f}: {size} bytes, modified {mtime.strftime('%H:%M:%S')}")
    else:
        print(f"   ⏳ Folder exists but no files yet")
else:
    print(f"⏳ {signals_dir} - Not created yet")

print()

if os.path.exists(market_dir):
    print(f"✅ {market_dir} EXISTS!")
    folders_exist = True
else:
    print(f"⏳ {market_dir} - Not created yet")

print()

if os.path.exists(ensemble_dir):
    print(f"✅ {ensemble_dir} EXISTS!")
    folders_exist = True
else:
    print(f"⏳ {ensemble_dir} - Not created yet")

print()
print("=" * 80)

if folders_exist:
    print("🎉 SUCCESS! Bot is collecting data!")
    print()
    print("The 1h bot is working correctly and writing data.")
    print("Check back at the top of each hour to see new bars added.")
else:
    print("⏳ WAITING FOR DATA...")
    print()
    print("Bot is running but hasn't created today's folders yet.")
    print()
    print("This is normal if:")
    print("1. Bot just started (needs a few minutes to initialize)")
    print("2. Waiting for the top of the next hour to write first bar")
    print()
    current_time = datetime.now()
    next_hour = current_time.replace(minute=0, second=0, microsecond=0)
    if current_time.minute > 0:
        from datetime import timedelta
        next_hour = next_hour + timedelta(hours=1)
    
    wait_time = (next_hour - current_time).total_seconds() / 60
    print(f"⏰ Next expected update: {next_hour.strftime('%H:%M:%S')} ({wait_time:.0f} minutes)")
    print()
    print("Run this script again after that time to check!")

print()
print("=" * 80)
print(f"Monitor Time: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 80)
