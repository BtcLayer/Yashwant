"""
COMPREHENSIVE 5M BOT MONITORING - NEW MODEL
Monitor all aspects: trades, confidence, BUY/SELL balance, profitability
Run this every 30 minutes to track performance
"""
import pandas as pd
import json
import os
from datetime import datetime, timedelta

print("=" * 80)
print("5M BOT COMPREHENSIVE MONITORING - NEW MODEL")
print("=" * 80)
print(f"Monitor Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================
# PART 1: MODEL INFO
# ============================================
print("📊 PART 1: CURRENT MODEL INFO")
print("-" * 80)

with open('live_demo/models/LATEST.json', 'r') as f:
    latest = json.load(f)

with open(f"live_demo/models/{latest['training_meta']}", 'r') as f:
    meta = json.load(f)

model_date = datetime.strptime(meta['timestamp_utc'], '%Y%m%d_%H%M%S')
model_age_hours = (datetime.now() - model_date).total_seconds() / 3600

print(f"Model Date: {model_date.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Model Age: {model_age_hours:.1f} hours ({model_age_hours/24:.1f} days)")
print(f"Training Accuracy: {meta['meta_score_in_sample']*100:.2f}%")
print(f"Test Accuracy: {meta['calibrated_score']*100:.2f}%")
print()

# ============================================
# PART 2: RECENT TRADING ACTIVITY
# ============================================
print("📈 PART 2: RECENT TRADING ACTIVITY")
print("-" * 80)

try:
    df_exec = pd.read_csv('paper_trading_outputs/executions_paper.csv')
    df_exec['ts_ist'] = pd.to_datetime(df_exec['ts_ist'])
    
    # Get trades since model deployment
    recent = df_exec[df_exec['ts_ist'] > model_date]
    
    if len(recent) > 0:
        print(f"✅ Trades since new model: {len(recent)}")
        print()
        
        # BUY vs SELL
        buy_count = len(recent[recent['side'] == 'BUY'])
        sell_count = len(recent[recent['side'] == 'SELL'])
        
        print(f"Trade Distribution:")
        print(f"   BUY:  {buy_count:4d} ({buy_count/len(recent)*100:5.1f}%)")
        print(f"   SELL: {sell_count:4d} ({sell_count/len(recent)*100:5.1f}%)")
        print()
        
        if sell_count == 0:
            print("   ⚠️ WARNING: No SELL trades yet!")
        elif buy_count > 0 and sell_count > 0:
            ratio = buy_count / sell_count
            print(f"   BUY/SELL Ratio: {ratio:.2f}")
            if 0.5 <= ratio <= 2.0:
                print("   ✅ GOOD: Balanced trading")
            else:
                print("   ⚠️ WARNING: Imbalanced trading")
        
        print()
        
        # P&L Analysis
        if 'pnl' in recent.columns:
            total_pnl = recent['pnl'].sum()
            wins = len(recent[recent['pnl'] > 0])
            losses = len(recent[recent['pnl'] < 0])
            
            print(f"Performance:")
            print(f"   Total P&L: ${total_pnl:+.2f}")
            print(f"   Wins:      {wins:4d}")
            print(f"   Losses:    {losses:4d}")
            
            if wins + losses > 0:
                win_rate = wins / (wins + losses) * 100
                print(f"   Win Rate:  {win_rate:5.1f}%")
                
                if wins > 0:
                    avg_win = recent[recent['pnl'] > 0]['pnl'].mean()
                    print(f"   Avg Win:   ${avg_win:+.2f}")
                
                if losses > 0:
                    avg_loss = recent[recent['pnl'] < 0]['pnl'].mean()
                    print(f"   Avg Loss:  ${avg_loss:+.2f}")
                
                print()
                
                # Profitability assessment
                if total_pnl > 0:
                    print(f"   ✅ PROFITABLE: ${total_pnl:+.2f}")
                elif total_pnl == 0:
                    print(f"   ⚠️ BREAK-EVEN")
                else:
                    print(f"   ❌ LOSING: ${total_pnl:+.2f}")
                
                if win_rate >= 50:
                    print(f"   ✅ GOOD WIN RATE: {win_rate:.1f}%")
                elif win_rate >= 45:
                    print(f"   ⚠️ MODERATE WIN RATE: {win_rate:.1f}%")
                else:
                    print(f"   ❌ LOW WIN RATE: {win_rate:.1f}%")
        
        print()
        
        # Recent trades
        print("Last 5 Trades:")
        recent_5 = recent.tail(5)[['ts_ist', 'side', 'pnl']].copy() if 'pnl' in recent.columns else recent.tail(5)[['ts_ist', 'side']]
        for idx, row in recent_5.iterrows():
            if 'pnl' in row:
                print(f"   {row['ts_ist'].strftime('%H:%M:%S')} | {row['side']:4s} | ${row['pnl']:+7.2f}")
            else:
                print(f"   {row['ts_ist'].strftime('%H:%M:%S')} | {row['side']:4s}")
        
    else:
        print("⏳ No trades yet since new model deployment")
        print(f"   Model deployed: {model_age_hours:.1f} hours ago")
        print(f"   Expected first trade: Within next few hours")
    
except FileNotFoundError:
    print("❌ No execution data found")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# ============================================
# PART 3: SIGNAL CONFIDENCE LEVELS
# ============================================
print("🎯 PART 3: SIGNAL CONFIDENCE LEVELS")
print("-" * 80)

try:
    # Check recent signals
    signal_files = []
    signals_dir = 'paper_trading_outputs/5m/logs/signals'
    
    if os.path.exists(signals_dir):
        for date_dir in sorted(os.listdir(signals_dir), reverse=True)[:3]:  # Last 3 days
            signal_file = f"{signals_dir}/{date_dir}/signals.jsonl"
            if os.path.exists(signal_file):
                signal_files.append(signal_file)
        
        if signal_files:
            all_signals = []
            for sf in signal_files:
                with open(sf, 'r') as f:
                    for line in f:
                        try:
                            signal = json.loads(line)
                            all_signals.append(signal)
                        except:
                            pass
            
            if all_signals:
                # Get recent signals (last 100)
                recent_signals = all_signals[-100:]
                
                # Extract confidence levels
                confidences = []
                directions = []
                
                for sig in recent_signals:
                    if 'sanitized' in sig and 's_model' in sig['sanitized']:
                        conf = abs(sig['sanitized']['s_model'])
                        confidences.append(conf)
                        
                        if sig['sanitized']['s_model'] > 0:
                            directions.append('UP')
                        elif sig['sanitized']['s_model'] < 0:
                            directions.append('DOWN')
                        else:
                            directions.append('NEUTRAL')
                
                if confidences:
                    avg_conf = sum(confidences) / len(confidences)
                    max_conf = max(confidences)
                    min_conf = min(confidences)
                    
                    print(f"Signal Analysis (last {len(confidences)} signals):")
                    print(f"   Avg Confidence: {avg_conf:.4f}")
                    print(f"   Max Confidence: {max_conf:.4f}")
                    print(f"   Min Confidence: {min_conf:.4f}")
                    print()
                    
                    # Direction distribution
                    up_count = directions.count('UP')
                    down_count = directions.count('DOWN')
                    neutral_count = directions.count('NEUTRAL')
                    
                    print(f"Signal Directions:")
                    print(f"   UP:      {up_count:4d} ({up_count/len(directions)*100:5.1f}%)")
                    print(f"   DOWN:    {down_count:4d} ({down_count/len(directions)*100:5.1f}%)")
                    print(f"   NEUTRAL: {neutral_count:4d} ({neutral_count/len(directions)*100:5.1f}%)")
                    print()
                    
                    if down_count > 0:
                        print("   ✅ Model predicts both directions")
                    else:
                        print("   ⚠️ Model only predicts UP")
                else:
                    print("⏳ No confidence data available yet")
            else:
                print("⏳ No signals found")
        else:
            print("⏳ No signal files found")
    else:
        print("⏳ Signals directory not found")
        
except Exception as e:
    print(f"❌ Error: {e}")

print()

# ============================================
# PART 4: MONITORING SCHEDULE
# ============================================
print("=" * 80)
print("📅 MONITORING SCHEDULE")
print("=" * 80)
print()

print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Model Age: {model_age_hours:.1f} hours")
print()

if model_age_hours < 6:
    print("⏰ PHASE 1: Initial Monitoring (0-6 hours)")
    print("   Status: IN PROGRESS")
    print("   Action: Check every 30 minutes")
    print("   Goal: Verify bot is trading and making both BUY/SELL")
    print()
    print("   Next check: In 30 minutes")
    
elif model_age_hours < 24:
    print("⏰ PHASE 2: Active Monitoring (6-24 hours)")
    print("   Status: IN PROGRESS")
    print("   Action: Check every 2 hours")
    print("   Goal: Monitor win rate and P&L trend")
    print()
    print("   Next check: In 2 hours")
    
elif model_age_hours < 48:
    print("⏰ PHASE 3: Performance Evaluation (24-48 hours)")
    print("   Status: IN PROGRESS")
    print("   Action: Check every 4 hours")
    print("   Goal: Evaluate overall performance vs old model")
    print()
    print("   Next check: In 4 hours")
    
else:
    print("⏰ PHASE 4: Final Decision (48+ hours)")
    print("   Status: READY FOR DECISION")
    print("   Action: Make keep/rollback decision")
    print()
    
    if len(recent) > 0 and 'pnl' in recent.columns:
        total_pnl = recent['pnl'].sum()
        wins = len(recent[recent['pnl'] > 0])
        losses = len(recent[recent['pnl'] < 0])
        win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        
        print("   DECISION CRITERIA:")
        if total_pnl > 0 and win_rate >= 45:
            print("   ✅ KEEP NEW MODEL - Performance is good")
        elif total_pnl > 0:
            print("   ⚠️ MONITOR MORE - Profitable but low win rate")
        else:
            print("   ❌ CONSIDER ROLLBACK - Not profitable")

print()
print("=" * 80)
print("Run this script again at the scheduled time")
print("Command: python monitor_new_model.py")
print("=" * 80)
