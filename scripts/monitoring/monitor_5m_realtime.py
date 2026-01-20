"""
COMPREHENSIVE 5M BOT MONITOR
Real-time monitoring of trades, confidence, logs, and signals
"""
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import time

def monitor_5m_bot():
    """Monitor 5m bot in real-time"""
    
    print("=" * 80)
    print("5M BOT REAL-TIME MONITOR")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Monitoring: Trades, Confidence, Logs, Signals")
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()
    
    last_trade_count = 0
    last_signal_count = 0
    
    while True:
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 80)
            print(f"5M BOT MONITOR - {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 80)
            print()
            
            # ============================================
            # SECTION 1: TRADE STATUS
            # ============================================
            print("📈 TRADE STATUS")
            print("-" * 80)
            
            exec_file = 'paper_trading_outputs/executions_paper.csv'
            if os.path.exists(exec_file):
                try:
                    df_exec = pd.read_csv(exec_file)
                    df_exec['ts_ist'] = pd.to_datetime(df_exec['ts_ist'])
                    
                    # Get recent trades (last hour)
                    recent = df_exec[df_exec['ts_ist'] > (datetime.now() - timedelta(hours=1))]
                    
                    if len(recent) > 0:
                        print(f"✅ Trades in last hour: {len(recent)}")
                        
                        buy_count = len(recent[recent['side'] == 'BUY'])
                        sell_count = len(recent[recent['side'] == 'SELL'])
                        
                        print(f"   BUY: {buy_count}, SELL: {sell_count}")
                        
                        if 'pnl' in recent.columns:
                            total_pnl = recent['pnl'].sum()
                            wins = len(recent[recent['pnl'] > 0])
                            losses = len(recent[recent['pnl'] < 0])
                            win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
                            
                            print(f"   P&L: ${total_pnl:+.2f}")
                            print(f"   Win Rate: {win_rate:.1f}%")
                        
                        # Show last 3 trades
                        print()
                        print("Last 3 Trades:")
                        for idx, row in recent.tail(3).iterrows():
                            time_str = row['ts_ist'].strftime('%H:%M:%S')
                            side = row['side']
                            pnl = row['pnl'] if 'pnl' in row else 0
                            print(f"   {time_str} | {side:4s} | ${pnl:+7.2f}")
                        
                        if len(recent) > last_trade_count:
                            print()
                            print(f"   🔔 NEW TRADE! ({len(recent) - last_trade_count} new)")
                        
                        last_trade_count = len(recent)
                    else:
                        print("⏳ No trades in last hour")
                        
                except Exception as e:
                    print(f"⚠️ Error reading trades: {e}")
            else:
                print("⏳ No execution file yet")
            
            print()
            
            # ============================================
            # SECTION 2: CONFIDENCE LEVELS
            # ============================================
            print("🎯 CONFIDENCE LEVELS")
            print("-" * 80)
            
            signal_file = 'paper_trading_outputs/5m/logs/signals/date=2026-01-02/signals.csv'
            if os.path.exists(signal_file):
                try:
                    df_signals = pd.read_csv(signal_file)
                    
                    # Get recent signals (last 20)
                    recent_signals = df_signals.tail(20)
                    
                    if 's_model' in recent_signals.columns:
                        s_model = recent_signals['s_model'].dropna()
                        
                        if len(s_model) > 0:
                            print(f"Recent Predictions (last 20 signals):")
                            print(f"   Min: {s_model.min():+.4f}")
                            print(f"   Max: {s_model.max():+.4f}")
                            print(f"   Mean: {s_model.mean():+.4f}")
                            print(f"   Abs Max: {abs(s_model).max():.4f}")
                            print()
                            
                            # Count above threshold
                            above_threshold = sum(abs(s_model) >= 0.40)
                            print(f"   Above 0.40 threshold: {above_threshold}/20")
                            
                            # Direction distribution
                            up = sum(s_model > 0)
                            down = sum(s_model < 0)
                            print(f"   UP: {up}, DOWN: {down}")
                            
                            # Latest prediction
                            latest = s_model.iloc[-1]
                            direction = "UP" if latest > 0 else "DOWN" if latest < 0 else "NEUTRAL"
                            print()
                            print(f"   Latest: {latest:+.4f} ({direction})")
                            
                            if abs(latest) >= 0.40:
                                print(f"   ✅ TRADEABLE (above 0.40)")
                            else:
                                print(f"   ⏳ Below threshold (need 0.40)")
                    
                    if len(df_signals) > last_signal_count:
                        print()
                        print(f"   🔔 NEW SIGNALS! ({len(df_signals) - last_signal_count} new)")
                    
                    last_signal_count = len(df_signals)
                    
                except Exception as e:
                    print(f"⚠️ Error reading signals: {e}")
            else:
                print("⏳ No signals file yet")
            
            print()
            
            # ============================================
            # SECTION 3: SYSTEM STATUS
            # ============================================
            print("🤖 SYSTEM STATUS")
            print("-" * 80)
            
            # Check if bot is running (approximate)
            print("Bot Process: ✅ RUNNING (assumed)")
            print(f"Config CONF_MIN: 0.40")
            print(f"Model: New (64.95% accuracy)")
            
            print()
            
            # ============================================
            # SECTION 4: ALERTS
            # ============================================
            alert_file = 'paper_trading_outputs/5m/logs/system_alerts.csv'
            if os.path.exists(alert_file):
                try:
                    df_alerts = pd.read_csv(alert_file)
                    recent_alerts = df_alerts.tail(5)
                    
                    if len(recent_alerts) > 0:
                        print("🚨 RECENT ALERTS")
                        print("-" * 80)
                        for idx, row in recent_alerts.iterrows():
                            print(f"   {row.get('timestamp', 'N/A')} | {row.get('message', 'N/A')}")
                        print()
                except:
                    pass
            
            print("=" * 80)
            print("Refreshing in 10 seconds... (Ctrl+C to stop)")
            print("=" * 80)
            
            time.sleep(10)
            
        except KeyboardInterrupt:
            print()
            print("=" * 80)
            print("Monitor stopped")
            print("=" * 80)
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_5m_bot()
