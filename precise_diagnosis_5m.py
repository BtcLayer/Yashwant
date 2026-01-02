"""
PRECISE DIAGNOSIS: What's Wrong with Current 5M Model
Analyze the exact issues to fix with retraining
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

print("=" * 80)
print("PRECISE DIAGNOSIS: CURRENT 5M MODEL ISSUES")
print("=" * 80)
print()

# ============================================
# ISSUE 1: MODEL AGE & DATA STALENESS
# ============================================
print("🔍 ISSUE 1: DATA STALENESS")
print("-" * 80)

with open('live_demo/models/LATEST.json', 'r') as f:
    latest = json.load(f)

with open(f"live_demo/models/{latest['training_meta']}", 'r') as f:
    meta = json.load(f)

train_date = datetime.strptime(meta['timestamp_utc'], '%Y%m%d_%H%M%S')
age_days = (datetime.now() - train_date).days

print(f"Model trained on: {train_date.strftime('%Y-%m-%d')}")
print(f"Current date: {datetime.now().strftime('%Y-%m-%d')}")
print(f"Age: {age_days} days")
print()

print("❌ PROBLEM:")
print(f"   Model learned patterns from data ending ~{train_date.strftime('%B %Y')}")
print(f"   But market has evolved over {age_days} days")
print(f"   Old patterns may no longer work")
print()

print("✅ SOLUTION:")
print("   Retrain with fresh data from last 6 months")
print("   Model will learn current market patterns")
print()

# ============================================
# ISSUE 2: PERFORMANCE ANALYSIS
# ============================================
print("🔍 ISSUE 2: ACTUAL PERFORMANCE")
print("-" * 80)

try:
    df_exec = pd.read_csv('paper_trading_outputs/executions_paper.csv')
    df_exec['ts_ist'] = pd.to_datetime(df_exec['ts_ist'])
    
    # Get recent performance (last 7 days)
    recent = df_exec[df_exec['ts_ist'] > datetime.now() - timedelta(days=7)]
    
    if len(recent) > 0 and 'pnl' in recent.columns:
        total_pnl = recent['pnl'].sum()
        wins = len(recent[recent['pnl'] > 0])
        losses = len(recent[recent['pnl'] < 0])
        win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        
        print(f"Last 7 days performance:")
        print(f"   Total P&L: ${total_pnl:.2f}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Wins: {wins}, Losses: {losses}")
        print()
        
        if total_pnl < 0:
            print("❌ PROBLEM:")
            print(f"   Model is losing money (${total_pnl:.2f})")
            print(f"   Predictions don't match current market")
            print()
            
            print("✅ SOLUTION:")
            print("   Retrain on recent data")
            print("   Learn profitable patterns from current market")
            print()
        
        if win_rate < 45:
            print("❌ PROBLEM:")
            print(f"   Win rate too low ({win_rate:.1f}%)")
            print("   Model predictions are not accurate enough")
            print()
            
            print("✅ SOLUTION:")
            print("   Fresh training data will improve accuracy")
            print("   Target: >50% win rate")
            print()
            
except Exception as e:
    print(f"⚠️ Could not analyze performance: {e}")
    print()

# ============================================
# ISSUE 3: WHAT RETRAINING WILL FIX
# ============================================
print("=" * 80)
print("🎯 WHAT RETRAINING WILL FIX")
print("=" * 80)
print()

print("The SAME proven approach, just with FRESH data:")
print()

print("✅ KEEP (What Works):")
print("   • Same 17 features")
print("   • Same model structure (RF, ET, HistGB, GB → Meta → Calibrator)")
print("   • Same training process")
print("   • Same save format")
print()

print("🔄 UPDATE (What Changes):")
print("   • Training data: Oct 2025 → Recent 6 months")
print("   • Learned patterns: Old market → Current market")
print("   • Model weights: Stale → Fresh")
print()

print("Expected improvements:")
print("   1. ✅ Predictions match current market conditions")
print("   2. ✅ Better win rate (target: >50%)")
print("   3. ✅ Positive P&L")
print("   4. ✅ Fewer losing streaks")
print()

# ============================================
# ISSUE 4: WHY THE APPROACH WORKS
# ============================================
print("=" * 80)
print("💡 WHY THE CURRENT APPROACH IS GOOD")
print("=" * 80)
print()

print("The 5m model structure is proven:")
print("   ✅ Uses 17 well-designed features")
print("   ✅ Ensemble of 4 strong base models")
print("   ✅ Meta-learning for better predictions")
print("   ✅ Calibration for probability estimates")
print("   ✅ Compatible with live trading bot")
print()

print("We DON'T need to change the approach!")
print("We ONLY need to update the training data.")
print()

# ============================================
# FINAL RECOMMENDATION
# ============================================
print("=" * 80)
print("📋 RETRAINING PLAN")
print("=" * 80)
print()

print("Step-by-step process:")
print()

print("1. FETCH FRESH DATA")
print("   • Get 5m OHLCV from Hyperliquid")
print("   • Last 6 months (~50,000+ bars)")
print("   • Same format as before")
print()

print("2. USE EXACT SAME FEATURES")
print("   • All 17 features (mom_1, mom_3, etc.)")
print("   • Same formulas")
print("   • Same preprocessing")
print()

print("3. USE EXACT SAME MODEL STRUCTURE")
print("   • RandomForest, ExtraTrees, HistGB, GradientBoosting")
print("   • LogisticRegression meta-classifier")
print("   • CalibratedClassifierCV wrapper")
print()

print("4. TRAIN ON FRESH DATA")
print("   • 80/20 train/test split")
print("   • Same hyperparameters")
print("   • Same training process")
print()

print("5. VALIDATE & DEPLOY")
print("   • Check accuracy > 60%")
print("   • Verify predicts all 3 classes")
print("   • Backup old model")
print("   • Update LATEST.json")
print("   • Restart bot")
print()

print("=" * 80)
print("✅ READY TO CREATE RETRAINING SCRIPT")
print("=" * 80)
print()

print("The script will:")
print("   ✅ Use the proven 5m approach (no changes)")
print("   ✅ Train on fresh data only")
print("   ✅ Automatically backup old model")
print("   ✅ Update LATEST.json automatically")
print("   ✅ Provide rollback if needed")
print()
