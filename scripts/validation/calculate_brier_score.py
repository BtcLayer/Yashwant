#!/usr/bin/env python3
"""
Calculate Brier Score for Calibration Quality

Measures how well calibrated the model probabilities are compared to
actual outcomes. Lower Brier score = better calibration.

Brier Score = mean((predicted_probability - actual_outcome)^2)

For tri-class: Brier = mean((p_up - I_up)^2 + (p_neutral - I_neutral)^2 + (p_down - I_down)^2)

KPI: Brier score should improve by >5% with calibration
"""

import argparse
import json
import gzip
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


def load_signals_and_outcomes(logs_root: Path, max_days: int = 7) -> List[Dict]:
    """Load signals and match to P&L outcomes.
    
    Reuses logic from assess_calibration_data.py
    """
    signals = []
    
    # Scan signal files
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
                        
                        # Extract probabilities
                        p_up = rec.get('p_up')
                        p_down = rec.get('p_down')
                        p_neutral = rec.get('p_neutral')
                        
                        # Fallback to nested structure
                        if p_up is None or p_down is None or p_neutral is None:
                            model = rec.get('model', {})
                            p_up = model.get('p_up', 0.0)
                            p_down = model.get('p_down', 0.0)
                            p_neutral = model.get('p_neutral', 1.0)
                        
                        p_up = float(p_up) if p_up is not None else 0.0
                        p_down = float(p_down) if p_down is not None else 0.0
                        p_neutral = float(p_neutral) if p_neutral is not None else 1.0
                        
                        # Normalize
                        total = p_up + p_down + p_neutral
                        if total > 0:
                            p_up /= total
                            p_down /= total
                            p_neutral /= total
                        
                        ts = rec.get('ts')
                        symbol = rec.get('symbol') or rec.get('asset')
                        
                        if ts and symbol:
                            signals.append({
                                'ts': ts,
                                'symbol': symbol,
                                'p_up': p_up,
                                'p_down': p_down,
                                'p_neutral': p_neutral,
                                'bar_id': rec.get('bar_id')
                            })
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue
        except Exception as e:
            print(f"⚠️  Error reading {signal_file}: {e}")
            continue
    
    print(f"Loaded {len(signals)} signals")
    
    # Load P&L records
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
            print(f"⚠️  Error reading {pnl_file}: {e}")
            continue
    
    print(f"Loaded {len(pnl_records)} P&L records")
    
    # Match signals to P&L outcomes
    matched = []
    TOLERANCE_MS = 30000  # ±30 seconds
    
    for signal in signals:
        signal_ts = signal.get('ts')
        signal_symbol = signal.get('symbol')
        signal_bar_id = signal.get('bar_id')
        
        if not signal_symbol:
            continue
        
        # Try bar_id matching first
        if signal_bar_id is not None:
            for pnl in pnl_records:
                pnl_symbol = pnl.get('asset') or pnl.get('symbol')
                pnl_bar_id = pnl.get('bar_id')
                
                if pnl_symbol == signal_symbol and pnl_bar_id == signal_bar_id:
                    pnl_value = pnl.get('pnl_total_usd') or pnl.get('realized_pnl_usd')
                    
                    if pnl_value is not None:
                        # Classify outcome
                        pnl_val = float(pnl_value)
                        if pnl_val > 0:
                            outcome = 'up'
                        elif pnl_val < 0:
                            outcome = 'down'
                        else:
                            outcome = 'neutral'
                        
                        matched.append({
                            **signal,
                            'realized_pnl': pnl_val,
                            'outcome': outcome
                        })
                        break
        
        # Fallback: timestamp matching
        if signal_ts and signal not in [m for m in matched]:
            best_match = None
            min_time_diff = float('inf')
            
            for pnl in pnl_records:
                pnl_symbol = pnl.get('asset') or pnl.get('symbol')
                if pnl_symbol != signal_symbol:
                    continue
                
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
                    pnl_val = float(pnl_value)
                    if pnl_val > 0:
                        outcome = 'up'
                    elif pnl_val < 0:
                        outcome = 'down'
                    else:
                        outcome = 'neutral'
                    
                    matched.append({
                        **signal,
                        'realized_pnl': pnl_val,
                        'outcome': outcome
                    })
    
    print(f"✅ Matched {len(matched)} signals to P&L outcomes ({len(matched)/len(signals)*100:.1f}% match rate)")
    return matched


def calculate_brier_score(data: List[Dict]) -> Dict:
    """Calculate Brier score for tri-class predictions."""
    if not data:
        return {
            'brier_score': None,
            'sample_count': 0,
            'error': 'No data'
        }
    
    df = pd.DataFrame(data)
    
    # Create indicator vectors for actual outcomes
    df['I_up'] = (df['outcome'] == 'up').astype(float)
    df['I_neutral'] = (df['outcome'] == 'neutral').astype(float)
    df['I_down'] = (df['outcome'] == 'down').astype(float)
    
    # Brier score for tri-class
    df['brier_up'] = (df['p_up'] - df['I_up']) ** 2
    df['brier_neutral'] = (df['p_neutral'] - df['I_neutral']) ** 2
    df['brier_down'] = (df['p_down'] - df['I_down']) ** 2
    
    # Total Brier score (average over all classes)
    df['brier_total'] = df['brier_up'] + df['brier_neutral'] + df['brier_down']
    
    brier_score = df['brier_total'].mean()
    
    # Also calculate per-class
    brier_up = df['brier_up'].mean()
    brier_neutral = df['brier_neutral'].mean()
    brier_down = df['brier_down'].mean()
    
    return {
        'brier_score': float(brier_score),
        'brier_up': float(brier_up),
        'brier_neutral': float(brier_neutral),
        'brier_down': float(brier_down),
        'sample_count': len(df),
        'outcome_distribution': {
            'up': int((df['outcome'] == 'up').sum()),
            'neutral': int((df['outcome'] == 'neutral').sum()),
            'down': int((df['outcome'] == 'down').sum())
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate Brier score for calibration quality")
    parser.add_argument('--logs-root', type=str, default='paper_trading_outputs',
                       help='Root directory for logs')
    parser.add_argument('--output', type=str, default='brier_score_report.json',
                       help='Output JSON file')
    parser.add_argument('--max-days', type=int, default=7,
                       help='Maximum days of logs to analyze')
    
    args = parser.parse_args()
    
    logs_root = Path(args.logs_root)
    
    if not logs_root.exists():
        print(f"❌ Logs directory not found: {logs_root}")
        return 1
    
    print("=" * 80)
    print("BRIER SCORE CALCULATION - Calibration Quality")
    print("=" * 80)
    print()
    print(f"Analyzing logs from: {logs_root}")
    print()
    
    # Load data
    data = load_signals_and_outcomes(logs_root, max_days=args.max_days)
    
    if len(data) < 10:
        print(f"\n❌ Insufficient data: Only {len(data)} matched samples (need ≥10)")
        return 1
    
    print()
    
    # Calculate Brier score
    print("Calculating Brier score...")
    result = calculate_brier_score(data)
    
    # Print results
    print()
    print("=" * 80)
    print("BRIER SCORE RESULTS")
    print("=" * 80)
    print()
    print(f"Sample Count:        {result['sample_count']}")
    print()
    print(f"Overall Brier Score: {result['brier_score']:.4f}")
    print()
    print(f"Per-Class Brier Scores:")
    print(f"  Up:      {result['brier_up']:.4f}")
    print(f"  Neutral: {result['brier_neutral']:.4f}")
    print(f"  Down:    {result['brier_down']:.4f}")
    print()
    print(f"Outcome Distribution:")
    print(f"  Up:      {result['outcome_distribution']['up']}")
    print(f"  Neutral: {result['outcome_distribution']['neutral']}")
    print(f"  Down:    {result['outcome_distribution']['down']}")
    print()
    
    # Interpretation
    print("INTERPRETATION:")
    if result['brier_score'] < 0.10:
        print("  ✅ Excellent calibration (Brier < 0.10)")
    elif result['brier_score'] < 0.20:
        print("  ✅ Good calibration (Brier < 0.20)")
    elif result['brier_score'] < 0.30:
        print("  ⚠️  Acceptable calibration (Brier < 0.30)")
    else:
        print("  ❌ Poor calibration (Brier >= 0.30)")
    
    print()
    print(f"📝 Baseline Brier score: {result['brier_score']:.4f}")
    print(f"🎯 Target: <5% improvement with calibration (< {result['brier_score'] * 0.95:.4f})")
    print()
    
    # Save to JSON
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Results saved to: {output_path}")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
