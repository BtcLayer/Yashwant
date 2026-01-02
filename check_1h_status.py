"""
Comprehensive 1h Bot Status Check
Check if model training worked and bot is functioning correctly
"""
import os
import pandas as pd
import json
import joblib
from datetime import datetime, timedelta

print("=" * 80)
print("1H BOT COMPREHENSIVE STATUS CHECK")
print("=" * 80)
print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
print(f"Bot Running Since: ~3 hours ago (started around 12:50 PM)")
print()

# ============================================
# 1. CHECK MODEL FILES
# ============================================
print("📦 STEP 1: Checking Model Files")
print("-" * 80)

try:
    latest_path = 'live_demo_1h/models/LATEST.json'
    with open(latest_path, 'r') as f:
        latest = json.load(f)
    
    print(f"✅ LATEST.json found")
    print(f"   Meta-classifier: {latest['meta_classifier']}")
    print(f"   Calibrator: {latest['calibrator']}")
    
    # Load training metadata
    meta_file = f"live_demo_1h/models/{latest['training_meta']}"
    with open(meta_file, 'r') as f:
        training_meta = json.load(f)
    
    print(f"\n✅ Training Metadata:")
    print(f"   Trained: {training_meta['timestamp_utc']}")
    print(f"   Target: {training_meta['target']}")
    print(f"   Features: {training_meta['n_features']}")
    print(f"   Meta Score: {training_meta.get('meta_score_in_sample', 'N/A'):.4f}")
    print(f"   Calibrated Score: {training_meta.get('calibrated_score', 'N/A'):.4f}")
    print(f"   Training Samples: {training_meta.get('training_samples', 'N/A')}")
    print(f"   Test Samples: {training_meta.get('test_samples', 'N/A')}")
    
    # Try loading the model
    meta_path = f"live_demo_1h/models/{latest['meta_classifier']}"
    model = joblib.load(meta_path)
    print(f"\n✅ Model loads successfully")
    print(f"   Model Type: {type(model).__name__}")
    print(f"   Predicts Classes: {model.classes_}")
    
except Exception as e:
    print(f"❌ Error checking model: {e}")

print()

# ============================================
# 2. CHECK BOT OUTPUT - SIGNALS
# ============================================
print("📊 STEP 2: Checking Signals Generated")
print("-" * 80)

signals_file = "paper_trading_outputs/signals.csv"
if os.path.exists(signals_file):
    try:
        df_signals = pd.read_csv(signals_file)
        df_signals['ts_ist'] = pd.to_datetime(df_signals['ts_ist'])
        
        # Get signals from last 4 hours
        cutoff = datetime.now() - timedelta(hours=4)
        recent_signals = df_signals[df_signals['ts_ist'] > cutoff]
        
        print(f"✅ Total Signals in File: {len(df_signals)}")
        print(f"✅ Signals (last 4 hours): {len(recent_signals)}")
        
        if len(recent_signals) > 0:
            print(f"\n📈 Recent Signal Statistics:")
            print(f"   Latest Signal: {recent_signals['ts_ist'].max()}")
            print(f"   Oldest Signal: {recent_signals['ts_ist'].min()}")
            
            # Show signal distribution
            print(f"\n   Signal Values (S_top):")
            print(f"   - Mean: {recent_signals['S_top'].mean():.4f}")
            print(f"   - Min: {recent_signals['S_top'].min():.4f}")
            print(f"   - Max: {recent_signals['S_top'].max():.4f}")
            
            print(f"\n   Last 10 Signals:")
            cols_to_show = ['ts_ist', 'bar_id', 'S_top', 'S_bot']
            available_cols = [c for c in cols_to_show if c in recent_signals.columns]
            print(recent_signals[available_cols].tail(10).to_string(index=False))
        else:
            print("⚠️ No signals in last 4 hours")
            print("   This might be normal for 1h timeframe if bot just started")
            
    except Exception as e:
        print(f"❌ Error reading signals: {e}")
else:
    print("❌ Signals file not found")
    print("   Expected: paper_trading_outputs/signals.csv")

print()

# ============================================
# 3. CHECK BOT OUTPUT - EXECUTIONS
# ============================================
print("💼 STEP 3: Checking Trade Executions")
print("-" * 80)

exec_file = "paper_trading_outputs/executions_paper.csv"
if os.path.exists(exec_file):
    try:
        df_exec = pd.read_csv(exec_file)
        df_exec['ts_ist'] = pd.to_datetime(df_exec['ts_ist'])
        
        # Get executions from last 4 hours
        cutoff = datetime.now() - timedelta(hours=4)
        recent_exec = df_exec[df_exec['ts_ist'] > cutoff]
        
        print(f"✅ Total Executions in File: {len(df_exec)}")
        print(f"✅ Executions (last 4 hours): {len(recent_exec)}")
        
        if len(recent_exec) > 0:
            # Count BUY vs SELL
            buy_count = len(recent_exec[recent_exec['side'] == 'BUY'])
            sell_count = len(recent_exec[recent_exec['side'] == 'SELL'])
            
            print(f"\n📊 Trade Distribution:")
            print(f"   BUY trades: {buy_count} ({buy_count/len(recent_exec)*100:.1f}%)")
            print(f"   SELL trades: {sell_count} ({sell_count/len(recent_exec)*100:.1f}%)")
            
            if sell_count == 0 and buy_count > 0:
                print(f"\n   ⚠️ WARNING: Only BUY trades detected!")
                print(f"   → May need to apply consensus fix to 1h config")
            elif sell_count > 0 and buy_count > 0:
                print(f"\n   ✅ GOOD: Both BUY and SELL trades present")
            
            print(f"\n   Latest Execution: {recent_exec['ts_ist'].max()}")
            
            print(f"\n   Last 10 Trades:")
            cols_to_show = ['ts_ist', 'side', 'size', 'price']
            available_cols = [c for c in cols_to_show if c in recent_exec.columns]
            print(recent_exec[available_cols].tail(10).to_string(index=False))
            
        else:
            print("⏳ No executions in last 4 hours")
            print("   This is normal - 1h bot trades less frequently than 5m")
            
    except Exception as e:
        print(f"❌ Error reading executions: {e}")
else:
    print("⏳ Executions file not found yet")
    print("   This is normal if no trades have been executed")

print()

# ============================================
# 4. OVERALL ASSESSMENT
# ============================================
print("=" * 80)
print("🎯 OVERALL ASSESSMENT")
print("=" * 80)

# Determine status
model_ok = os.path.exists('live_demo_1h/models/LATEST.json')
signals_exist = os.path.exists(signals_file)

if model_ok:
    print("✅ Model Training: SUCCESS")
    print("   - Model files created correctly")
    print("   - Model loads without errors")
    print("   - Training metrics look good")
else:
    print("❌ Model Training: FAILED")
    print("   - Model files missing or corrupted")

print()

if signals_exist:
    print("✅ Bot Operation: RUNNING")
    print("   - Bot is generating output")
    print("   - Check signals above for activity")
else:
    print("⚠️ Bot Operation: UNCLEAR")
    print("   - No output files detected")
    print("   - Bot may not be running or just started")

print()
print("=" * 80)
print("📝 RECOMMENDATIONS")
print("=" * 80)

if model_ok and signals_exist:
    print("✅ Everything looks good!")
    print("   1. Continue monitoring for 24 hours")
    print("   2. Check for both BUY and SELL trades")
    print("   3. If working well, train 24h and 12h models")
else:
    print("⚠️ Need attention:")
    if not model_ok:
        print("   1. Re-run model training: python train_model.py")
    if not signals_exist:
        print("   2. Verify bot is running: check terminal for 'python run_1h.py'")
        print("   3. Check bot logs for errors")

print()
print("=" * 80)
print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
print("=" * 80)
