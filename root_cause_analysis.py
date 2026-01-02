"""
ROOT CAUSE ANALYSIS - Why No SELL Trades After 17 Hours
"""

import pandas as pd
import json
from datetime import datetime, timedelta

print("="*80)
print("ROOT CAUSE ANALYSIS - SELL TRADES")
print("="*80)
print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# Load data
signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')

# Convert timestamps
signals_df['ts'] = pd.to_datetime(signals_df['ts_iso'])
exec_df['ts'] = pd.to_datetime(exec_df['ts_iso'])

# Get recent data (last 24 hours)
recent_signals = signals_df.tail(288)  # 288 5-min bars = 24 hours

print(f"\n1. DATA SUMMARY:")
print(f"   Total signals: {len(signals_df)}")
print(f"   Recent signals (24h): {len(recent_signals)}")
print(f"   Total executions: {len(exec_df)}")

# Check market movement
print(f"\n2. MARKET MOVEMENT (Last 24 Hours):")
if 'close' in recent_signals.columns:
    start_price = recent_signals.iloc[0]['close']
    end_price = recent_signals.iloc[-1]['close']
    price_change = ((end_price - start_price) / start_price) * 100
    
    print(f"   Start price: ${start_price:,.2f}")
    print(f"   End price: ${end_price:,.2f}")
    print(f"   Change: {price_change:+.2f}%")
    
    if price_change > 1:
        print(f"   📈 Strong UPTREND - explains why no SELL signals")
    elif price_change > 0:
        print(f"   📈 Uptrend - explains why no SELL signals")
    elif price_change < -1:
        print(f"   📉 Strong DOWNTREND - should have SELL signals!")
    else:
        print(f"   ➡️  Sideways - mixed signals expected")

# Check model predictions
print(f"\n3. MODEL PREDICTIONS (Last 24 Hours):")
s_model_pos = (recent_signals['s_model'] > 0).sum()
s_model_neg = (recent_signals['s_model'] < 0).sum()
s_model_zero = (recent_signals['s_model'] == 0).sum()

print(f"   UP (s_model > 0):   {s_model_pos} ({s_model_pos/len(recent_signals)*100:.1f}%)")
print(f"   DOWN (s_model < 0): {s_model_neg} ({s_model_neg/len(recent_signals)*100:.1f}%)")
print(f"   NEUTRAL (s_model = 0): {s_model_zero}")

if s_model_neg == 0:
    print(f"\n   🔍 ROOT CAUSE: Model NEVER predicted DOWN in 24 hours")
    print(f"      → This is why there are no SELL trades")
    print(f"      → Check if this matches market conditions")
else:
    print(f"\n   ⚠️  Model DID predict DOWN {s_model_neg} times!")
    print(f"      → Need to check if these became SELL signals")

# Check decision signals
print(f"\n4. DECISION SIGNALS (Last 24 Hours):")
dir_buy = (recent_signals['dir'] == 1).sum()
dir_sell = (recent_signals['dir'] == -1).sum()
dir_neutral = (recent_signals['dir'] == 0).sum()

print(f"   BUY (dir = 1):   {dir_buy} ({dir_buy/len(recent_signals)*100:.1f}%)")
print(f"   SELL (dir = -1): {dir_sell} ({dir_sell/len(recent_signals)*100:.1f}%)")
print(f"   NEUTRAL (dir = 0): {dir_neutral} ({dir_neutral/len(recent_signals)*100:.1f}%)")

if s_model_neg > 0 and dir_sell == 0:
    print(f"\n   🔴 CRITICAL: Model predicted DOWN {s_model_neg} times but NO SELL signals!")
    print(f"      → Consensus is STILL blocking despite fix")
    print(f"      → Need to investigate decision logic")
elif s_model_neg == 0:
    print(f"\n   ✅ Consistent: No DOWN predictions = No SELL signals")
    print(f"      → System is working correctly")

# Detailed analysis of DOWN predictions
if s_model_neg > 0:
    print(f"\n5. DETAILED ANALYSIS OF DOWN PREDICTIONS:")
    down_preds = recent_signals[recent_signals['s_model'] < 0]
    
    print(f"\n   When model predicted DOWN ({len(down_preds)} times):")
    print(f"   What happened to these signals?")
    
    # Check what dir was set for these DOWN predictions
    dir_distribution = down_preds['dir'].value_counts()
    print(f"\n   dir = 1 (BUY):   {dir_distribution.get(1, 0)}")
    print(f"   dir = -1 (SELL): {dir_distribution.get(-1, 0)}")
    print(f"   dir = 0 (NEUT):  {dir_distribution.get(0, 0)}")
    
    if dir_distribution.get(-1, 0) == 0:
        print(f"\n   🔴 SMOKING GUN: All DOWN predictions blocked!")
        print(f"      → Consensus is STILL active despite config")
        print(f"      → Fix may not be working")
    
    # Show sample
    print(f"\n   Sample DOWN predictions:")
    for idx, row in down_preds.head(5).iterrows():
        print(f"   {row['ts_iso'][-8:]}: s_model={row['s_model']:+.4f} → dir={row['dir']} ({'BLOCKED' if row['dir'] != -1 else 'OK'})")

# Check if bot is using the updated code
print(f"\n6. CONFIGURATION CHECK:")
with open('live_demo/config.json') as f:
    config = json.load(f)
    require_consensus = config['thresholds'].get('require_consensus', 'NOT FOUND')
    
print(f"   require_consensus in config: {require_consensus}")

if require_consensus == False:
    print(f"   ✅ Config is correct")
else:
    print(f"   ❌ Config is WRONG - fix not applied!")

# Check recent signals to see if pattern changed after fix
print(f"\n7. TIMELINE ANALYSIS:")
fix_time = pd.to_datetime('2025-12-29 17:09:00+05:30')  # When we deployed fix

if signals_df['ts'].max() > fix_time:
    before_fix = signals_df[signals_df['ts'] < fix_time]
    after_fix = signals_df[signals_df['ts'] >= fix_time]
    
    print(f"\n   Before fix ({len(before_fix)} signals):")
    print(f"   SELL signals: {(before_fix['dir'] == -1).sum()}")
    
    print(f"\n   After fix ({len(after_fix)} signals):")
    print(f"   SELL signals: {(after_fix['dir'] == -1).sum()}")
    
    if (after_fix['dir'] == -1).sum() == 0 and (after_fix['s_model'] < 0).sum() > 0:
        print(f"\n   🔴 PROBLEM: Fix deployed but still no SELL signals!")
        print(f"      Model predicted DOWN {(after_fix['s_model'] < 0).sum()} times after fix")
        print(f"      But STILL 0 SELL signals")
        print(f"      → Bot may not have restarted with new code")

print(f"\n" + "="*80)
print("CONCLUSION:")
print("="*80)

# Determine root cause
if s_model_neg == 0:
    print(f"\n✅ ROOT CAUSE: Market conditions (no DOWN predictions)")
    print(f"   - Model correctly predicting uptrend")
    print(f"   - No SELL signals expected")
    print(f"   - System is working correctly")
    print(f"\n   ACTION: Wait for market to reverse")
    
elif s_model_neg > 0 and dir_sell == 0:
    print(f"\n🔴 ROOT CAUSE: Fix not working (DOWN predictions blocked)")
    print(f"   - Model predicted DOWN {s_model_neg} times")
    print(f"   - But 0 SELL signals generated")
    print(f"   - Consensus still blocking despite config")
    print(f"\n   POSSIBLE REASONS:")
    print(f"   1. Bot not restarted after fix")
    print(f"   2. Using cached/old decision.py code")
    print(f"   3. Fix not applied correctly")
    print(f"\n   ACTION: Restart bot with fix")
    
elif dir_sell > 0:
    print(f"\n⚠️  ROOT CAUSE: SELL signals exist but not executing")
    print(f"   - {dir_sell} SELL signals generated")
    print(f"   - But 0 SELL trades executed")
    print(f"   - Execution logic issue")
    print(f"\n   ACTION: Check execution logic")

print("="*80)
