"""
MONITORING DASHBOARD - Track SELL Trades Fix Performance
Run this in a separate terminal while bot is running
"""

import pandas as pd
import time
import json
from datetime import datetime, timedelta

class BotMonitor:
    def __init__(self):
        self.baseline = None
        self.start_time = datetime.now()
        
    def load_data(self):
        """Load current data"""
        try:
            exec_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/executions_paper.csv')
            signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
            return exec_df, signals_df, None
        except Exception as e:
            return None, None, str(e)
    
    def get_metrics(self, exec_df, signals_df):
        """Calculate key metrics"""
        if exec_df is None or signals_df is None:
            return None
            
        # Execution metrics
        total_exec = len(exec_df)
        buy_exec = (exec_df['side'] == 'BUY').sum()
        sell_exec = (exec_df['side'] == 'SELL').sum()
        
        # Signal metrics
        dir_counts = signals_df['dir'].value_counts()
        total_signals = len(signals_df)
        dir_buy = dir_counts.get(1, 0)
        dir_sell = dir_counts.get(-1, 0)
        dir_neutral = dir_counts.get(0, 0)
        
        # Model predictions
        s_model_positive = (signals_df['s_model'] > 0).sum()
        s_model_negative = (signals_df['s_model'] < 0).sum()
        
        # Execution rate
        exec_rate = (dir_buy + dir_sell) / total_signals * 100 if total_signals > 0 else 0
        
        # P&L (if available)
        total_pnl = 0
        wins = 0
        losses = 0
        
        for idx, row in exec_df.iterrows():
            try:
                raw = json.loads(row['raw'])
                pnl = raw.get('realized_pnl', 0)
                total_pnl += pnl
                if pnl > 0:
                    wins += 1
                elif pnl < 0:
                    losses += 1
            except:
                pass
        
        win_rate = (wins / total_exec * 100) if total_exec > 0 else 0
        
        return {
            'total_exec': total_exec,
            'buy_exec': buy_exec,
            'sell_exec': sell_exec,
            'total_signals': total_signals,
            'dir_buy': dir_buy,
            'dir_sell': dir_sell,
            'dir_neutral': dir_neutral,
            's_model_pos': s_model_positive,
            's_model_neg': s_model_negative,
            'exec_rate': exec_rate,
            'total_pnl': total_pnl,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'timestamp': datetime.now()
        }
    
    def print_dashboard(self, metrics, baseline):
        """Print monitoring dashboard"""
        print("\n" + "="*80)
        print(f"🚀 5M BOT MONITORING DASHBOARD - SELL TRADES FIX")
        print(f"⏰ {metrics['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Running for: {str(datetime.now() - self.start_time).split('.')[0]}")
        print("="*80)
        
        # Fix Status
        print(f"\n🎯 FIX STATUS:")
        if metrics['sell_exec'] > 0:
            print(f"   ✅ SELL TRADES ARE WORKING! ({metrics['sell_exec']} trades)")
            if baseline and baseline['sell_exec'] == 0:
                print(f"   🎉 First SELL trade detected! Fix is successful!")
        elif metrics['dir_sell'] > 0:
            print(f"   ⏳ SELL signals generated ({metrics['dir_sell']}) - waiting for execution")
        else:
            print(f"   ⏳ Waiting for model to predict DOWN...")
        
        # Execution Summary
        print(f"\n📊 EXECUTION SUMMARY:")
        print(f"   Total: {metrics['total_exec']}")
        print(f"   BUY:   {metrics['buy_exec']} ({metrics['buy_exec']/max(1,metrics['total_exec'])*100:.1f}%)")
        print(f"   SELL:  {metrics['sell_exec']} ({metrics['sell_exec']/max(1,metrics['total_exec'])*100:.1f}%)")
        
        if baseline:
            new_exec = metrics['total_exec'] - baseline['total_exec']
            new_sell = metrics['sell_exec'] - baseline['sell_exec']
            if new_exec > 0:
                print(f"   📈 New since start: {new_exec} (+{new_sell} SELL)")
        
        # Signal Summary
        print(f"\n📡 SIGNAL SUMMARY:")
        print(f"   Total signals: {metrics['total_signals']}")
        print(f"   BUY signals:   {metrics['dir_buy']} ({metrics['dir_buy']/max(1,metrics['total_signals'])*100:.1f}%)")
        print(f"   SELL signals:  {metrics['dir_sell']} ({metrics['dir_sell']/max(1,metrics['total_signals'])*100:.1f}%)")
        print(f"   NEUTRAL:       {metrics['dir_neutral']} ({metrics['dir_neutral']/max(1,metrics['total_signals'])*100:.1f}%)")
        print(f"   Execution rate: {metrics['exec_rate']:.1f}%")
        
        # Model Predictions
        print(f"\n🤖 MODEL PREDICTIONS:")
        print(f"   UP (s_model > 0):   {metrics['s_model_pos']} ({metrics['s_model_pos']/max(1,metrics['total_signals'])*100:.1f}%)")
        print(f"   DOWN (s_model < 0): {metrics['s_model_neg']} ({metrics['s_model_neg']/max(1,metrics['total_signals'])*100:.1f}%)")
        
        # Performance
        print(f"\n💰 PERFORMANCE:")
        print(f"   Total P&L: ${metrics['total_pnl']:.2f}")
        print(f"   Wins: {metrics['wins']}")
        print(f"   Losses: {metrics['losses']}")
        print(f"   Win Rate: {metrics['win_rate']:.1f}%")
        
        if baseline:
            pnl_change = metrics['total_pnl'] - baseline['total_pnl']
            if pnl_change != 0:
                print(f"   📈 P&L change: ${pnl_change:+.2f}")
        
        # Key Indicators
        print(f"\n🔍 KEY INDICATORS:")
        
        # Check 1: Are SELL signals being generated?
        if metrics['dir_sell'] > 0:
            print(f"   ✅ SELL signals: YES ({metrics['dir_sell']} signals)")
        else:
            print(f"   ⏳ SELL signals: Waiting for DOWN predictions...")
        
        # Check 2: Are SELL trades executing?
        if metrics['sell_exec'] > 0:
            print(f"   ✅ SELL executions: YES ({metrics['sell_exec']} trades)")
        elif metrics['dir_sell'] > 0:
            print(f"   ⚠️  SELL executions: NO (signals exist but not executing)")
        else:
            print(f"   ⏳ SELL executions: Waiting for signals...")
        
        # Check 3: Is win rate improving?
        if metrics['win_rate'] > 0:
            print(f"   ✅ Win rate: {metrics['win_rate']:.1f}% (improved from 0%!)")
        else:
            print(f"   ⏳ Win rate: Still 0% (need more trades)")
        
        # Check 4: Is execution rate reasonable?
        if metrics['exec_rate'] > 50:
            print(f"   ⚠️  Execution rate: {metrics['exec_rate']:.1f}% (very high - monitor costs)")
        elif metrics['exec_rate'] > 20:
            print(f"   ✅ Execution rate: {metrics['exec_rate']:.1f}% (good)")
        else:
            print(f"   ⏳ Execution rate: {metrics['exec_rate']:.1f}% (low)")
        
        print(f"\n{'='*80}")
        print(f"Next update in 30 seconds... (Ctrl+C to stop)")
        print("="*80)
    
    def run(self, interval=30):
        """Run monitoring loop"""
        print("Starting SELL Trades Fix Monitor...")
        print(f"Monitoring every {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                exec_df, signals_df, error = self.load_data()
                
                if error:
                    print(f"\n❌ ERROR: {error}")
                    print("   Waiting for bot to start...")
                    time.sleep(interval)
                    continue
                
                metrics = self.get_metrics(exec_df, signals_df)
                
                if metrics is None:
                    print("\n⏳ Waiting for data...")
                    time.sleep(interval)
                    continue
                
                # Set baseline on first run
                if self.baseline is None:
                    self.baseline = metrics
                    print(f"📊 Baseline captured: {metrics['total_exec']} executions, {metrics['sell_exec']} SELL trades")
                
                self.print_dashboard(metrics, self.baseline)
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n" + "="*80)
            print("MONITORING STOPPED")
            print("="*80)
            
            # Final summary
            exec_df, signals_df, _ = self.load_data()
            if exec_df is not None:
                final_metrics = self.get_metrics(exec_df, signals_df)
                
                print(f"\n📊 FINAL SUMMARY:")
                print(f"   Runtime: {str(datetime.now() - self.start_time).split('.')[0]}")
                print(f"   Total executions: {final_metrics['total_exec']}")
                print(f"   SELL trades: {final_metrics['sell_exec']}")
                print(f"   Win rate: {final_metrics['win_rate']:.1f}%")
                print(f"   Total P&L: ${final_metrics['total_pnl']:.2f}")
                
                if self.baseline:
                    new_exec = final_metrics['total_exec'] - self.baseline['total_exec']
                    new_sell = final_metrics['sell_exec'] - self.baseline['sell_exec']
                    pnl_change = final_metrics['total_pnl'] - self.baseline['total_pnl']
                    
                    print(f"\n📈 CHANGES SINCE START:")
                    print(f"   New executions: +{new_exec}")
                    print(f"   New SELL trades: +{new_sell}")
                    print(f"   P&L change: ${pnl_change:+.2f}")
                
                if final_metrics['sell_exec'] > 0:
                    print(f"\n✅ FIX IS WORKING! SELL trades are happening.")
                else:
                    print(f"\n⏳ No SELL trades yet. Keep bot running longer.")
            
            print("="*80)

if __name__ == "__main__":
    monitor = BotMonitor()
    monitor.run(interval=30)
