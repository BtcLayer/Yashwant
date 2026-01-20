"""
Deep diagnostic of 1h bot - check what's really happening
"""
import os
import sys

print("=" * 80)
print("1H BOT DEEP DIAGNOSTIC")
print("=" * 80)
print()

# Check if bot is actually writing any files
print("🔍 Checking for ANY output files from 1h bot...")
print("-" * 80)

# Check live_demo_1h directory
base_dirs = [
    'live_demo_1h',
    'live_demo_1h/emitters',
    'live_demo_1h/ops',
    'paper_trading_outputs'
]

for dir_path in base_dirs:
    if os.path.exists(dir_path):
        files = []
        for root, dirs, filenames in os.walk(dir_path):
            for f in filenames:
                if f.endswith(('.csv', '.log', '.json', '.jsonl')):
                    full_path = os.path.join(root, f)
                    stat = os.stat(full_path)
                    files.append((full_path, stat.st_size, stat.st_mtime))
        
        if files:
            print(f"\n📁 {dir_path}:")
            # Sort by modification time
            files.sort(key=lambda x: x[2], reverse=True)
            for fpath, size, mtime in files[:10]:  # Show top 10 most recent
                from datetime import datetime
                mod_time = datetime.fromtimestamp(mtime)
                print(f"   {os.path.basename(fpath)}: {size} bytes, modified {mod_time}")
        else:
            print(f"\n⚠️ {dir_path}: No relevant files found")
    else:
        print(f"\n❌ {dir_path}: Directory doesn't exist")

print()
print("-" * 80)

# Check config warmup issue
print("\n⚠️ POTENTIAL ISSUE DETECTED:")
print("-" * 80)
print("Config shows: warmup_bars = 1000")
print("For 1h timeframe: 1000 bars = 1000 HOURS = 41+ DAYS!")
print()
print("This means the bot won't trade until it has 41 days of data.")
print("This is likely TOO HIGH for testing.")
print()
print("RECOMMENDATION:")
print("1. Reduce warmup_bars to 50-100 for 1h timeframe")
print("2. Restart the bot")
print("3. Should see signals within 1-2 hours")

print()
print("=" * 80)
