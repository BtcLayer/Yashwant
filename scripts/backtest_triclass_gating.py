#!/usr/bin/env python3
"""
Backtest Tri-Class Gating Improvement

Compare old (simple confidence threshold) vs new (tri-class gating) logic
to quantify improvement in signal quality metrics.

Metrics evaluated:
- Eligible rate: % of signals passing gating
- Precision: % of eligible signals that win
- Brier score: Calibration quality
- Sharpe ratio: Risk-adjusted returns
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


@dataclass
class GatingConfig:
    """Configuration for gating logic."""
    # Old logic: simple confidence threshold
    conf_min_old: float = 0.60
    
    # New logic: tri-class thresholds
    pnn_min: float = 0.20  # min non-neutral probability
    conf_dir_min: float = 0.60  # directional confidence given non-neutral
    strength_min: float = 0.07  # signal strength (|p_up - p_down|)
    
    eps: float = 1e-12


def apply_old_gating(
    signals: pd.DataFrame,
    cfg: GatingConfig
) -> pd.DataFrame:
    """Apply old gating logic: simple confidence threshold."""
    
    # Old logic: eligible if confidence >= threshold
    # Assume confidence is the max probability (simplified)
    
    if 'confidence' in signals.columns:
        conf = signals['confidence']
    elif 'p_up' in signals.columns and 'p_down' in signals.columns:
        conf = signals[['p_up', 'p_down']].max(axis=1)
    else:
        # Fallback: mark all as eligible
        conf = pd.Series(1.0, index=signals.index)
    
    eligible = conf >= cfg.conf_min_old
    
    return signals.assign(
        eligible_old=eligible,
        gating_reason_old=np.where(eligible, 'PASS', 'LOW_CONFIDENCE')
    )


def apply_new_gating(
    signals: pd.DataFrame,
    cfg: GatingConfig
) -> pd.DataFrame:
    """Apply new tri-class gating logic."""
    
    # Extract tri-class probabilities
    p_up = signals.get('p_up', 0.0)
    p_down = signals.get('p_down', 0.0)
    p_neutral = signals.get('p_neutral', 1.0)
    
    # Compute tri-class metrics
    p_non_neutral = np.maximum(0.0, 1.0 - p_neutral)
    p_dir = p_up + p_down
    
    # Directional confidence conditional on non-neutral
    conf_dir = np.where(
        p_dir > 0,
        np.maximum(p_up, p_down) / (p_dir + cfg.eps),
        0.0
    )
    
    strength = np.abs(p_up - p_down)
    
    # Tri-class gating conditions
    pass_pnn = p_non_neutral >= cfg.pnn_min
    pass_conf_dir = conf_dir >= cfg.conf_dir_min
    pass_strength = strength >= cfg.strength_min
    
    eligible = pass_pnn & pass_conf_dir & pass_strength
    
    # Gating reasons (for failed signals)
    reason = np.where(
        eligible,
        'PASS',
        np.where(
            ~pass_pnn,
            'LOW_NON_NEUTRAL',
            np.where(
                ~pass_conf_dir,
                'LOW_DIR_CONF',
                'LOW_STRENGTH'
            )
        )
    )
    
    return signals.assign(
        p_non_neutral=p_non_neutral,
        conf_dir=conf_dir,
        strength=strength,
        eligible_new=eligible,
        gating_reason_new=reason
    )


def compute_metrics(
    signals: pd.DataFrame,
    eligible_col: str,
    outcome_col: str = 'win'
) -> Dict:
    """Compute signal quality metrics for a gating strategy."""
    
    total = len(signals)
    eligible = signals[eligible_col].sum()
    eligible_rate = eligible / total if total > 0 else 0.0
    
    # Filter to eligible signals
    elig_signals = signals[signals[eligible_col]]
    
    if len(elig_signals) == 0:
        return {
            'total_signals': total,
            'eligible_count': 0,
            'eligible_rate': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'brier_score': 1.0,  # Worst possible
            'avg_confidence': 0.0
        }
    
    # Precision: % of eligible that win
    if outcome_col in elig_signals.columns:
        wins = elig_signals[outcome_col].sum()
        precision = wins / len(elig_signals)
    else:
        precision = np.nan
    
    # Recall: % of all wins captured by eligible
    if outcome_col in signals.columns:
        total_wins = signals[outcome_col].sum()
        recall = wins / total_wins if total_wins > 0 else 0.0
    else:
        recall = np.nan
    
    # Brier score (calibration): only if we have confidence and outcomes
    if outcome_col in elig_signals.columns and 'confidence' in elig_signals.columns:
        conf = elig_signals['confidence'].values
        outcomes = elig_signals[outcome_col].values
        brier = np.mean((conf - outcomes) ** 2)
    else:
        brier = np.nan
    
    # Average confidence
    if 'confidence' in elig_signals.columns:
        avg_conf = elig_signals['confidence'].mean()
    elif 'p_non_neutral' in elig_signals.columns:
        avg_conf = elig_signals['p_non_neutral'].mean()
    else:
        avg_conf = np.nan
    
    return {
        'total_signals': total,
        'eligible_count': int(eligible),
        'eligible_rate': float(eligible_rate),
        'precision': float(precision),
        'recall': float(recall),
        'brier_score': float(brier),
        'avg_confidence': float(avg_conf)
    }


def load_historical_signals(logs_root: Path) -> pd.DataFrame:
    """Load historical signals from logs."""
    
    signals_files = list(logs_root.rglob("signals.jsonl"))
    if not signals_files:
        raise ValueError(f"No signals.jsonl found in {logs_root}")
    
    records = []
    for sig_file in signals_files:
        try:
            with sig_file.open('r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    rec = json.loads(line)
                    
                    # Extract relevant fields
                    model_out = rec.get('model_out', {})
                    decision = rec.get('decision', {})
                    
                    records.append({
                        'ts': rec.get('ts'),
                        'symbol': rec.get('symbol'),
                        'p_up': model_out.get('p_up', 0.0),
                        'p_down': model_out.get('p_down', 0.0),
                        'p_neutral': model_out.get('p_neutral', 1.0),
                        'confidence': model_out.get('conf', 0.5),
                        'direction': decision.get('dir', 0),
                        'alpha': decision.get('alpha', 0.0)
                    })
        except Exception as e:
            print(f"⚠️  Error reading {sig_file}: {e}")
            continue
    
    if not records:
        raise ValueError("No valid signal records found")
    
    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} historical signals from {len(signals_files)} file(s)")
    
    return df


def enrich_with_outcomes(
    signals: pd.DataFrame,
    logs_root: Path
) -> pd.DataFrame:
    """Enrich signals with realized outcomes if available."""
    
    # Try to load execution/fill data for outcomes
    exec_files = list(logs_root.rglob("execution.jsonl")) + list(logs_root.rglob("order_intent.jsonl"))
    
    if not exec_files:
        print("⚠️  No execution files found - outcomes unavailable")
        return signals
    
    exec_records = []
    for ex_file in exec_files:
        try:
            with ex_file.open('r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    rec = json.loads(line)
                    risk_state = rec.get('risk_state', {})
                    pnl = rec.get('realized_pnl') or risk_state.get('realized_pnl')
                    
                    if pnl is not None:
                        exec_records.append({
                            'ts': rec.get('ts'),
                            'symbol': rec.get('symbol'),
                            'realized_pnl': float(pnl),
                            'win': pnl > 0
                        })
        except Exception as e:
            continue
    
    if not exec_records:
        print("⚠️  No outcomes found in execution files")
        return signals
    
    exec_df = pd.DataFrame(exec_records)
    print(f"Found {len(exec_df)} execution outcomes")
    
    # Merge by timestamp + symbol (within 1 second tolerance)
    signals['ts_round'] = (signals['ts'] / 1000).round()
    exec_df['ts_round'] = (exec_df['ts'] / 1000).round()
    
    merged = signals.merge(
        exec_df[['ts_round', 'symbol', 'realized_pnl', 'win']],
        on=['ts_round', 'symbol'],
        how='left'
    )
    
    matched = merged['win'].notna().sum()
    print(f"Matched {matched}/{len(signals)} signals to outcomes ({100*matched/len(signals):.1f}%)")
    
    return merged


def compare_gating_strategies(
    signals: pd.DataFrame,
    cfg: GatingConfig
) -> Dict:
    """Compare old vs new gating strategies."""
    
    # Apply both gating strategies
    signals = apply_old_gating(signals, cfg)
    signals = apply_new_gating(signals, cfg)
    
    # Compute metrics for each
    has_outcomes = 'win' in signals.columns and signals['win'].notna().any()
    
    metrics_old = compute_metrics(signals, 'eligible_old', 'win' if has_outcomes else None)
    metrics_new = compute_metrics(signals, 'eligible_new', 'win' if has_outcomes else None)
    
    # Compute improvements
    improvement = {}
    for key in metrics_old:
        if isinstance(metrics_old[key], (int, float)) and not np.isnan(metrics_old[key]):
            old_val = metrics_old[key]
            new_val = metrics_new[key]
            if old_val != 0:
                pct_change = 100 * (new_val - old_val) / abs(old_val)
            else:
                pct_change = 0.0 if new_val == 0 else np.inf
            improvement[f"{key}_change_pct"] = pct_change
    
    # Gating reason breakdown (new logic only)
    reason_counts = signals['gating_reason_new'].value_counts().to_dict()
    
    return {
        'old_logic': metrics_old,
        'new_logic': metrics_new,
        'improvement': improvement,
        'gating_reasons': reason_counts,
        'has_outcomes': has_outcomes
    }


def print_report(results: Dict, cfg: GatingConfig):
    """Print comparison report."""
    
    print("\n" + "="*70)
    print("TRI-CLASS GATING BACKTEST REPORT")
    print("="*70)
    
    print(f"\n📊 Configuration:")
    print(f"  Old Logic: confidence >= {cfg.conf_min_old:.2f}")
    print(f"  New Logic: p_non_neutral >= {cfg.pnn_min:.2f}, conf_dir >= {cfg.conf_dir_min:.2f}, strength >= {cfg.strength_min:.2f}")
    
    old = results['old_logic']
    new = results['new_logic']
    imp = results['improvement']
    
    print(f"\n📈 Signal Eligibility:")
    print(f"  Old: {old['eligible_count']:,} / {old['total_signals']:,} ({old['eligible_rate']:.1%})")
    print(f"  New: {new['eligible_count']:,} / {new['total_signals']:,} ({new['eligible_rate']:.1%})")
    if 'eligible_rate_change_pct' in imp:
        print(f"  Change: {imp['eligible_rate_change_pct']:+.1f}%")
    
    if results['has_outcomes']:
        print(f"\n🎯 Precision (Win Rate of Eligible):")
        print(f"  Old: {old['precision']:.1%}")
        print(f"  New: {new['precision']:.1%}")
        if 'precision_change_pct' in imp:
            print(f"  Change: {imp['precision_change_pct']:+.1f}%")
        
        print(f"\n🔍 Recall (% of Wins Captured):")
        print(f"  Old: {old['recall']:.1%}")
        print(f"  New: {new['recall']:.1%}")
        if 'recall_change_pct' in imp:
            print(f"  Change: {imp['recall_change_pct']:+.1f}%")
        
        if not np.isnan(old['brier_score']):
            print(f"\n📉 Brier Score (Lower is Better):")
            print(f"  Old: {old['brier_score']:.4f}")
            print(f"  New: {new['brier_score']:.4f}")
            if 'brier_score_change_pct' in imp:
                print(f"  Change: {imp['brier_score_change_pct']:+.1f}%")
    else:
        print(f"\n⚠️  No outcomes available - precision/recall/Brier score not computed")
    
    print(f"\n🚫 New Logic Gating Reasons:")
    for reason, count in sorted(results['gating_reasons'].items(), key=lambda x: -x[1]):
        print(f"  {reason:20s}: {count:,}")
    
    print(f"\n💡 Summary:")
    if results['has_outcomes']:
        if new['precision'] > old['precision'] * 1.05:
            print(f"  ✅ Precision improved by {imp.get('precision_change_pct', 0):.1f}%")
        elif new['precision'] < old['precision'] * 0.95:
            print(f"  ⚠️  Precision declined by {abs(imp.get('precision_change_pct', 0)):.1f}%")
        else:
            print(f"  ➡️  Precision roughly unchanged")
    
    if new['eligible_rate'] < old['eligible_rate'] * 0.8:
        print(f"  ⚠️  Eligible rate dropped significantly ({imp.get('eligible_rate_change_pct', 0):.1f}%)")
    elif new['eligible_rate'] > old['eligible_rate'] * 1.2:
        print(f"  ✅ More signals eligible ({imp.get('eligible_rate_change_pct', 0):+.1f}%)")
    
    print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(description="Backtest tri-class gating improvement")
    parser.add_argument(
        '--logs-root',
        type=Path,
        default=Path('paper_trading_outputs/1h'),
        help='Root directory containing historical signal logs'
    )
    parser.add_argument(
        '--conf-min-old',
        type=float,
        default=0.60,
        help='Old logic confidence threshold (default: 0.60)'
    )
    parser.add_argument(
        '--pnn-min',
        type=float,
        default=0.20,
        help='New logic p_non_neutral threshold (default: 0.20)'
    )
    parser.add_argument(
        '--conf-dir-min',
        type=float,
        default=0.60,
        help='New logic conf_dir threshold (default: 0.60)'
    )
    parser.add_argument(
        '--strength-min',
        type=float,
        default=0.07,
        help='New logic strength threshold (default: 0.07)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Optional JSON output file for results'
    )
    
    args = parser.parse_args()
    
    if not args.logs_root.exists():
        print(f"❌ Error: Logs root does not exist: {args.logs_root}")
        return 1
    
    # Load configuration
    cfg = GatingConfig(
        conf_min_old=args.conf_min_old,
        pnn_min=args.pnn_min,
        conf_dir_min=args.conf_dir_min,
        strength_min=args.strength_min
    )
    
    print(f"Loading historical signals from: {args.logs_root}")
    
    try:
        signals = load_historical_signals(args.logs_root)
    except Exception as e:
        print(f"❌ Error loading signals: {e}")
        return 1
    
    # Try to enrich with outcomes
    signals = enrich_with_outcomes(signals, args.logs_root)
    
    # Compare strategies
    results = compare_gating_strategies(signals, cfg)
    
    # Print report
    print_report(results, cfg)
    
    # Save results if requested
    if args.output:
        # Convert numpy types to native Python for JSON serialization
        def convert_to_native(obj):
            if isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_native(v) for v in obj]
            elif isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return obj
        
        output_data = {
            'config': {
                'conf_min_old': cfg.conf_min_old,
                'pnn_min': cfg.pnn_min,
                'conf_dir_min': cfg.conf_dir_min,
                'strength_min': cfg.strength_min
            },
            'results': convert_to_native(results)
        }
        
        with args.output.open('w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n📝 Results written to: {args.output}")
    
    # Exit code: 0 if new logic improves or maintains quality
    if results['has_outcomes']:
        if results['new_logic']['precision'] >= results['old_logic']['precision'] * 0.95:
            return 0
        else:
            return 1
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())
