"""
Export Backtest Baseline - Day 4 Task 2
Creates baseline JSON files from backtest results for live comparison
"""

import json
import os
import glob
from datetime import datetime
from typing import Dict, List, Optional


def aggregate_backtest_results(results_dir: str = 'backtest_results') -> Dict:
    """
    Aggregate multiple backtest result files into a single baseline
    
    Args:
        results_dir: Directory containing backtest JSON files
        
    Returns:
        Dictionary with aggregated metrics
    """
    if not os.path.exists(results_dir):
        print(f"❌ Directory not found: {results_dir}")
        return {}
    
    json_files = glob.glob(os.path.join(results_dir, '*.json'))
    
    if not json_files:
        print(f"❌ No JSON files found in {results_dir}")
        return {}
    
    print(f"📂 Found {len(json_files)} backtest result files")
    
    # Collect all metrics
    all_metrics = []
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                if 'metrics' in data:
                    all_metrics.append(data['metrics'])
        except Exception as e:
            print(f"⚠️  Failed to load {json_file}: {e}")
    
    if not all_metrics:
        print("❌ No valid metrics found in result files")
        return {}
    
    # Aggregate metrics (average across all backtests)
    aggregated = {}
    metric_keys = set()
    for m in all_metrics:
        metric_keys.update(m.keys())
    
    for key in metric_keys:
        values = [m.get(key) for m in all_metrics if m.get(key) is not None]
        if values:
            # For counts, sum; for ratios/percentages, average
            if key in ['n_trades', 'turnover']:
                aggregated[key] = sum(values) / len(values)  # Still average for consistency
            else:
                aggregated[key] = sum(values) / len(values)
    
    print(f"✅ Aggregated {len(all_metrics)} backtest results")
    return aggregated


def create_baseline_json(
    metrics: Dict,
    timeframe: str,
    output_path: Optional[str] = None
) -> str:
    """
    Create a baseline JSON file for a specific timeframe
    
    Args:
        metrics: Aggregated metrics dictionary
        timeframe: Timeframe identifier (e.g., '5m', '1h', '12h', '24h')
        output_path: Optional custom output path
        
    Returns:
        Path to created baseline file
    """
    if output_path is None:
        output_path = f'backtest_baseline_{timeframe}.json'
    
    baseline_data = {
        'timeframe': timeframe,
        'version': '1.0',
        'created_at': datetime.now().isoformat(),
        'metrics': {
            'sharpe': metrics.get('sharpe', metrics.get('hit_rate', 0.0)),  # Fallback compatibility
            'win_rate': metrics.get('hit_rate', metrics.get('win_rate', 0.0)),
            'max_dd': metrics.get('maxDD', metrics.get('max_dd', 0.0)),
            'sortino': metrics.get('sortino'),
            'n_trades': int(metrics.get('n_trades', 0)),
            'turnover': metrics.get('turnover', 0.0),
            'final_equity': metrics.get('final_equity', 1.0),
            'total_return': metrics.get('total_return', 0.0) if 'total_return' in metrics else (metrics.get('final_equity', 1.0) - 1.0)
        },
        'description': f'Backtest baseline for {timeframe} trading bot',
        'usage': 'Compare live trading performance against this baseline using edge_validation.py'
    }
    
    with open(output_path, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    
    print(f"✅ Baseline created: {output_path}")
    return output_path


def export_mock_baseline(timeframe: str = '5m'):
    """
    Create a mock baseline for testing (when no backtest results exist)
    
    Args:
        timeframe: Timeframe identifier
    """
    mock_metrics = {
        'sharpe': 1.85,
        'win_rate': 0.562,
        'max_dd': 0.085,
        'sortino': 2.20,
        'n_trades': 1247,
        'turnover': 450.0,
        'final_equity': 1.432,
        'total_return': 0.432
    }
    
    create_baseline_json(mock_metrics, timeframe)
    print(f"✅ Mock baseline created for {timeframe} (test data)")


def main():
    """Main execution"""
    print("=" * 80)
    print("Export Backtest Baseline - Day 4 Task 2")
    print("=" * 80)
    print()
    
    # Try to aggregate existing backtest results
    aggregated = aggregate_backtest_results()
    
    if aggregated:
        # Create baseline for 5m (default)
        timeframe = '5m'
        create_baseline_json(aggregated, timeframe)
        
        print("\n" + "=" * 80)
        print("📊 Created Baseline Summary:")
        print("=" * 80)
        print(f"Timeframe: {timeframe}")
        print(f"Sharpe Ratio: {aggregated.get('sharpe', 'N/A'):.2f}" if aggregated.get('sharpe') else "Sharpe Ratio: N/A")
        print(f"Win Rate: {aggregated.get('hit_rate', aggregated.get('win_rate', 0)) * 100:.1f}%")
        print(f"Max Drawdown: {aggregated.get('maxDD', aggregated.get('max_dd', 0)) * 100:.1f}%")
        print(f"Trades: {int(aggregated.get('n_trades', 0))}")
        print("=" * 80)
    else:
        # Create mock baseline for testing
        print("⚠️  No backtest results found. Creating mock baseline for testing...")
        print()
        export_mock_baseline('5m')
        
        print("\n" + "=" * 80)
        print("ℹ️  Mock Baseline Created")
        print("=" * 80)
        print("To create a real baseline:")
        print("  1. Run backtest with save_results=True")
        print("  2. Re-run this script to aggregate results")
        print("=" * 80)


if __name__ == "__main__":
    main()
