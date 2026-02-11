"""
Live Monitor Dashboard - Day 4 Task 3
Real-time monitoring dashboard for MetaStackerBandit trading bots
"""

import json
import os
import glob
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import time

# Try to import tabulate, fallback to basic formatting
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False
    print("⚠️  Install tabulate for better formatting: pip install tabulate")


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def load_jsonl_files(directory: str, hours_back: int = 24) -> List[Dict]:
    """Load JSONL files from directory, filtering by time"""
    if not os.path.exists(directory):
        return []
    
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    cutoff_ts = cutoff_time.timestamp() * 1000  # Convert to milliseconds
    
    records = []
    
    # Look for both date-partitioned and non-partitioned files
    patterns = [
        os.path.join(directory, '*.jsonl'),
        os.path.join(directory, 'date=*', '*.jsonl')
    ]
    
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        # Filter by timestamp if present
                        ts = record.get('ts', record.get('timestamp', 0))
                        if ts >= cutoff_ts:
                            records.append(record)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue
    
    return records


def load_kpi_data(timeframe: str, hours_back: int = 24) -> Optional[Dict]:
    """Load most recent KPI scorecard for timeframe"""
    kpi_dir = f'paper_trading_outputs/{timeframe}/logs/kpi_scorecard'
    records = load_jsonl_files(kpi_dir, hours_back)
    
    if not records:
        return None
    
    # Return most recent record
    records_sorted = sorted(records, key=lambda x: x.get('ts', 0), reverse=True)
    return records_sorted[0] if records_sorted else None


def load_executions(timeframe: str, limit: int = 10, hours_back: int = 24) -> List[Dict]:
    """Load recent executions (organic only)"""
    exec_dir = f'paper_trading_outputs/{timeframe}/logs/execution'
    records = load_jsonl_files(exec_dir, hours_back)
    
    # Filter organic only (exclude forced/synthetic)
    organic = [r for r in records if not r.get('is_forced', False) and not r.get('is_synthetic', False)]
    
    # Sort by timestamp, most recent first
    organic_sorted = sorted(organic, key=lambda x: x.get('ts', 0), reverse=True)
    
    return organic_sorted[:limit]


def load_veto_data(timeframe: str, hours_back: int = 24) -> List[Dict]:
    """Load veto reasons from logs"""
    veto_dir = f'paper_trading_outputs/{timeframe}/logs'
    
    # Try veto_reasons.jsonl first, fallback to order_intent
    veto_file = os.path.join(veto_dir, 'veto_reasons.jsonl')
    intent_dir = os.path.join(veto_dir, 'order_intent')
    
    vetoes = []
    
    # Try veto_reasons.jsonl
    if os.path.exists(veto_file):
        vetoes = load_jsonl_files(veto_dir, hours_back)
        vetoes = [v for v in vetoes if 'reason_code' in v]
    
    # Fallback to order_intent
    if not vetoes and os.path.exists(intent_dir):
        intents = load_jsonl_files(intent_dir, hours_back)
        vetoes = [i for i in intents if i.get('decision') == 'VETO']
    
    return vetoes


def get_bot_status(timeframe: str) -> Tuple[str, str, str]:
    """
    Get bot status: running/idle/stopped
    Returns: (status, symbol, color)
    """
    # Check for recent health logs
    health_dir = f'paper_trading_outputs/{timeframe}/logs/health'
    health_records = load_jsonl_files(health_dir, hours_back=1)  # Last hour
    
    if not health_records:
        return ('STOPPED', '⭕', Colors.RED)
    
    # Check most recent timestamp
    latest = max(health_records, key=lambda x: x.get('ts', 0))
    latest_ts = latest.get('ts', 0) / 1000  # Convert to seconds
    now_ts = datetime.now().timestamp()
    
    staleness_min = (now_ts - latest_ts) / 60
    
    if staleness_min < 10:  # Active within 10 minutes
        return ('RUNNING', '✅', Colors.GREEN)
    elif staleness_min < 120:  # Seen within 2 hours
        return ('IDLE', '⚠️', Colors.YELLOW)
    else:
        return ('STOPPED', '⭕', Colors.RED)


def format_pnl(pnl: float) -> str:
    """Format PnL with color"""
    if pnl > 0:
        return f"{Colors.GREEN}+${pnl:.2f}{Colors.RESET}"
    elif pnl < 0:
        return f"{Colors.RED}-${abs(pnl):.2f}{Colors.RESET}"
    else:
        return f"${pnl:.2f}"


def format_metric(value: Optional[float], threshold: float, higher_is_better: bool = True) -> str:
    """Format metric with color based on threshold"""
    if value is None:
        return f"{Colors.GRAY}N/A{Colors.RESET}"
    
    if higher_is_better:
        color = Colors.GREEN if value >= threshold else Colors.YELLOW if value >= threshold * 0.8 else Colors.RED
    else:
        color = Colors.GREEN if value <= threshold else Colors.YELLOW if value <= threshold * 1.2 else Colors.RED
    
    return f"{color}{value:.2f}{Colors.RESET}"


def print_header():
    """Print dashboard header"""
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'═' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'   MetaStackerBandit Live Monitor Dashboard   ':^80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'═' * 80}{Colors.RESET}")
    print(f"{Colors.GRAY}Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    print()


def print_bot_status(timeframes: List[str]):
    """Print status for all bots"""
    print(f"{Colors.BOLD}Bot Status{Colors.RESET}")
    print(f"{Colors.GRAY}{'─' * 80}{Colors.RESET}")
    
    rows = []
    for tf in timeframes:
        status, symbol, color = get_bot_status(tf)
        
        # Get last signal time
        signal_dir = f'paper_trading_outputs/{tf}/logs/signals'
        signals = load_jsonl_files(signal_dir, hours_back=24)
        if signals:
            latest_signal = max(signals, key=lambda x: x.get('ts', 0))
            signal_ts = latest_signal.get('ts', 0) / 1000
            signal_ago = (datetime.now().timestamp() - signal_ts) / 60
            if signal_ago < 60:
                last_signal = f"{signal_ago:.0f}m ago"
            else:
                last_signal = f"{signal_ago / 60:.1f}h ago"
        else:
            last_signal = "No data"
        
        rows.append([
            f"{tf} Bot",
            f"{color}{symbol} {status}{Colors.RESET}",
            last_signal
        ])
    
    if HAS_TABULATE:
        print(tabulate(rows, headers=['Timeframe', 'Status', 'Last Signal'], tablefmt='simple'))
    else:
        print(f"{'Timeframe':<15} {'Status':<20} {'Last Signal':<20}")
        for row in rows:
            print(f"{row[0]:<15} {row[1]:<20} {row[2]:<20}")
    print()


def print_recent_trades(timeframe: str, limit: int = 10):
    """Print recent trades"""
    print(f"{Colors.BOLD}Recent Trades (Last {limit}) - {timeframe}{Colors.RESET}")
    print(f"{Colors.GRAY}{'─' * 80}{Colors.RESET}")
    
    executions = load_executions(timeframe, limit)
    
    if not executions:
        print(f"{Colors.GRAY}No recent trades{Colors.RESET}")
        print()
        return
    
    rows = []
    for ex in executions:
        ts = ex.get('ts', 0) / 1000
        time_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        
        asset = ex.get('asset', ex.get('symbol', 'N/A'))
        side = ex.get('side', 'N/A')
        qty = ex.get('qty', 0)
        price = ex.get('fill_price', ex.get('price', 0))
        
        # Calculate PnL if available
        pnl = ex.get('realized_pnl', 'N/A')
        if isinstance(pnl, (int, float)):
            pnl_str = format_pnl(pnl)
        else:
            pnl_str = f"{Colors.GRAY}N/A{Colors.RESET}"
        
        side_colored = f"{Colors.GREEN}{side}{Colors.RESET}" if side == 'LONG' else f"{Colors.RED}{side}{Colors.RESET}" if side == 'SHORT' else side
        
        rows.append([
            time_str,
            asset,
            side_colored,
            f"{qty:.4f}",
            f"${price:,.2f}",
            pnl_str
        ])
    
    if HAS_TABULATE:
        print(tabulate(rows, headers=['Time', 'Asset', 'Side', 'Qty', 'Price', 'PnL'], tablefmt='simple'))
    else:
        print(f"{'Time':<10} {'Asset':<12} {'Side':<10} {'Qty':<12} {'Price':<12} {'PnL':<12}")
        for row in rows:
            print(f"{row[0]:<10} {row[1]:<12} {row[2]:<10} {row[3]:<12} {row[4]:<12} {row[5]:<12}")
    print()


def print_performance_metrics(timeframe: str):
    """Print performance metrics from KPI scorecard"""
    print(f"{Colors.BOLD}Performance Metrics (24h) - {timeframe}{Colors.RESET}")
    print(f"{Colors.GRAY}{'─' * 80}{Colors.RESET}")
    
    kpi = load_kpi_data(timeframe, hours_back=24)
    
    if not kpi:
        print(f"{Colors.GRAY}No KPI data available{Colors.RESET}")
        print()
        return
    
    sharpe = kpi.get('Sharpe_1w')
    win_rate = kpi.get('win_rate_1w')
    max_dd = kpi.get('max_DD_pct')
    cost_avg = kpi.get('cost_bps_avg')
    trades = kpi.get('total_trades_1w', 0)
    
    # Format metrics with color coding
    sharpe_str = format_metric(sharpe, 2.5, higher_is_better=True) if sharpe else f"{Colors.GRAY}N/A{Colors.RESET}"
    win_rate_str = format_metric(win_rate * 100 if win_rate else None, 50.0, higher_is_better=True) if win_rate else f"{Colors.GRAY}N/A{Colors.RESET}"
    max_dd_str = format_metric(max_dd, 20.0, higher_is_better=False) if max_dd else f"{Colors.GRAY}N/A{Colors.RESET}"
    cost_str = format_metric(cost_avg, 7.0, higher_is_better=False) if cost_avg else f"{Colors.GRAY}N/A{Colors.RESET}"
    
    # Gates
    gates = kpi.get('gates', {})
    sharpe_gate = "✅" if gates.get('sharpe_pass') else "❌"
    dd_gate = "✅" if gates.get('dd_pass') else "❌"
    cost_gate = "✅" if gates.get('cost_pass') else "❌" if gates.get('cost_pass') is not None else "⚠️"
    
    rows = [
        ['Sharpe (1w)', sharpe_str, sharpe_gate],
        ['Win Rate', win_rate_str + "%" if win_rate else f"{Colors.GRAY}N/A{Colors.RESET}", "-"],
        ['Max DD', max_dd_str + "%" if max_dd else f"{Colors.GRAY}N/A{Colors.RESET}", dd_gate],
        ['Cost (avg)', cost_str + " bps" if cost_avg else f"{Colors.GRAY}N/A{Colors.RESET}", cost_gate],
        ['Trades (1w)', f"{trades}", "-"]
    ]
    
    if HAS_TABULATE:
        print(tabulate(rows, headers=['Metric', 'Value', 'Gate'], tablefmt='simple'))
    else:
        print(f"{'Metric':<15} {'Value':<20} {'Gate':<10}")
        for row in rows:
            print(f"{row[0]:<15} {row[1]:<20} {row[2]:<10}")
    print()


def print_veto_breakdown(timeframe: str):
    """Print veto reason breakdown"""
    print(f"{Colors.BOLD}Veto Breakdown (24h) - {timeframe}{Colors.RESET}")
    print(f"{Colors.GRAY}{'─' * 80}{Colors.RESET}")
    
    vetoes = load_veto_data(timeframe, hours_back=24)
    
    if not vetoes:
        print(f"{Colors.GRAY}No veto data available{Colors.RESET}")
        print()
        return
    
    # Count by reason
    reason_counts = defaultdict(int)
    for veto in vetoes:
        reason = veto.get('reason_code', veto.get('veto_reason', 'UNKNOWN'))
        reason_counts[reason] += 1
    
    total = len(vetoes)
    
    # Sort by count
    sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
    
    rows = []
    for reason, count in sorted_reasons[:5]:  # Top 5
        pct = (count / total * 100) if total > 0 else 0
        rows.append([reason, count, f"{pct:.1f}%"])
    
    if HAS_TABULATE:
        print(tabulate(rows, headers=['Reason', 'Count', 'Percentage'], tablefmt='simple'))
    else:
        print(f"{'Reason':<30} {'Count':<10} {'Percentage':<12}")
        for row in rows:
            print(f"{row[0]:<30} {row[1]:<10} {row[2]:<12}")
    
    print(f"\nTotal Vetoes: {total}")
    print()


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def main():
    parser = argparse.ArgumentParser(description='Live Monitor Dashboard for MetaStackerBandit')
    parser.add_argument('--timeframe', type=str, default='5m', choices=['5m', '1h', '12h', '24h'],
                        help='Primary timeframe to monitor (default: 5m)')
    parser.add_argument('--all', action='store_true',
                        help='Show status for all timeframes')
    parser.add_argument('--refresh', type=int, default=0,
                        help='Auto-refresh interval in seconds (0 = no refresh)')
    parser.add_argument('--trades', type=int, default=10,
                        help='Number of recent trades to show (default: 10)')
    
    args = parser.parse_args()
    
    timeframes_to_show = ['5m', '1h', '12h', '24h'] if args.all else [args.timeframe]
    
    try:
        while True:
            if args.refresh > 0:
                clear_screen()
            
            print_header()
            
            # Bot status for all timeframes
            print_bot_status(timeframes_to_show)
            
            # Detailed metrics for primary timeframe
            primary_tf = timeframes_to_show[0]
            
            print_recent_trades(primary_tf, args.trades)
            print_performance_metrics(primary_tf)
            print_veto_breakdown(primary_tf)
            
            # If showing all, print compact metrics for other timeframes
            if args.all and len(timeframes_to_show) > 1:
                print(f"{Colors.BOLD}Other Timeframes{Colors.RESET}")
                print(f"{Colors.GRAY}{'─' * 80}{Colors.RESET}")
                for tf in timeframes_to_show[1:]:
                    kpi = load_kpi_data(tf, hours_back=24)
                    if kpi:
                        sharpe = kpi.get('Sharpe_1w', 0)
                        win_rate = kpi.get('win_rate_1w', 0) * 100 if kpi.get('win_rate_1w') else 0
                        print(f"{tf}: Sharpe={sharpe:.2f}, WinRate={win_rate:.1f}%")
                print()
            
            # Footer
            print(f"{Colors.GRAY}{'─' * 80}{Colors.RESET}")
            if args.refresh > 0:
                print(f"{Colors.GRAY}Refreshing in {args.refresh} seconds... (Ctrl+C to exit){Colors.RESET}")
                time.sleep(args.refresh)
            else:
                break
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitor stopped by user{Colors.RESET}")


if __name__ == "__main__":
    main()
