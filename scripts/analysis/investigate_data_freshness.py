"""
Step 3: Check Data Freshness and Market Data
Investigate if we need to fetch new data daily
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

print("="*80)
print("STEP 3: DATA FRESHNESS ANALYSIS")
print("="*80)

# Check cached OHLC data
cache_dir = Path("paper_trading_outputs/cache")
if cache_dir.exists():
    print("\n--- CACHED DATA FILES ---")
    for file in cache_dir.glob("*.csv"):
        if file.stat().st_size > 0:
            df = pd.read_csv(file)
            if len(df) > 0 and 'ts' in df.columns:
                # Convert timestamp to datetime
                df['datetime'] = pd.to_datetime(df['ts'], unit='ms')
                first_date = df['datetime'].min()
                last_date = df['datetime'].max()
                age_hours = (datetime.now() - last_date).total_seconds() / 3600
                
                print(f"\n{file.name}:")
                print(f"  Rows: {len(df)}")
                print(f"  First: {first_date}")
                print(f"  Last: {last_date}")
                print(f"  Age: {age_hours:.1f} hours ago")
                print(f"  Status: {'STALE' if age_hours > 1 else 'FRESH'}")

# Check signals file timestamps
print("\n--- SIGNALS TIMESTAMP ANALYSIS ---")
signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

if 'ts_iso' in signals.columns:
    # Parse timestamps
    signals['datetime'] = pd.to_datetime(signals['ts_iso'])
    
    first_signal = signals['datetime'].min()
    last_signal = signals['datetime'].max()
    now = datetime.now()
    
    print(f"\nFirst signal: {first_signal}")
    print(f"Last signal: {last_signal}")
    print(f"Current time: {now}")
    print(f"Signal age: {(now - last_signal).total_seconds() / 60:.1f} minutes")
    
    # Check if signals are continuous
    time_diffs = signals['datetime'].diff()
    expected_interval = timedelta(minutes=5)
    gaps = time_diffs[time_diffs > expected_interval * 1.5]
    
    print(f"\nExpected interval: 5 minutes")
    print(f"Gaps detected: {len(gaps)}")
    if len(gaps) > 0:
        print(f"Largest gap: {gaps.max()}")

# Check if data spans today
print("\n--- DATA COVERAGE ---")
today = datetime.now().date()
yesterday = today - timedelta(days=1)

signals['date'] = signals['datetime'].dt.date
date_counts = signals['date'].value_counts().sort_index()

print(f"\nSignals by date:")
for date, count in date_counts.tail(5).items():
    print(f"  {date}: {count} signals")

today_signals = signals[signals['date'] == today]
print(f"\nToday's signals: {len(today_signals)}")
if len(today_signals) > 0:
    print(f"  First: {today_signals['datetime'].min()}")
    print(f"  Last: {today_signals['datetime'].max()}")

# Check model file modification time
print("\n--- MODEL FILES ---")
model_dir = Path("live_demo/models")
if model_dir.exists():
    for model_file in model_dir.glob("*.keras"):
        mod_time = datetime.fromtimestamp(model_file.stat().st_mtime)
        age_days = (datetime.now() - mod_time).days
        print(f"\n{model_file.name}:")
        print(f"  Modified: {mod_time}")
        print(f"  Age: {age_days} days")

# Check cohort files
print("\n--- COHORT FILES ---")
cohort_files = [
    "live_demo/assets/top_cohort.csv",
    "live_demo/assets/bottom_cohort.csv"
]

for cohort_file in cohort_files:
    path = Path(cohort_file)
    if path.exists():
        df = pd.read_csv(path)
        mod_time = datetime.fromtimestamp(path.stat().st_mtime)
        age_days = (datetime.now() - mod_time).days
        
        print(f"\n{path.name}:")
        print(f"  Rows: {len(df)}")
        print(f"  Modified: {mod_time}")
        print(f"  Age: {age_days} days")
        print(f"  Columns: {list(df.columns)}")
        
        # Check if file has data
        if len(df) == 0:
            print(f"  WARNING: File is EMPTY!")
    else:
        print(f"\n{cohort_file}: NOT FOUND")

print("\n" + "="*80)
print("DIAGNOSIS - STEP 3")
print("="*80)

print("\nKey findings:")
print("1. Check if cached data is stale (>1 hour old)")
print("2. Check if cohort files exist and have data")
print("3. Check if model files are recent")
print("4. Verify signals are being generated for today")

print("\n" + "="*80)
