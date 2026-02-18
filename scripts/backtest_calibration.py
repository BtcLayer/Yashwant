#!/usr/bin/env python3
"""
Calibration Backtest - Ensemble 1.1 B2.4

Compare trading performance with and without probability calibration:
- Uncalibrated: Raw model probabilities
- Calibrated: Platt-scaled probabilities

Metrics evaluated:
- Total P&L (absolute and per-trade)
- Win rate
- Profit factor
- Sharpe ratio
- Trade count
- Expected Calibration Error (ECE)
"""

import argparse
import gzip
import json
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# Import calibration utilities for unpickling
try:
    from live_demo.calibration_utils import CalibrationWrapper
except ImportError:
    print("⚠️  Warning: Could not import CalibrationWrapper")
    CalibrationWrapper = None


@dataclass
class BacktestConfig:
    """Configuration for backtest."""
    cost_bps: float = 5.0  # Transaction costs
    expected_move_bps: float = 50.0  # Expected price move when directional
    enable_edge_gating: bool = True  # Gate trades with negative edge
    min_samples: int = 100  # Minimum samples for valid backtest


def load_calibrator(calibrator_path: Path) -> Optional[object]:
    """Load trained calibrator from pickle file."""
    try:
        with open(calibrator_path, 'rb') as f:
            calibrator = pickle.load(f)
        print(f"✅ Loaded calibrator from: {calibrator_path}")
        return calibrator
    except Exception as e:
        print(f"❌ Failed to load calibrator: {e}")
        return None


def apply_calibration(model_probs: np.ndarray, calibrator: Optional[object]) -> np.ndarray:
    """Apply calibrator to model probabilities.
    
    Args:
        model_probs: Raw model probabilities [N x 3] (down, neutral, up)
        calibrator: Trained CalibratedClassifierCV or CalibrationWrapper
    
    Returns:
        Calibrated probabilities [N x 3]
    """
    if calibrator is None:
        # Fallback: Simulate calibration effect for testing
        # Apply temperature scaling (softening effect)
        temperature = 1.5
        probs_scaled = np.exp(np.log(model_probs + 1e-10) / temperature)
        probs_normalized = probs_scaled / probs_scaled.sum(axis=1, keepdims=True)
        return probs_normalized
    
    try:
        # CalibrationWrapper expects [N x 3] and returns [N x 3]
        calibrated = calibrator.transform(model_probs)
        return calibrated
    except Exception as e:
        print(f"⚠️  Calibration failed: {e}, using temperature scaling fallback")
        # Fallback to temperature scaling
        temperature = 1.5
        probs_scaled = np.exp(np.log(model_probs + 1e-10) / temperature)
        probs_normalized = probs_scaled / probs_scaled.sum(axis=1, keepdims=True)
        return probs_normalized


def compute_edge_for_probs(
    p_up: float,
    p_down: float,
    p_neutral: float,
    cost_bps: float,
    expected_move_bps: float
) -> Dict:
    """Compute edge after costs for given probabilities."""
    # Expected return for LONG
    expected_return_long = p_up * expected_move_bps - p_down * expected_move_bps
    
    # Expected return for SHORT
    expected_return_short = p_down * expected_move_bps - p_up * expected_move_bps
    
    # Determine best direction based on relative advantage
    # Take any directional signal where one side is preferred
    MIN_EDGE_THRESHOLD = 0.01  # 1 bps minimum edge to consider
    
    if expected_return_long >= expected_return_short and abs(expected_return_long) > MIN_EDGE_THRESHOLD:
        direction = 1
        expected_return = expected_return_long
    elif expected_return_short > expected_return_long and abs(expected_return_short) > MIN_EDGE_THRESHOLD:
        direction = -1
        expected_return = expected_return_short
    else:
        direction = 0
        expected_return = 0.0
    
    edge_after_costs = expected_return - cost_bps if direction != 0 else 0.0
    should_trade = edge_after_costs > 0
    
    return {
        'direction': direction,
        'expected_return_bps': expected_return,
        'edge_after_costs_bps': edge_after_costs,
        'should_trade': should_trade
    }


def load_matched_data(logs_root: Path) -> List[Dict]:
    """Load and match signals to P&L outcomes.
    
    Uses same logic as assess_calibration_data.py for consistency.
    """
    signals = []
    
    # Scan signal files - use rglob to find all signals.jsonl files
    signal_files = list(logs_root.rglob("signals.jsonl"))
    
    if not signal_files:
        print(f"⚠️  No signal files found in {logs_root}")
        return []
    
    print(f"Found {len(signal_files)} signal file(s)")
    
    for signal_file in signal_files:
        try:
            with open(signal_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                        
                        # Extract probabilities from flattened structure (production logs)
                        p_up = rec.get('p_up')
                        p_down = rec.get('p_down')
                        p_neutral = rec.get('p_neutral')
                        
                        # Fallback to nested structure if not found
                        if p_up is None or p_down is None or p_neutral is None:
                            model = rec.get('model', {})
                            p_up = model.get('p_up', 0.0)
                            p_down = model.get('p_down', 0.0)
                            p_neutral = model.get('p_neutral', 1.0)
                        
                        p_up = float(p_up) if p_up is not None else 0.0
                        p_down = float(p_down) if p_down is not None else 0.0
                        p_neutral = float(p_neutral) if p_neutral is not None else 1.0
                        
                        # Normalize probabilities
                        total = p_up + p_down + p_neutral
                        if total > 0:
                            p_up /= total
                            p_down /= total
                            p_neutral /= total
                        
                        # Extract timestamp and symbol
                        ts = rec.get('ts')
                        symbol = rec.get('symbol') or rec.get('asset')
                        
                        if ts and symbol:
                            signals.append({
                                'ts': ts,
                                'symbol': symbol,
                                'p_up': p_up,
                                'p_down': p_down,
                                'p_neutral': p_neutral,
                                'bar_id': rec.get('bar_id'),
                                'signal_file': str(signal_file)
                            })
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue
        except Exception as e:
            print(f"⚠️  Error reading {signal_file}: {e}")
            continue
    
    print(f"Loaded {len(signals)} signals")
    
    # Load P&L records - use same glob pattern as assess_calibration_data.py
    pnl_records = []
    pnl_files = list(logs_root.rglob("pnl_equity_log.jsonl.gz"))
    
    if not pnl_files:
        print(f"⚠️  No P&L files found")
        return []
    
    print(f"Found {len(pnl_files)} P&L file(s)")
    
    for pnl_file in pnl_files:
        try:
            with gzip.open(pnl_file, 'rt', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                        pnl_records.append(rec)
                    except (json.JSONDecodeError, ValueError):
                        continue
        except Exception as e:
            if 'pnl_file' in locals() and pnl_file:
                print(f"⚠️  Error reading {pnl_file}: {e}")
            continue
    
    print(f"Loaded {len(pnl_records)} P&L records")
    
    # Match signals to P&L outcomes using same matching logic as assess_calibration_data.py
    matched = []
    TOLERANCE_MS = 30000  # ±30 seconds (same as assess_calibration_data.py)
    
    for signal in signals:
        signal_ts = signal.get('ts')
        signal_symbol = signal.get('symbol')
        signal_bar_id = signal.get('bar_id')
        
        if not signal_symbol:
            continue
        
        # Try bar_id matching first (most accurate)
        if signal_bar_id is not None:
            for pnl in pnl_records:
                pnl_symbol = pnl.get('asset') or pnl.get('symbol')
                pnl_bar_id = pnl.get('bar_id')
                
                if pnl_symbol == signal_symbol and pnl_bar_id == signal_bar_id:
                    pnl_value = pnl.get('pnl_total_usd') or pnl.get('realized_pnl_usd')
                    
                    if pnl_value is not None:
                        matched.append({
                            **signal,
                            'realized_pnl': float(pnl_value),
                            'win': float(pnl_value) > 0
                        })
                        break  # Found match, move to next signal
        
        # Fallback: timestamp matching
        if signal_ts and signal not in [m for m in matched]:
            best_match = None
            min_time_diff = float('inf')
            
            for pnl in pnl_records:
                pnl_symbol = pnl.get('asset') or pnl.get('symbol')
                if pnl_symbol != signal_symbol:
                    continue
                
                # Get P&L timestamp (try multiple fields)
                pnl_ts = pnl.get('ts')
                if pnl_ts is None:
                    ts_ist = pnl.get('ts_ist')
                    if ts_ist:
                        try:
                            if isinstance(ts_ist, str):
                                dt = datetime.fromisoformat(ts_ist.replace('Z', '+00:00'))
                                pnl_ts = int(dt.timestamp() * 1000)
                            else:
                                pnl_ts = int(ts_ist)
                        except:
                            continue
                
                if pnl_ts:
                    time_diff = abs(pnl_ts - signal_ts)
                    if time_diff <= TOLERANCE_MS and time_diff < min_time_diff:
                        min_time_diff = time_diff
                        best_match = pnl
            
            if best_match:
                pnl_value = best_match.get('pnl_total_usd') or best_match.get('realized_pnl_usd')
                if pnl_value is not None:
                    matched.append({
                        **signal,
                        'realized_pnl': float(pnl_value),
                        'win': float(pnl_value) > 0
                    })
    
    print(f"✅ Matched {len(matched)} signals to P&L outcomes ({len(matched)/len(signals)*100:.1f}% match rate)")
    return matched


def run_backtest_scenario(
    data: pd.DataFrame,
    cfg: BacktestConfig,
    use_calibrated: bool,
    calibrator: Optional[object] = None
) -> Dict:
    """Run backtest for one scenario (calibrated or uncalibrated).
    
    Args:
        data: DataFrame with columns [p_up, p_down, p_neutral, realized_pnl, win]
        cfg: Backtest configuration
        use_calibrated: If True, apply calibrator to probabilities
        calibrator: Trained calibrator (required if use_calibrated=True)
    
    Returns:
        Dictionary with performance metrics
    """
    if len(data) == 0:
        return {'error': 'No data'}
    
    # Prepare probability matrix [N x 3] for calibrator
    probs_raw = data[['p_down', 'p_neutral', 'p_up']].values
    
    # Debug: Check probability distribution
    if not use_calibrated:  # Only print once
        non_neutral = ((data['p_up'] > 0.01) | (data['p_down'] > 0.01)).sum()
        print(f"  DEBUG: {len(data)} total samples, {non_neutral} with directional bias (p_up or p_down > 0.01)")
        if non_neutral > 0:
            directional_df = data[(data['p_up'] > 0.01) | (data['p_down'] > 0.01)]
            print(f"  DEBUG: Directional signals - mean p_up={directional_df['p_up'].mean():.4f}, mean p_down={directional_df['p_down'].mean():.4f}")
    
    # Apply calibration if requested
    if use_calibrated:
        # apply_calibration handles None calibrator with temperature scaling fallback
        probs = apply_calibration(probs_raw, calibrator)
    else:
        probs = probs_raw
    
    # Extract calibrated/uncalibrated probabilities
    p_down_adj = probs[:, 0]
    p_neutral_adj = probs[:, 1]
    p_up_adj = probs[:, 2]
    
    # Compute edge and trade decisions
    trades = []
    for i in range(len(data)):
        edge_result = compute_edge_for_probs(
            p_up=p_up_adj[i],
            p_down=p_down_adj[i],
            p_neutral=p_neutral_adj[i],
            cost_bps=cfg.cost_bps,
            expected_move_bps=cfg.expected_move_bps
        )
        
        # Determine if trade would be taken
        if cfg.enable_edge_gating:
            take_trade = edge_result['should_trade']
        else:
            # Without edge gating, take any non-neutral signal
            take_trade = edge_result['direction'] != 0
        
        if take_trade:
            # Record trade outcome
            realized_pnl = data.iloc[i]['realized_pnl']
            win = data.iloc[i]['win']
            
            trades.append({
                'direction': edge_result['direction'],
                'edge_bps': edge_result['edge_after_costs_bps'],
                'realized_pnl': realized_pnl,
                'win': win,
                'p_up': p_up_adj[i],
                'p_down': p_down_adj[i],
                'p_neutral': p_neutral_adj[i]
            })
    
    if not trades:
        return {
            'trade_count': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_pnl_per_trade': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'ece': 0.0
        }
    
    # Calculate metrics
    trade_df = pd.DataFrame(trades)
    total_pnl = trade_df['realized_pnl'].sum()
    wins = trade_df['win'].sum()
    win_rate = wins / len(trades)
    avg_pnl = total_pnl / len(trades)
    
    # Profit factor
    gross_profit = trade_df[trade_df['realized_pnl'] > 0]['realized_pnl'].sum()
    gross_loss = abs(trade_df[trade_df['realized_pnl'] < 0]['realized_pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Sharpe ratio (annualized, assuming 5m bars)
    pnl_series = trade_df['realized_pnl'].values
    if len(pnl_series) > 1:
        sharpe_ratio = (np.mean(pnl_series) / np.std(pnl_series)) * np.sqrt(252 * 288)  # 5m bars
    else:
        sharpe_ratio = 0.0
    
    # Max drawdown
    cumulative_pnl = np.cumsum(pnl_series)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdown = running_max - cumulative_pnl
    max_drawdown = np.max(drawdown)
    
    # ECE (Expected Calibration Error)
    ece = compute_ece(trade_df)
    
    return {
        'trade_count': len(trades),
        'total_pnl': round(total_pnl, 2),
        'win_rate': round(win_rate, 4),
        'avg_pnl_per_trade': round(avg_pnl, 2),
        'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 999.0,
        'sharpe_ratio': round(sharpe_ratio, 3),
        'max_drawdown': round(max_drawdown, 2),
        'ece': round(ece, 4)
    }


def compute_ece(trade_df: pd.DataFrame, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error."""
    if len(trade_df) == 0:
        return 1.0
    
    # Use max probability as confidence
    trade_df['confidence'] = trade_df[['p_up', 'p_down']].max(axis=1)
    
    # Bin by confidence
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(trade_df['confidence'], bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    
    ece = 0.0
    total_count = len(trade_df)
    
    for bin_idx in range(n_bins):
        bin_mask = bin_indices == bin_idx
        bin_data = trade_df[bin_mask]
        
        if len(bin_data) == 0:
            continue
        
        # Average confidence in bin
        avg_confidence = bin_data['confidence'].mean()
        
        # Accuracy in bin
        accuracy = bin_data['win'].mean()
        
        # Weight by bin size
        weight = len(bin_data) / total_count
        
        ece += weight * abs(avg_confidence - accuracy)
    
    return ece


def print_comparison_report(
    uncalibrated: Dict,
    calibrated: Dict,
    cfg: BacktestConfig
):
    """Print comparison between calibrated and uncalibrated performance."""
    
    print("\n" + "="*80)
    print("CALIBRATION BACKTEST REPORT - Ensemble 1.1 B2.4")
    print("="*80)
    print()
    
    print(f"Configuration:")
    print(f"  Transaction costs:     {cfg.cost_bps:.1f} bps")
    print(f"  Expected move:         {cfg.expected_move_bps:.1f} bps")
    print(f"  Edge gating:           {'Enabled' if cfg.enable_edge_gating else 'Disabled'}")
    print()
    
    print("="*80)
    print("PERFORMANCE COMPARISON")
    print("="*80)
    print()
    
    metrics = [
        ('Trade Count', 'trade_count', ''),
        ('Total P&L', 'total_pnl', ' USD'),
        ('Avg P&L/Trade', 'avg_pnl_per_trade', ' USD'),
        ('Win Rate', 'win_rate', '%'),
        ('Profit Factor', 'profit_factor', 'x'),
        ('Sharpe Ratio', 'sharpe_ratio', ''),
        ('Max Drawdown', 'max_drawdown', ' USD'),
        ('ECE', 'ece', '')
    ]
    
    print(f"{'Metric':<20} {'Uncalibrated':>15} {'Calibrated':>15} {'Improvement':>15}")
    print("-"*80)
    
    for metric_name, metric_key, unit in metrics:
        uncal_val = uncalibrated.get(metric_key, 0)
        cal_val = calibrated.get(metric_key, 0)
        
        # Format values
        if metric_key == 'win_rate':
            uncal_str = f"{uncal_val*100:.1f}%"
            cal_str = f"{cal_val*100:.1f}%"
            improvement = (cal_val - uncal_val) * 100
            imp_str = f"{improvement:+.1f}pp"
        elif metric_key in ['total_pnl', 'avg_pnl_per_trade', 'max_drawdown']:
            uncal_str = f"${uncal_val:.2f}"
            cal_str = f"${cal_val:.2f}"
            if uncal_val != 0:
                improvement = ((cal_val - uncal_val) / abs(uncal_val)) * 100
                imp_str = f"{improvement:+.1f}%"
            else:
                imp_str = "N/A"
        elif metric_key == 'trade_count':
            uncal_str = f"{uncal_val}"
            cal_str = f"{cal_val}"
            change = cal_val - uncal_val
            imp_str = f"{change:+d}"
        else:
            uncal_str = f"{uncal_val:.3f}{unit}"
            cal_str = f"{cal_val:.3f}{unit}"
            if uncal_val != 0:
                improvement = ((cal_val - uncal_val) / abs(uncal_val)) * 100
                imp_str = f"{improvement:+.1f}%"
            else:
                imp_str = "N/A"
        
        print(f"{metric_name:<20} {uncal_str:>15} {cal_str:>15} {imp_str:>15}")
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    
    # Determine winner
    if calibrated['total_pnl'] > uncalibrated['total_pnl']:
        pnl_improvement = calibrated['total_pnl'] - uncalibrated['total_pnl']
        pnl_pct = (pnl_improvement / abs(uncalibrated['total_pnl'])) * 100 if uncalibrated['total_pnl'] != 0 else 0
        print(f"✅ Calibration IMPROVED total P&L by ${pnl_improvement:.2f} ({pnl_pct:+.1f}%)")
    elif calibrated['total_pnl'] < uncalibrated['total_pnl']:
        pnl_decline = uncalibrated['total_pnl'] - calibrated['total_pnl']
        pnl_pct = (pnl_decline / abs(uncalibrated['total_pnl'])) * 100 if uncalibrated['total_pnl'] != 0 else 0
        print(f"⚠️  Calibration DECREASED total P&L by ${pnl_decline:.2f} ({-pnl_pct:.1f}%)")
    else:
        print(f"➖ Calibration had NO EFFECT on total P&L")
    
    print()
    
    # ECE comparison
    if calibrated['ece'] < uncalibrated['ece']:
        ece_improvement = uncalibrated['ece'] - calibrated['ece']
        print(f"✅ Calibration IMPROVED ECE by {ece_improvement:.4f} (better calibration)")
    else:
        ece_decline = calibrated['ece'] - uncalibrated['ece']
        print(f"⚠️  Calibration WORSENED ECE by {ece_decline:.4f} (overfitting?)")
    
    print()
    
    # Trade count comparison
    trade_diff = calibrated['trade_count'] - uncalibrated['trade_count']
    if trade_diff > 0:
        print(f"📈 Calibration enabled {trade_diff} additional trades")
    elif trade_diff < 0:
        print(f"📉 Calibration filtered {-trade_diff} trades")
    else:
        print(f"➖ Calibration did not change trade count")
    
    print()
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description="Backtest calibration impact on trading performance")
    parser.add_argument(
        '--logs-root',
        type=Path,
        default=Path('paper_trading_outputs/logs'),
        help='Root directory containing log files'
    )
    parser.add_argument(
        '--calibrator',
        type=Path,
        default=Path('live_demo/models/calibrator_5m_platt.pkl'),
        help='Path to trained calibrator pickle file'
    )
    parser.add_argument(
        '--cost-bps',
        type=float,
        default=5.0,
        help='Transaction costs in basis points'
    )
    parser.add_argument(
        '--expected-move-bps',
        type=float,
        default=50.0,
        help='Expected price move when directional'
    )
    parser.add_argument(
        '--no-edge-gating',
        action='store_true',
        help='Disable edge gating (take all directional signals)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Optional JSON output file for backtest results'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.logs_root.exists():
        print(f"❌ Error: Logs root does not exist: {args.logs_root}")
        return 1
    
    if not args.calibrator.exists():
        print(f"❌ Error: Calibrator file does not exist: {args.calibrator}")
        return 1
    
    # Load calibrator
    calibrator = None
    if args.calibrator.exists():
        calibrator = load_calibrator(args.calibrator)
        if calibrator is None:
            print(f"⚠️  Warning: Could not load calibrator, will use simulated calibration")
    else:
        print(f"⚠️  Warning: Calibrator file not found, will use simulated calibration")
    
    # Load matched data
    print(f"\nScanning logs in: {args.logs_root}")
    matched_data = load_matched_data(args.logs_root)
    
    if len(matched_data) < 100:
        print(f"\n❌ Insufficient data: Only {len(matched_data)} matched samples (need ≥100)")
        return 1
    
    # Convert to DataFrame
    df = pd.DataFrame(matched_data)
    print(f"✅ Prepared {len(df)} samples for backtest")
    print()
    
    # Configure backtest
    cfg = BacktestConfig(
        cost_bps=args.cost_bps,
        expected_move_bps=args.expected_move_bps,
        enable_edge_gating=not args.no_edge_gating
    )
    
    # Run uncalibrated backtest
    print("Running uncalibrated backtest...")
    uncalibrated_results = run_backtest_scenario(
        data=df,
        cfg=cfg,
        use_calibrated=False,
        calibrator=None
    )
    
    # Run calibrated backtest
    print("Running calibrated backtest...")
    calibrated_results = run_backtest_scenario(
        data=df,
        cfg=cfg,
        use_calibrated=True,
        calibrator=calibrator
    )
    
    # Print comparison report
    print_comparison_report(uncalibrated_results, calibrated_results, cfg)
    
    # Save to JSON if requested
    if args.output:
        output_data = {
            'config': {
                'cost_bps': cfg.cost_bps,
                'expected_move_bps': cfg.expected_move_bps,
                'enable_edge_gating': cfg.enable_edge_gating,
                'sample_count': len(df),
                'calibrator_path': str(args.calibrator),
                'timestamp': datetime.now().isoformat()
            },
            'uncalibrated': uncalibrated_results,
            'calibrated': calibrated_results
        }
        
        with args.output.open('w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"\n📝 Results saved to: {args.output}")
    
    # Exit code: 0 if calibration improved, 1 otherwise
    improvement = calibrated_results['total_pnl'] > uncalibrated_results['total_pnl']
    return 0 if improvement else 1


if __name__ == '__main__':
    sys.exit(main())
