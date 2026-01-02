"""
Show what data the 1h bot has collected
"""
import os
import json
from datetime import datetime

print("=" * 80)
print("1H BOT DATA COLLECTION STATUS")
print("=" * 80)
print()

print("🔍 Checking for collected bars/data...")
print("-" * 80)
print()

# Check JSONL log files (this is where the bot writes data)
log_dirs = [
    'paper_trading_outputs/1h/logs/market',
    'paper_trading_outputs/1h/logs/signals',
    'paper_trading_outputs/1h/logs/ensemble',
]

total_records = 0

for log_dir in log_dirs:
    if os.path.exists(log_dir):
        print(f"📁 {log_dir}:")
        
        # Find all JSONL files
        record_count = 0
        latest_time = None
        
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith('.jsonl'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r') as f:
                            lines = f.readlines()
                            record_count += len(lines)
                            
                            # Try to get timestamp from last line
                            if lines:
                                try:
                                    last_record = json.loads(lines[-1])
                                    if 'sanitized' in last_record and 'ts' in last_record['sanitized']:
                                        ts = last_record['sanitized']['ts']
                                        latest_time = datetime.fromtimestamp(ts / 1000)
                                except:
                                    pass
                    except:
                        pass
        
        if record_count > 0:
            print(f"   ✅ Found {record_count} records")
            if latest_time:
                print(f"   📅 Latest data: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
            total_records += record_count
        else:
            print(f"   ⏳ No records yet")
        print()
    else:
        print(f"❌ {log_dir}: Directory doesn't exist")
        print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

if total_records > 0:
    print(f"✅ Bot has collected data: {total_records} total records")
    print()
    print("However, these appear to be OLD records from previous runs.")
    print("The bot may be running but not writing NEW data yet.")
else:
    print("⏳ No data collected yet")
    print()
    print("This means:")
    print("1. Bot is still initializing")
    print("2. Bot is waiting for first hourly candle to complete")
    print("3. Bot may have an issue preventing data collection")

print()
print("💡 TO SEE LIVE ACTIVITY:")
print("-" * 80)
print("The 1h bot collects data every hour (at the top of each hour).")
print()
print("Current time:", datetime.now().strftime('%H:%M:%S'))
print("Next expected update: Top of next hour (e.g., 17:00:00)")
print()
print("Check again after the next full hour to see if new data appears.")
print()
print("=" * 80)
