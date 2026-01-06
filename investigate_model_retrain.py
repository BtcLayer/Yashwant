"""
Investigate Model Changes - Was a new model trained yesterday?
Compare model performance before and after
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import json

print("="*80)
print("MODEL INVESTIGATION - Did retraining break the bot?")
print("="*80)

# Check model files and their timestamps
model_dir = Path("live_demo/models")
print("\n--- MODEL FILES ---")

model_files = []
if model_dir.exists():
    for model_file in sorted(model_dir.glob("*.keras")):
        mod_time = datetime.fromtimestamp(model_file.stat().st_mtime)
        size_mb = model_file.stat().st_size / (1024*1024)
        age_hours = (datetime.now() - mod_time).total_seconds() / 3600
        
        model_files.append({
            'name': model_file.name,
            'modified': mod_time,
            'age_hours': age_hours,
            'size_mb': size_mb
        })
        
        print(f"\n{model_file.name}:")
        print(f"  Modified: {mod_time}")
        print(f"  Age: {age_hours:.1f} hours ago ({age_hours/24:.1f} days)")
        print(f"  Size: {size_mb:.2f} MB")
        
        # Check if modified yesterday
        if 12 < age_hours < 36:
            print(f"  *** MODIFIED YESTERDAY! ***")

# Check LATEST.json manifest
latest_manifest = Path("live_demo/models/LATEST.json")
if latest_manifest.exists():
    print("\n--- LATEST.json MANIFEST ---")
    with open(latest_manifest, 'r') as f:
        manifest = json.load(f)
    
    print(json.dumps(manifest, indent=2))
    
    mod_time = datetime.fromtimestamp(latest_manifest.stat().st_mtime)
    print(f"\nManifest last updated: {mod_time}")
    print(f"Age: {(datetime.now() - mod_time).total_seconds() / 3600:.1f} hours ago")

# Check execution archives to see when performance changed
print("\n--- CHECKING EXECUTION HISTORY ---")

exec_file = Path("paper_trading_outputs/5m/sheets_fallback/executions_paper.csv")
if exec_file.exists():
    df = pd.read_csv(exec_file)
    df['datetime'] = pd.to_datetime(df['ts_iso'])
    df['date'] = df['datetime'].dt.date
    
    # Group by date
    daily_stats = df.groupby('date').agg({
        'side': 'count',
        'realized_pnl': 'sum'
    }).rename(columns={'side': 'trades', 'realized_pnl': 'pnl'})
    
    print("\nTrades by date:")
    print(daily_stats)

# Check signals by date to see when they became mostly neutral
print("\n--- SIGNAL QUALITY BY DATE ---")

signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')

# Parse timestamp (handle microseconds)
try:
    signals['datetime'] = pd.to_datetime(signals['ts_iso'], format='ISO8601')
except:
    signals['datetime'] = pd.to_datetime(signals['ts_iso'].str.split('.').str[0])

signals['date'] = signals['datetime'].dt.date

# Analyze by date
for date in sorted(signals['date'].unique())[-3:]:  # Last 3 days
    day_signals = signals[signals['date'] == date]
    
    print(f"\n{date}:")
    print(f"  Total signals: {len(day_signals)}")
    print(f"  dir=0 (neutral): {(day_signals['dir']==0).sum()} ({(day_signals['dir']==0).sum()/len(day_signals)*100:.1f}%)")
    print(f"  dir=1 (buy): {(day_signals['dir']==1).sum()} ({(day_signals['dir']==1).sum()/len(day_signals)*100:.1f}%)")
    print(f"  Mean p_neutral: {day_signals['p_neutral'].mean():.3f}")
    print(f"  Mean p_up: {day_signals['p_up'].mean():.3f}")
    print(f"  Mean p_down: {day_signals['p_down'].mean():.3f}")
    print(f"  Mean confidence: {day_signals[['p_up', 'p_down']].max(axis=1).mean():.3f}")
    print(f"  Non-zero alpha: {(day_signals['alpha'] != 0).sum()} ({(day_signals['alpha']!=0).sum()/len(day_signals)*100:.1f}%)")

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)

# Check if there's a clear date when things changed
yesterday = (datetime.now() - timedelta(days=1)).date()
today = datetime.now().date()

yesterday_signals = signals[signals['date'] == yesterday] if yesterday in signals['date'].values else pd.DataFrame()
today_signals = signals[signals['date'] == today] if today in signals['date'].values else pd.DataFrame()

if len(yesterday_signals) > 0 and len(today_signals) > 0:
    print(f"\nCOMPARISON: Yesterday vs Today")
    print(f"\nYesterday ({yesterday}):")
    print(f"  Neutral rate: {(yesterday_signals['dir']==0).sum()/len(yesterday_signals)*100:.1f}%")
    print(f"  Mean confidence: {yesterday_signals[['p_up', 'p_down']].max(axis=1).mean():.3f}")
    print(f"  Mean p_neutral: {yesterday_signals['p_neutral'].mean():.3f}")
    
    print(f"\nToday ({today}):")
    print(f"  Neutral rate: {(today_signals['dir']==0).sum()/len(today_signals)*100:.1f}%")
    print(f"  Mean confidence: {today_signals[['p_up', 'p_down']].max(axis=1).mean():.3f}")
    print(f"  Mean p_neutral: {today_signals['p_neutral'].mean():.3f}")
    
    # Check if there's a significant change
    yesterday_neutral_pct = (yesterday_signals['dir']==0).sum()/len(yesterday_signals)*100
    today_neutral_pct = (today_signals['dir']==0).sum()/len(today_signals)*100
    
    if today_neutral_pct - yesterday_neutral_pct > 20:
        print(f"\n*** SIGNIFICANT DEGRADATION DETECTED! ***")
        print(f"Neutral rate increased by {today_neutral_pct - yesterday_neutral_pct:.1f}%")

# Check for model retraining logs
print("\n--- CHECKING FOR RETRAINING LOGS ---")
retrain_logs = [
    "retraining_log.txt",
    "5m_new_model_err.log",
    "5m_new_model_std.log"
]

for log_file in retrain_logs:
    p = Path(log_file)
    if p.exists() and p.stat().st_size > 0:
        mod_time = datetime.fromtimestamp(p.stat().st_mtime)
        age_hours = (datetime.now() - mod_time).total_seconds() / 3600
        print(f"\n{log_file}:")
        print(f"  Modified: {mod_time}")
        print(f"  Age: {age_hours:.1f} hours ago")
        if 12 < age_hours < 36:
            print(f"  *** MODIFIED YESTERDAY! ***")

print("\n" + "="*80)
