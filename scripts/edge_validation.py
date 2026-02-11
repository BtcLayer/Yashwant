"""
Edge Validation Tool - Day 4 Task 5
Compare live trading performance against backtest baselines
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics
import math

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'

def load_backtest_baseline(timeframe: str, baseline_dir: str = "backtest_baselines") -> Optional[Dict]:
    """
    Load backtest baseline metrics for a given timeframe
    
    Args:
        timeframe: Trading timeframe (5m, 1h, 12h, 24h)
        baseline_dir: Directory containing baseline files
    
    Returns:
        Dictionary with backtest metrics or None if not found
    """
    baseline_path = Path(baseline_dir) / f"backtest_baseline_{timeframe}.json"
    
    if not baseline_path.exists():
        print(f"⚠️  Baseline not found: {baseline_path}")
        return None
    
    try:
        with open(baseline_path, 'r') as f:
            data = json.load(f)
            return data.get('metrics', {})
    except Exception as e:
        print(f"❌ Error loading baseline: {e}")
        return None


def load_jsonl_files(directory: str, hours_back: int = 24) -> List[Dict]:
    """Load JSONL log files with time filtering"""
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    records = []
    
    if not os.path.exists(directory):
        return records
    
    # Try both flat and date-partitioned structure
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.jsonl'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        for line in f:
                            try:
                                record = json.loads(line.strip())
                                
                                # Parse timestamp
                                ts_str = record.get('timestamp', '')
                                if ts_str:
                                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                    if ts.replace(tzinfo=None) >= cutoff_time:
                                        records.append(record)
                            except:
                                continue
                except:
                    continue
    
    return records


def load_live_performance(timeframe: str, days: int = 7) -> Dict:
    """
    Load live trading performance metrics from logs
    
    Args:
        timeframe: Trading timeframe (5m, 1h, 12h, 24h)
        days: Number of days to look back
    
    Returns:
        Dictionary with live performance metrics
    """
    log_dir = f"paper_trading_outputs/{timeframe}"
    kpi_dir = f"{log_dir}/kpi_scorecard"
    exec_dir = f"{log_dir}/execution"
    
    hours = days * 24
    
    # Load KPI scorecards
    kpi_records = load_jsonl_files(kpi_dir, hours_back=hours)
    
    # Load executions for PnL calculation
    exec_records = load_jsonl_files(exec_dir, hours_back=hours)
    
    if not kpi_records:
        return {
            'sharpe': None,
            'win_rate': None,
            'max_dd': None,
            'n_trades': 0,
            'total_pnl': 0.0,
            'returns': []
        }
    
    # Get most recent KPI
    kpi_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    latest_kpi = kpi_records[0]
    
    # Extract metrics
    sharpe = latest_kpi.get('Sharpe_1w')
    win_rate = latest_kpi.get('win_rate_1w')
    max_dd = latest_kpi.get('max_DD_pct')
    total_trades = latest_kpi.get('total_trades_1w', 0)
    
    # Calculate total PnL from executions
    organic_execs = [e for e in exec_records if e.get('trade_type') == 'organic']
    total_pnl = sum(float(e.get('pnl_usd', 0)) for e in organic_execs)
    
    # Build returns list for statistical test
    returns = [float(e.get('pnl_usd', 0)) for e in organic_execs]
    
    return {
        'sharpe': sharpe,
        'win_rate': win_rate,
        'max_dd': max_dd,
        'n_trades': total_trades,
        'total_pnl': total_pnl,
        'returns': returns
    }


def compare_metrics(backtest: Dict, live: Dict) -> Dict:
    """
    Compare live vs backtest metrics and calculate deviations
    
    Args:
        backtest: Backtest baseline metrics
        live: Live trading metrics
    
    Returns:
        Dictionary with comparison results and status
    """
    comparisons = {}
    
    metrics_to_compare = [
        ('sharpe', 'Sharpe Ratio', False),  # False = lower is worse
        ('win_rate', 'Win Rate', False),
        ('max_dd', 'Max Drawdown', True),  # True = higher is worse
    ]
    
    for metric_key, metric_name, higher_is_worse in metrics_to_compare:
        backtest_val = backtest.get(metric_key)
        live_val = live.get(metric_key)
        
        if backtest_val is None or live_val is None:
            comparisons[metric_key] = {
                'name': metric_name,
                'backtest': backtest_val,
                'live': live_val,
                'deviation_pct': None,
                'status': 'UNKNOWN'
            }
            continue
        
        # Calculate percentage deviation
        if backtest_val != 0:
            deviation_pct = ((live_val - backtest_val) / abs(backtest_val)) * 100
        else:
            deviation_pct = 0 if live_val == 0 else 100
        
        # Determine status based on deviation thresholds
        # For max_dd (higher is worse), flip the logic
        if higher_is_worse:
            deviation_pct = -deviation_pct  # Flip sign for "higher is worse" metrics
        
        if abs(deviation_pct) <= 20:
            status = 'GOOD'
        elif abs(deviation_pct) <= 40:
            status = 'WARN'
        else:
            status = 'BAD'
        
        # If live is doing BETTER than backtest, always mark as GOOD
        if deviation_pct > 0:
            status = 'GOOD'
        
        comparisons[metric_key] = {
            'name': metric_name,
            'backtest': backtest_val,
            'live': live_val,
            'deviation_pct': deviation_pct,
            'status': status
        }
    
    return comparisons


def statistical_significance_test(live_returns: List[float], expected_mean: float = 0.0) -> Dict:
    """
    Perform t-test to check if live returns significantly differ from expected
    
    Args:
        live_returns: List of individual trade PnLs
        expected_mean: Expected mean return from backtest (default 0)
    
    Returns:
        Dictionary with t-stat, p-value, and significance flag
    """
    if len(live_returns) < 30:  # Not enough data for reliable test
        return {
            'n_samples': len(live_returns),
            't_stat': None,
            'p_value': None,
            'significant': False,
            'note': 'Insufficient samples (need >= 30)'
        }
    
    mean_return = statistics.mean(live_returns)
    std_return = statistics.stdev(live_returns)
    n = len(live_returns)
    
    # t-statistic
    if std_return == 0:
        t_stat = 0
    else:
        t_stat = (mean_return - expected_mean) / (std_return / math.sqrt(n))
    
    # Approximate p-value (two-tailed)
    # For t-distribution, use simplified approximation
    # For large n, approaches normal distribution
    # Critical values: t(0.05, df) ≈ 2.0 for large df
    significant = abs(t_stat) > 2.0  # Simplified threshold
    
    return {
        'n_samples': n,
        'mean_return': mean_return,
        't_stat': t_stat,
        'significant': significant,
        'note': 'Returns significantly differ from expected' if significant else 'Returns within expected range'
    }


def detect_systematic_deviations(timeframe: str, days: int = 7) -> Dict:
    """
    Detect systematic cost deviations (impact, funding, fees)
    
    Args:
        timeframe: Trading timeframe
        days: Number of days to analyze
    
    Returns:
        Dictionary with cost analysis results
    """
    log_dir = f"paper_trading_outputs/{timeframe}"
    attr_dir = f"{log_dir}/pnl_attribution"
    
    hours = days * 24
    attr_records = load_jsonl_files(attr_dir, hours_back=hours)
    
    if not attr_records:
        return {
            'avg_impact_bps': None,
            'avg_fees_bps': None,
            'total_cost_bps': None,
            'status': 'NO_DATA'
        }
    
    # Sort by timestamp and get latest
    attr_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    latest_attr = attr_records[0]
    
    # Extract cost components
    cum_impact = latest_attr.get('cumulative_impact', 0)
    cum_fees = latest_attr.get('cumulative_fees', 0)
    cum_volume = latest_attr.get('cumulative_volume', 1)  # Prevent division by zero
    
    # Calculate bps costs
    impact_bps = (abs(cum_impact) / cum_volume * 10000) if cum_volume > 0 else 0
    fees_bps = (abs(cum_fees) / cum_volume * 10000) if cum_volume > 0 else 0
    total_cost_bps = impact_bps + fees_bps
    
    # Determine status
    if total_cost_bps <= 7.0:
        status = 'GOOD'
    elif total_cost_bps <= 10.0:
        status = 'WARN'
    else:
        status = 'BAD'
    
    return {
        'avg_impact_bps': round(impact_bps, 2),
        'avg_fees_bps': round(fees_bps, 2),
        'total_cost_bps': round(total_cost_bps, 2),
        'status': status
    }


def format_status(status: str) -> str:
    """Format status with color"""
    if status == 'GOOD':
        return f"{GREEN}✅ GOOD{RESET}"
    elif status == 'WARN':
        return f"{YELLOW}⚠️  WARN{RESET}"
    elif status == 'BAD':
        return f"{RED}❌ BAD{RESET}"
    else:
        return f"❓ {status}"


def generate_report(timeframe: str, days: int = 7, baseline_dir: str = "backtest_baselines") -> None:
    """
    Generate comprehensive edge validation report
    
    Args:
        timeframe: Trading timeframe (5m, 1h, 12h, 24h)
        days: Number of days to analyze
        baseline_dir: Directory containing baseline files
    """
    print("=" * 80)
    print(f"{BOLD}Edge Validation Report - {timeframe.upper()} Bot{RESET}")
    print("=" * 80)
    print(f"Analysis Period: Last {days} days")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load backtest baseline
    print(f"📊 Loading backtest baseline...")
    backtest = load_backtest_baseline(timeframe, baseline_dir)
    
    if backtest is None:
        print(f"{RED}❌ No backtest baseline found. Run backtest first.{RESET}")
        print()
        print("To create baseline:")
        print(f"  1. Run backtest: python backtest_engine.py --timeframe {timeframe}")
        print(f"  2. Export baseline: python scripts/export_backtest_baseline.py")
        return
    
    print(f"{GREEN}✅ Baseline loaded{RESET}")
    print(f"   Sharpe: {backtest.get('sharpe', 'N/A')}, Win Rate: {backtest.get('win_rate', 'N/A')}")
    print()
    
    # Load live performance
    print(f"📈 Loading live performance data...")
    live = load_live_performance(timeframe, days)
    
    if live['sharpe'] is None:
        print(f"{YELLOW}⚠️  No live trading data found{RESET}")
        print()
        return
    
    print(f"{GREEN}✅ Live data loaded{RESET}")
    print(f"   Trades: {live['n_trades']}, Total PnL: ${live['total_pnl']:.2f}")
    print()
    
    # Compare metrics
    print("=" * 80)
    print(f"{BOLD}PERFORMANCE COMPARISON{RESET}")
    print("=" * 80)
    print()
    
    comparisons = compare_metrics(backtest, live)
    
    # Print comparison table
    print(f"{'Metric':<20} {'Backtest':<15} {'Live':<15} {'Deviation':<15} {'Status':<15}")
    print("-" * 80)
    
    for metric_key, comp in comparisons.items():
        metric_name = comp['name']
        backtest_val = comp['backtest']
        live_val = comp['live']
        dev_pct = comp['deviation_pct']
        status = comp['status']
        
        # Format values
        if metric_key == 'win_rate':
            backtest_str = f"{backtest_val*100:.1f}%" if backtest_val is not None else "N/A"
            live_str = f"{live_val*100:.1f}%" if live_val is not None else "N/A"
        elif metric_key == 'max_dd':
            backtest_str = f"{backtest_val:.1f}%" if backtest_val is not None else "N/A"
            live_str = f"{live_val:.1f}%" if live_val is not None else "N/A"
        else:
            backtest_str = f"{backtest_val:.2f}" if backtest_val is not None else "N/A"
            live_str = f"{live_val:.2f}" if live_val is not None else "N/A"
        
        dev_str = f"{dev_pct:+.1f}%" if dev_pct is not None else "N/A"
        status_str = format_status(status)
        
        print(f"{metric_name:<20} {backtest_str:<15} {live_str:<15} {dev_str:<15} {status_str:<15}")
    
    print()
    
    # Statistical significance test
    if len(live['returns']) >= 30:
        print("=" * 80)
        print(f"{BOLD}STATISTICAL SIGNIFICANCE TEST{RESET}")
        print("=" * 80)
        print()
        
        expected_return = backtest.get('total_return', 0) / backtest.get('n_trades', 1)
        sig_test = statistical_significance_test(live['returns'], expected_return)
        
        print(f"Sample Size: {sig_test['n_samples']} trades")
        print(f"Mean Return: ${sig_test.get('mean_return', 0):.2f}")
        print(f"t-statistic: {sig_test.get('t_stat', 0):.2f}")
        print(f"Significance: {sig_test['note']}")
        print()
    
    # Cost analysis
    print("=" * 80)
    print(f"{BOLD}COST ANALYSIS{RESET}")
    print("=" * 80)
    print()
    
    cost_analysis = detect_systematic_deviations(timeframe, days)
    
    if cost_analysis['status'] == 'NO_DATA':
        print(f"{YELLOW}⚠️  No cost data available{RESET}")
    else:
        print(f"Impact Cost:    {cost_analysis['avg_impact_bps']} bps")
        print(f"Fee Cost:       {cost_analysis['avg_fees_bps']} bps")
        print(f"Total Cost:     {cost_analysis['total_cost_bps']} bps")
        print(f"Cost Status:    {format_status(cost_analysis['status'])}")
        print()
        print(f"Threshold: ≤7.0 bps (GOOD), ≤10.0 bps (WARN), >10.0 bps (BAD)")
    
    print()
    
    # Overall summary
    print("=" * 80)
    print(f"{BOLD}OVERALL EDGE VALIDATION{RESET}")
    print("=" * 80)
    print()
    
    statuses = [comp['status'] for comp in comparisons.values()]
    if 'BAD' in statuses:
        overall = 'BAD'
        message = "Live performance significantly deviates from backtest. Investigate immediately."
    elif 'WARN' in statuses:
        overall = 'WARN'
        message = "Live performance shows some deviations. Monitor closely."
    else:
        overall = 'GOOD'
        message = "Live performance aligns with backtest expectations."
    
    print(f"Overall Status: {format_status(overall)}")
    print(f"Assessment: {message}")
    print()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Edge Validation Tool')
    parser.add_argument('--timeframe', type=str, default='5m', help='Timeframe (5m, 1h, 12h, 24h)')
    parser.add_argument('--days', type=int, default=7, help='Days to analyze')
    parser.add_argument('--baseline-dir', type=str, default='backtest_baselines', help='Baseline directory')
    
    args = parser.parse_args()
    
    generate_report(args.timeframe, args.days, args.baseline_dir)
