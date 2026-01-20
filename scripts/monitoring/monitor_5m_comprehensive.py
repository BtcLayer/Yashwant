"""
Comprehensive 5m Bot Monitoring Script
Monitors:
- Bot status and health
- Model performance metrics
- Trade execution (BUY/SELL/NEUTRAL balance)
- Confidence, BPS, Profitability
- Balance and position tracking
- Signal quality and direction distribution
"""

import os
import sys
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_section(text):
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}{'─'*80}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{Colors.BOLD}{'─'*80}{Colors.ENDC}")

def print_metric(label, value, status="info"):
    color = Colors.OKGREEN if status == "good" else Colors.WARNING if status == "warning" else Colors.FAIL if status == "bad" else Colors.OKBLUE
    print(f"{color}{label:.<50} {value}{Colors.ENDC}")

def check_bot_status():
    """Check if 5m bot is running"""
    print_section("🤖 BOT STATUS")
    
    # Check for running processes (Windows)
    import subprocess
    try:
        result = subprocess.run(['powershell', '-Command', 
                               "Get-Process python | Where-Object {$_.CommandLine -like '*live_demo*main*'}"],
                              capture_output=True, text=True, timeout=5)
        if result.stdout.strip():
            print_metric("Bot Process", "✓ RUNNING", "good")
            return True
        else:
            print_metric("Bot Process", "✗ NOT RUNNING", "bad")
            return False
    except Exception as e:
        print_metric("Bot Process Check", f"⚠ Error: {str(e)}", "warning")
        return None

def analyze_model_performance():
    """Analyze model performance metrics"""
    print_section("📊 MODEL PERFORMANCE")
    
    base_dir = Path("paper_trading_outputs")
    
    # Check for signals file
    signals_file = base_dir / "signals.csv"
    if signals_file.exists():
        try:
            df = pd.read_csv(signals_file)
            if len(df) > 0:
                recent = df.tail(100)
                
                # Signal statistics
                print_metric("Total Signals Generated", len(df), "info")
                print_metric("Recent Signals (last 100)", len(recent), "info")
                
                # Check for key columns
                if 'pred_stack' in df.columns:
                    avg_pred = recent['pred_stack'].mean()
                    print_metric("Avg Prediction (recent)", f"{avg_pred:.4f}", "info")
                
                if 'ic_200' in df.columns:
                    avg_ic = recent['ic_200'].mean()
                    status = "good" if avg_ic > 0 else "bad"
                    print_metric("Avg IC-200 (recent)", f"{avg_ic:.4f}", status)
                
                # Check timestamp freshness
                if 'ts_ist' in df.columns:
                    last_signal = pd.to_datetime(df['ts_ist'].iloc[-1])
                    now = datetime.now()
                    age_minutes = (now - last_signal).total_seconds() / 60
                    status = "good" if age_minutes < 10 else "warning" if age_minutes < 30 else "bad"
                    print_metric("Last Signal Age", f"{age_minutes:.1f} minutes ago", status)
            else:
                print_metric("Signals File", "Empty", "warning")
        except Exception as e:
            print_metric("Signals Analysis", f"Error: {str(e)}", "bad")
    else:
        print_metric("Signals File", "Not Found", "bad")

def analyze_trade_balance():
    """Analyze BUY/SELL/NEUTRAL balance"""
    print_section("⚖️ TRADE DIRECTION BALANCE")
    
    base_dir = Path("paper_trading_outputs")
    exec_file = base_dir / "executions_paper.csv"
    
    if exec_file.exists():
        try:
            df = pd.read_csv(exec_file)
            if len(df) > 0:
                # Overall balance
                direction_counts = df['direction'].value_counts()
                total = len(df)
                
                print(f"\n{Colors.BOLD}Overall Trade Distribution:{Colors.ENDC}")
                for direction in ['BUY', 'SELL', 'NEUTRAL']:
                    count = direction_counts.get(direction, 0)
                    pct = (count / total * 100) if total > 0 else 0
                    status = "good" if pct > 10 else "warning" if pct > 0 else "bad"
                    print_metric(f"  {direction}", f"{count} trades ({pct:.1f}%)", status)
                
                # Recent balance (last 50 trades)
                recent = df.tail(50)
                recent_counts = recent['direction'].value_counts()
                recent_total = len(recent)
                
                print(f"\n{Colors.BOLD}Recent Trade Distribution (last 50):{Colors.ENDC}")
                for direction in ['BUY', 'SELL', 'NEUTRAL']:
                    count = recent_counts.get(direction, 0)
                    pct = (count / recent_total * 100) if recent_total > 0 else 0
                    status = "good" if pct > 10 else "warning" if pct > 0 else "bad"
                    print_metric(f"  {direction}", f"{count} trades ({pct:.1f}%)", status)
                
                # Balance check
                buy_count = direction_counts.get('BUY', 0)
                sell_count = direction_counts.get('SELL', 0)
                if buy_count > 0 and sell_count > 0:
                    ratio = buy_count / sell_count
                    if 0.5 <= ratio <= 2.0:
                        print_metric("\nBalance Status", "✓ BALANCED", "good")
                    else:
                        print_metric("\nBalance Status", f"⚠ IMBALANCED (ratio: {ratio:.2f})", "warning")
                elif sell_count == 0:
                    print_metric("\nBalance Status", "✗ NO SELL TRADES", "bad")
                elif buy_count == 0:
                    print_metric("\nBalance Status", "✗ NO BUY TRADES", "bad")
                    
            else:
                print_metric("Executions File", "Empty", "warning")
        except Exception as e:
            print_metric("Trade Balance Analysis", f"Error: {str(e)}", "bad")
    else:
        print_metric("Executions File", "Not Found", "bad")

def analyze_profitability():
    """Analyze confidence, BPS, and profitability"""
    print_section("💰 PROFITABILITY METRICS")
    
    base_dir = Path("paper_trading_outputs")
    exec_file = base_dir / "executions_paper.csv"
    
    if exec_file.exists():
        try:
            df = pd.read_csv(exec_file)
            if len(df) > 0:
                # Confidence metrics
                if 'confidence' in df.columns:
                    avg_conf = df['confidence'].mean()
                    recent_conf = df.tail(50)['confidence'].mean()
                    status = "good" if avg_conf > 0.6 else "warning" if avg_conf > 0.5 else "bad"
                    print_metric("Avg Confidence (all)", f"{avg_conf:.3f}", status)
                    print_metric("Avg Confidence (recent 50)", f"{recent_conf:.3f}", status)
                
                # Alpha/BPS metrics
                if 'alpha' in df.columns:
                    avg_alpha = df['alpha'].mean()
                    recent_alpha = df.tail(50)['alpha'].mean()
                    alpha_bps = avg_alpha * 10000
                    recent_alpha_bps = recent_alpha * 10000
                    status = "good" if alpha_bps > 2 else "warning" if alpha_bps > 0 else "bad"
                    print_metric("Avg Alpha BPS (all)", f"{alpha_bps:.2f} bps", status)
                    print_metric("Avg Alpha BPS (recent 50)", f"{recent_alpha_bps:.2f} bps", status)
                
                # PnL analysis
                if 'pnl' in df.columns:
                    total_pnl = df['pnl'].sum()
                    avg_pnl = df['pnl'].mean()
                    win_rate = (df['pnl'] > 0).sum() / len(df) * 100
                    
                    status = "good" if total_pnl > 0 else "bad"
                    print_metric("Total PnL", f"${total_pnl:.2f}", status)
                    print_metric("Avg PnL per Trade", f"${avg_pnl:.2f}", status)
                    
                    status = "good" if win_rate > 50 else "warning" if win_rate > 40 else "bad"
                    print_metric("Win Rate", f"{win_rate:.1f}%", status)
                
                # Cost analysis
                if 'cost_bps' in df.columns:
                    avg_cost = df['cost_bps'].mean()
                    print_metric("Avg Cost (BPS)", f"{avg_cost:.2f} bps", "info")
                
                # Net edge
                if 'alpha' in df.columns and 'cost_bps' in df.columns:
                    net_edge_bps = (df['alpha'] * 10000 - df['cost_bps']).mean()
                    status = "good" if net_edge_bps > 0 else "bad"
                    print_metric("Avg Net Edge", f"{net_edge_bps:.2f} bps", status)
                    
            else:
                print_metric("Executions File", "Empty", "warning")
        except Exception as e:
            print_metric("Profitability Analysis", f"Error: {str(e)}", "bad")
    else:
        print_metric("Executions File", "Not Found", "bad")

def analyze_equity_balance():
    """Analyze equity curve and balance"""
    print_section("📈 EQUITY & BALANCE")
    
    base_dir = Path("paper_trading_outputs")
    equity_file = base_dir / "equity.csv"
    
    if equity_file.exists():
        try:
            df = pd.read_csv(equity_file)
            if len(df) > 0:
                # Current equity
                if 'equity' in df.columns:
                    current_equity = df['equity'].iloc[-1]
                    initial_equity = df['equity'].iloc[0]
                    total_return = ((current_equity - initial_equity) / initial_equity * 100) if initial_equity != 0 else 0
                    
                    status = "good" if total_return > 0 else "bad"
                    print_metric("Current Equity", f"${current_equity:.2f}", "info")
                    print_metric("Initial Equity", f"${initial_equity:.2f}", "info")
                    print_metric("Total Return", f"{total_return:.2f}%", status)
                
                # Drawdown
                if 'equity' in df.columns:
                    cummax = df['equity'].cummax()
                    drawdown = (df['equity'] - cummax) / cummax * 100
                    max_dd = drawdown.min()
                    current_dd = drawdown.iloc[-1]
                    
                    status = "good" if max_dd > -5 else "warning" if max_dd > -10 else "bad"
                    print_metric("Max Drawdown", f"{max_dd:.2f}%", status)
                    print_metric("Current Drawdown", f"{current_dd:.2f}%", status)
                
                # Position
                if 'position' in df.columns:
                    current_pos = df['position'].iloc[-1]
                    print_metric("Current Position", f"{current_pos:.4f}", "info")
                    
            else:
                print_metric("Equity File", "Empty", "warning")
        except Exception as e:
            print_metric("Equity Analysis", f"Error: {str(e)}", "bad")
    else:
        print_metric("Equity File", "Not Found", "bad")

def check_config_settings():
    """Check critical config settings"""
    print_section("⚙️ CONFIGURATION")
    
    config_file = Path("live_demo/config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Key settings
            print_metric("Timeframe", config.get('data', {}).get('interval', 'Unknown'), "info")
            print_metric("Symbol", config.get('data', {}).get('symbol', 'Unknown'), "info")
            print_metric("Dry Run", str(config.get('execution', {}).get('dry_run', True)), "info")
            
            # Thresholds
            thresholds = config.get('thresholds', {})
            print_metric("CONF_MIN", f"{thresholds.get('CONF_MIN', 0):.2f}", "info")
            print_metric("ALPHA_MIN", f"{thresholds.get('ALPHA_MIN', 0):.3f}", "info")
            print_metric("Require Consensus", str(thresholds.get('require_consensus', False)), "info")
            
            # Risk settings
            risk = config.get('risk', {})
            print_metric("Base Notional", f"${risk.get('base_notional', 0):,.0f}", "info")
            print_metric("Cost BPS", f"{risk.get('cost_bps', 0):.1f}", "info")
            
        except Exception as e:
            print_metric("Config Analysis", f"Error: {str(e)}", "bad")
    else:
        print_metric("Config File", "Not Found", "bad")

def show_recent_activity():
    """Show recent trading activity"""
    print_section("🔄 RECENT ACTIVITY")
    
    base_dir = Path("paper_trading_outputs")
    exec_file = base_dir / "executions_paper.csv"
    
    if exec_file.exists():
        try:
            df = pd.read_csv(exec_file)
            if len(df) > 0:
                recent = df.tail(10)
                
                print(f"\n{Colors.BOLD}Last 10 Trades:{Colors.ENDC}\n")
                print(f"{'Time':<20} {'Direction':<10} {'Confidence':<12} {'Alpha(bps)':<12} {'PnL':<10}")
                print("─" * 70)
                
                for _, row in recent.iterrows():
                    time_str = str(row.get('ts_ist', 'N/A'))[:19]
                    direction = row.get('direction', 'N/A')
                    conf = row.get('confidence', 0)
                    alpha = row.get('alpha', 0) * 10000
                    pnl = row.get('pnl', 0)
                    
                    # Color code by direction
                    if direction == 'BUY':
                        color = Colors.OKGREEN
                    elif direction == 'SELL':
                        color = Colors.FAIL
                    else:
                        color = Colors.WARNING
                    
                    print(f"{color}{time_str:<20} {direction:<10} {conf:<12.3f} {alpha:<12.2f} ${pnl:<10.2f}{Colors.ENDC}")
                    
            else:
                print_metric("No trades found", "", "warning")
        except Exception as e:
            print_metric("Recent Activity", f"Error: {str(e)}", "bad")
    else:
        print_metric("Executions File", "Not Found", "bad")

def main():
    """Main monitoring function"""
    print_header("5M BOT COMPREHENSIVE MONITORING")
    print(f"{Colors.OKBLUE}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    
    # Run all checks
    check_bot_status()
    check_config_settings()
    analyze_model_performance()
    analyze_trade_balance()
    analyze_profitability()
    analyze_equity_balance()
    show_recent_activity()
    
    print_header("MONITORING COMPLETE")
    print(f"\n{Colors.OKBLUE}Tip: Run this script periodically to track bot performance{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Monitoring interrupted by user{Colors.ENDC}\n")
    except Exception as e:
        print(f"\n\n{Colors.FAIL}Error: {str(e)}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
