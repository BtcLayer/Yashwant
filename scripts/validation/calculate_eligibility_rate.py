#!/usr/bin/env python3
"""
Calculate Eligibility Rate for Tri-Class Gating

Counts how many bars per day pass tri-class gating thresholds.

Tri-class gating checks:
1. p_non_neutral >= PNN_MIN (e.g., 0.20)
2. conf_dir >= CONF_DIR_MIN (e.g., 0.60)
3. strength >= STRENGTH_MIN (e.g., 0.07)

Where:
- p_non_neutral = 1 - p_neutral
- conf_dir = max(p_up, p_down) / (p_up + p_down) if p_up + p_down > 0 else 0
- strength = abs(p_up - p_down)

KPI: 5-50 eligible bars per day
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


class TriClassGating:
    """Tri-class gating logic (same as live_demo/decision.py)"""
    
    def __init__(self, pnn_min: float = 0.20, conf_dir_min: float = 0.60, strength_min: float = 0.07):
        self.pnn_min = pnn_min
        self.conf_dir_min = conf_dir_min
        self.strength_min = strength_min
        self.eps = 1e-12
    
    def is_eligible(self, p_up: float, p_down: float, p_neutral: float) -> Dict:
        """Check if signal passes tri-class gating."""
        # Calculate metrics
        p_non_neutral = 1.0 - p_neutral
        
        # Directional confidence
        denom = p_up + p_down
        if denom > self.eps:
            conf_dir = max(p_up, p_down) / denom
        else:
            conf_dir = 0.0
        
        # Signal strength
        strength = abs(p_up - p_down)
        
        # Check all thresholds
        pass_pnn = p_non_neutral >= self.pnn_min
        pass_conf_dir = conf_dir >= self.conf_dir_min
        pass_strength = strength >= self.strength_min
        
        eligible = pass_pnn and pass_conf_dir and pass_strength
        
        return {
            'eligible': eligible,
            'p_non_neutral': p_non_neutral,
            'conf_dir': conf_dir,
            'strength': strength,
            'pass_pnn': pass_pnn,
            'pass_conf_dir': pass_conf_dir,
            'pass_strength': pass_strength
        }


def load_signals(logs_root: Path) -> List[Dict]:
    """Load signals from logs."""
    signals = []
    
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
                                'p_neutral': p_neutral
                            })
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue
        except Exception as e:
            print(f"⚠️  Error reading {signal_file}: {e}")
            continue
    
    print(f"✅ Loaded {len(signals)} signals")
    return signals


def calculate_eligibility_rate(signals: List[Dict], gating: TriClassGating) -> Dict:
    """Calculate daily eligibility rates."""
    if not signals:
        return {
            'error': 'No signals',
            'daily_rates': []
        }
    
    # Group by date
    daily_data = defaultdict(lambda: {'total': 0, 'eligible': 0})
    
    for signal in signals:
        # Convert timestamp to date
        ts = signal['ts']
        dt = datetime.fromtimestamp(ts / 1000)
        date_str = dt.strftime('%Y-%m-%d')
        
        # Check eligibility
        result = gating.is_eligible(signal['p_up'], signal['p_down'], signal['p_neutral'])
        
        daily_data[date_str]['total'] += 1
        if result['eligible']:
            daily_data[date_str]['eligible'] += 1
    
    # Convert to list
    daily_rates = []
    for date_str in sorted(daily_data.keys()):
        data = daily_data[date_str]
        rate = data['eligible'] / data['total'] if data['total'] > 0 else 0.0
        daily_rates.append({
            'date': date_str,
            'total_bars': data['total'],
            'eligible_bars': data['eligible'],
            'eligibility_rate': rate
        })
    
    # Calculate overall stats
    total_bars = sum(d['total_bars'] for d in daily_rates)
    total_eligible = sum(d['eligible_bars'] for d in daily_rates)
    overall_rate = total_eligible / total_bars if total_bars > 0 else 0.0
    
    avg_daily_eligible = total_eligible / len(daily_rates) if daily_rates else 0.0
    
    return {
        'daily_rates': daily_rates,
        'total_bars': total_bars,
        'total_eligible': total_eligible,
        'overall_eligibility_rate': overall_rate,
        'avg_daily_eligible_bars': avg_daily_eligible,
        'num_days': len(daily_rates)
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate eligibility rate for tri-class gating")
    parser.add_argument('--logs-root', type=str, default='paper_trading_outputs',
                       help='Root directory for logs')
    parser.add_argument('--output', type=str, default='eligibility_rate_report.json',
                       help='Output JSON file')
    parser.add_argument('--pnn-min', type=float, default=0.20,
                       help='Minimum non-neutral probability')
    parser.add_argument('--conf-dir-min', type=float, default=0.60,
                       help='Minimum directional confidence')
    parser.add_argument('--strength-min', type=float, default=0.07,
                       help='Minimum signal strength')
    
    args = parser.parse_args()
    
    logs_root = Path(args.logs_root)
    
    if not logs_root.exists():
        print(f"❌ Logs directory not found: {logs_root}")
        return 1
    
    print("=" * 80)
    print("ELIGIBILITY RATE CALCULATION - Tri-Class Gating")
    print("=" * 80)
    print()
    print(f"Analyzing logs from: {logs_root}")
    print()
    print(f"Thresholds:")
    print(f"  PNN_MIN:      {args.pnn_min:.2f}")
    print(f"  CONF_DIR_MIN: {args.conf_dir_min:.2f}")
    print(f"  STRENGTH_MIN: {args.strength_min:.2f}")
    print()
    
    # Load signals
    signals = load_signals(logs_root)
    
    if not signals:
        print(f"\n❌ No signals found")
        return 1
    
    print()
    
    # Create gating instance
    gating = TriClassGating(
        pnn_min=args.pnn_min,
        conf_dir_min=args.conf_dir_min,
        strength_min=args.strength_min
    )
    
    # Calculate eligibility
    print("Calculating eligibility rates...")
    result = calculate_eligibility_rate(signals, gating)
    
    # Print results
    print()
    print("=" * 80)
    print("ELIGIBILITY RATE RESULTS")
    print("=" * 80)
    print()
    print(f"Total Bars:              {result['total_bars']}")
    print(f"Eligible Bars:           {result['total_eligible']}")
    print(f"Overall Eligibility:     {result['overall_eligibility_rate']*100:.1f}%")
    print()
    print(f"Number of Days:          {result['num_days']}")
    print(f"Avg Eligible Bars/Day:   {result['avg_daily_eligible_bars']:.1f}")
    print()
    
    print("DAILY BREAKDOWN:")
    print("-" * 80)
    print(f"{'Date':<12} {'Total':<8} {'Eligible':<10} {'Rate':<10}")
    print("-" * 80)
    
    for day in result['daily_rates']:
        print(f"{day['date']:<12} {day['total_bars']:<8} {day['eligible_bars']:<10} {day['eligibility_rate']*100:>6.1f}%")
    
    print()
    
    # KPI Check
    print("=" * 80)
    print("KPI CHECK")
    print("=" * 80)
    print()
    
    avg_eligible = result['avg_daily_eligible_bars']
    target_min = 5
    target_max = 50
    
    print(f"Target Range: {target_min}-{target_max} eligible bars/day")
    print(f"Actual:       {avg_eligible:.1f} eligible bars/day")
    print()
    
    if target_min <= avg_eligible <= target_max:
        print("✅ PASS: Eligibility rate within target range")
        status = "PASS"
    elif avg_eligible < target_min:
        print(f"❌ FAIL: Too few eligible bars (< {target_min}/day)")
        print("   Action: Consider loosening thresholds")
        status = "FAIL_LOW"
    else:
        print(f"⚠️  WARNING: Too many eligible bars (> {target_max}/day)")
        print("   Action: Consider tightening thresholds")
        status = "WARN_HIGH"
    
    print()
    
    # Save to JSON
    output_data = {
        **result,
        'kpi_check': {
            'target_min': target_min,
            'target_max': target_max,
            'actual': avg_eligible,
            'status': status
        },
        'thresholds': {
            'pnn_min': args.pnn_min,
            'conf_dir_min': args.conf_dir_min,
            'strength_min': args.strength_min
        }
    }
    
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Results saved to: {output_path}")
    print()
    
    return 0 if status == "PASS" else 1


if __name__ == '__main__':
    sys.exit(main())
