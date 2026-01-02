"""
Find where the 1h bot is actually writing data
"""
import os
from datetime import datetime, timedelta

print("=" * 80)
print("FINDING 1H BOT OUTPUT FILES")
print("=" * 80)
print()

# Check all possible locations
locations = [
    'paper_trading_outputs/1h',
    'live_demo_1h/emitters',
    'live_demo_1h/ops',
    'paper_trading_outputs',
]

cutoff = datetime.now() - timedelta(hours=4)

print(f"Looking for files modified in last 4 hours (since {cutoff.strftime('%H:%M:%S')})")
print()

found_files = []

for location in locations:
    if os.path.exists(location):
        print(f"📁 Checking: {location}")
        for root, dirs, files in os.walk(location):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(filepath)
                    mod_time = datetime.fromtimestamp(mtime)
                    
                    if mod_time > cutoff:
                        size = os.path.getsize(filepath)
                        found_files.append((filepath, mod_time, size))
                except:
                    pass
        
        if found_files:
            print(f"   ✅ Found {len(found_files)} recent files")
        else:
            print(f"   ⏳ No recent files")
        print()

if found_files:
    print("=" * 80)
    print(f"RECENT FILES ({len(found_files)} total):")
    print("=" * 80)
    print()
    
    # Sort by modification time
    found_files.sort(key=lambda x: x[1], reverse=True)
    
    for filepath, mod_time, size in found_files[:20]:  # Show top 20
        rel_path = filepath.replace('\\', '/')
        print(f"{mod_time.strftime('%H:%M:%S')} | {size:>8} bytes | {rel_path}")
    
    if len(found_files) > 20:
        print(f"\n... and {len(found_files) - 20} more files")
else:
    print("=" * 80)
    print("⚠️ NO RECENT FILES FOUND")
    print("=" * 80)
    print()
    print("This could mean:")
    print("1. Bot is running but not writing output yet (still warming up)")
    print("2. Bot is writing to a different location")
    print("3. Bot encountered an error")
    print()
    print("Check the bot terminal for any error messages.")

print()
print("=" * 80)
