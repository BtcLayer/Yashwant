"""
If Jan 5 model worked yesterday but not today, what changed?
Investigate environmental/data changes, not model
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

print("="*80)
print("WHAT CHANGED BETWEEN YESTERDAY (WORKING) AND TODAY (BROKEN)?")
print("="*80)

# Load signals
signals = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
signals['datetime'] = pd.to_datetime(signals['ts_iso'], format='ISO8601', errors='coerce')
signals['date'] = signals['datetime'].dt.date

yesterday = (datetime.now() - timedelta(days=1)).date()
today = datetime.now().date()

print(f"\nYesterday: {yesterday}")
print(f"Today: {today}")

# Compare yesterday vs today
yesterday_signals = signals[signals['date'] == yesterday]
today_signals = signals[signals['date'] == today]

print(f"\n--- YESTERDAY ({yesterday}) - WORKING ---")
if len(yesterday_signals) > 0:
    print(f"Total signals: {len(yesterday_signals)}")
    print(f"Neutral (dir=0): {(yesterday_signals['dir']==0).sum()} ({(yesterday_signals['dir']==0).sum()/len(yesterday_signals)*100:.1f}%)")
    print(f"BUY (dir=1): {(yesterday_signals['dir']==1).sum()} ({(yesterday_signals['dir']==1).sum()/len(yesterday_signals)*100:.1f}%)")
    print(f"Mean p_up: {yesterday_signals['p_up'].mean():.3f}")
    print(f"Mean p_down: {yesterday_signals['p_down'].mean():.3f}")
    print(f"Mean p_neutral: {yesterday_signals['p_neutral'].mean():.3f}")
    print(f"Mean confidence: {yesterday_signals[['p_up', 'p_down']].max(axis=1).mean():.3f}")
    print(f"Non-zero alpha: {(yesterday_signals['alpha'] != 0).sum()} ({(yesterday_signals['alpha']!=0).sum()/len(yesterday_signals)*100:.1f}%)")
    
    # Check S_top and S_bot
    print(f"\nCohort signals:")
    print(f"  S_top non-zero: {(yesterday_signals['S_top'] != 0).sum()} ({(yesterday_signals['S_top']!=0).sum()/len(yesterday_signals)*100:.1f}%)")
    print(f"  S_bot non-zero: {(yesterday_signals['S_bot'] != 0).sum()} ({(yesterday_signals['S_bot']!=0).sum()/len(yesterday_signals)*100:.1f}%)")
    print(f"  S_top mean: {yesterday_signals['S_top'].mean():.6f}")
    print(f"  S_bot mean: {yesterday_signals['S_bot'].mean():.6f}")
else:
    print("No signals from yesterday")

print(f"\n--- TODAY ({today}) - BROKEN ---")
if len(today_signals) > 0:
    print(f"Total signals: {len(today_signals)}")
    print(f"Neutral (dir=0): {(today_signals['dir']==0).sum()} ({(today_signals['dir']==0).sum()/len(today_signals)*100:.1f}%)")
    print(f"BUY (dir=1): {(today_signals['dir']==1).sum()} ({(today_signals['dir']==1).sum()/len(today_signals)*100:.1f}%)")
    print(f"Mean p_up: {today_signals['p_up'].mean():.3f}")
    print(f"Mean p_down: {today_signals['p_down'].mean():.3f}")
    print(f"Mean p_neutral: {today_signals['p_neutral'].mean():.3f}")
    print(f"Mean confidence: {today_signals[['p_up', 'p_down']].max(axis=1).mean():.3f}")
    print(f"Non-zero alpha: {(today_signals['alpha'] != 0).sum()} ({(today_signals['alpha']!=0).sum()/len(today_signals)*100:.1f}%)")
    
    # Check S_top and S_bot
    print(f"\nCohort signals:")
    print(f"  S_top non-zero: {(today_signals['S_top'] != 0).sum()} ({(today_signals['S_top']!=0).sum()/len(today_signals)*100:.1f}%)")
    print(f"  S_bot non-zero: {(today_signals['S_bot'] != 0).sum()} ({(today_signals['S_bot']!=0).sum()/len(today_signals)*100:.1f}%)")
    print(f"  S_top mean: {today_signals['S_top'].mean():.6f}")
    print(f"  S_bot mean: {today_signals['S_bot'].mean():.6f}")
else:
    print("No signals from today")

# Check market data freshness
print("\n" + "="*80)
print("MARKET DATA FRESHNESS")
print("="*80)

cache_5m = Path("paper_trading_outputs/cache/BTCUSDT_5m_1000.csv")
if cache_5m.exists():
    df_cache = pd.read_csv(cache_5m)
    df_cache['datetime'] = pd.to_datetime(df_cache['ts'], unit='ms')
    
    print(f"\nCached 5m data:")
    print(f"  Last update: {df_cache['datetime'].max()}")
    print(f"  Age: {(datetime.now() - df_cache['datetime'].max()).total_seconds() / 3600:.1f} hours")
    
    # Check if cache was updated today
    cache_dates = df_cache['datetime'].dt.date.unique()
    print(f"  Dates in cache: {sorted(cache_dates)[-3:]}")  # Last 3 dates
    
    if today in cache_dates:
        print(f"  ✓ Cache includes today's data")
    else:
        print(f"  ✗ Cache does NOT include today's data!")

# Check if bot restarted today
print("\n" + "="*80)
print("BOT RESTART ANALYSIS")
print("="*80)

# Look for gaps in signal timestamps
if len(signals) > 0:
    signals_sorted = signals.sort_values('datetime')
    time_diffs = signals_sorted['datetime'].diff()
    
    # Find gaps > 10 minutes (more than 2 bars)
    large_gaps = time_diffs[time_diffs > timedelta(minutes=10)]
    
    if len(large_gaps) > 0:
        print(f"\nFound {len(large_gaps)} gaps in signals (>10 min):")
        for idx in large_gaps.index[-5:]:  # Last 5 gaps
            gap_time = signals_sorted.loc[idx, 'datetime']
            gap_size = time_diffs.loc[idx]
            print(f"  {gap_time}: {gap_size}")
    else:
        print("\nNo significant gaps in signals")

print("\n" + "="*80)
print("KEY DIFFERENCES")
print("="*80)

if len(yesterday_signals) > 0 and len(today_signals) > 0:
    # Calculate differences
    neutral_diff = (today_signals['dir']==0).sum()/len(today_signals)*100 - (yesterday_signals['dir']==0).sum()/len(yesterday_signals)*100
    conf_diff = today_signals[['p_up', 'p_down']].max(axis=1).mean() - yesterday_signals[['p_up', 'p_down']].max(axis=1).mean()
    pneutral_diff = today_signals['p_neutral'].mean() - yesterday_signals['p_neutral'].mean()
    
    print(f"\n1. Neutral rate: {neutral_diff:+.1f}% change")
    print(f"2. Confidence: {conf_diff:+.3f} change")
    print(f"3. p_neutral: {pneutral_diff:+.3f} change")
    
    # S_bot comparison
    yesterday_sbot_nonzero = (yesterday_signals['S_bot'] != 0).sum()
    today_sbot_nonzero = (today_signals['S_bot'] != 0).sum()
    print(f"4. S_bot non-zero: {yesterday_sbot_nonzero} -> {today_sbot_nonzero} ({today_sbot_nonzero - yesterday_sbot_nonzero:+d})")
    
    if yesterday_sbot_nonzero > 0 and today_sbot_nonzero == 0:
        print("\n*** CRITICAL: S_bot worked yesterday but is ZERO today! ***")

print("\n" + "="*80)
