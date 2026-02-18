#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assess availability of historical data for model calibration.

Calibration requires:
1. Historical signals with model predictions (confidence scores)
2. Realized outcomes (P&L, win/loss) for each signal
3. Sufficient sample size (ideally 500+ samples per class)

This script scans available logs and databases to determine if we have enough
labeled data for calibration, or if we need to collect more.

Supports multiple log schemas:
- Simple schema: flat model_out structure (test logs)
- Production schema: nested sanitized.model structure (live logs)
- Handles gzipped files (.jsonl.gz)
- Handles date-partitioned directories
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import codecs
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


@dataclass
class SignalOutcome:
    """A signal with its realized outcome."""
    ts: float
    symbol: str
    direction: int
    confidence: float
    p_non_neutral: Optional[float]
    conf_dir: Optional[float]
    realized_pnl: Optional[float]
    win: Optional[bool]  # True if profitable, False if loss, None if neutral/unknown
    exit_ts: Optional[float]
    run_id: Optional[str] = None
    bar_id: Optional[int] = None


def read_jsonl_file(file_path: Path) -> List[Dict]:
    """Read JSONL file, handling gzip compression."""
    records = []
    
    try:
        if str(file_path).endswith('.gz'):
            with gzip.open(file_path, 'rb') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line.decode('utf-8')))
        else:
            with file_path.open('r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
    except Exception as e:
        print(f"⚠️  Error reading {file_path}: {e}")
    
    return records


def parse_signal_record(rec: Dict) -> Optional[Dict]:
    """Extract relevant signal fields from various schemas."""
    try:
        # Handle production schema (nested sanitized structure)
        if 'sanitized' in rec:
            sanitized = rec['sanitized']
            model = sanitized.get('model', {})
            decision = sanitized.get('decision', {})
            symbol = sanitized.get('symbol')   
            # Get timestamps
            ts = rec.get('ts')
            
            # Extract tri-class probabilities
            p_up = float(model.get('p_up', 0.0))
            p_down = float(model.get('p_down', 0.0))
            p_neutral = float(model.get('p_neutral', 1.0))
            
            # Compute derived metrics
            p_non_neutral = max(0.0, 1.0 - p_neutral)
            p_dir = p_up + p_down
            
            if p_dir > 0:
                conf_dir = max(p_up, p_down) / (p_dir + 1e-12)
            else:
                conf_dir = 0.0
            
            # Confidence as max directional prob given non-neutral
            if p_non_neutral > 0:
                confidence = max(p_up, p_down) / (p_non_neutral + 1e-12)
            else:
                confidence = 0.5
            
            return {
                'ts': ts,
                'symbol': symbol,
                'direction': decision.get('dir', 0),
                'confidence': confidence,
                'p_non_neutral': p_non_neutral,
                'conf_dir': conf_dir,
                'p_up': p_up,
                'p_down': p_down,
                'p_neutral': p_neutral,
                'run_id': None,  # Production signals don't have run_id
                'bar_id': None
            }
        
        # Handle simple schema (test/5m logs)
        else:
            model_out = rec.get('model_out', {})
            decision = rec.get('decision', {})
            
            return {
                'ts': rec.get('ts'),
                'symbol': rec.get('symbol'),
                'direction': decision.get('dir', 0),
                'confidence': model_out.get('conf', 0.0),
                'p_non_neutral': model_out.get('p_non_neutral'),
                'conf_dir': model_out.get('conf_dir'),
                'p_up': model_out.get('p_up', 0.0),
                'p_down': model_out.get('p_down', 0.0),
                'p_neutral': model_out.get('p_neutral', 1.0),
                'run_id': rec.get('run_id'),
                'bar_id': rec.get('bar_id')
            }
    except Exception as e:
        return None


def find_realized_outcome(signal: Dict, pnl_records: List[Dict]) -> Optional[Tuple[float, bool]]:
    """Match signal to a realized outcome using timestamp-based matching.
    
    Production logs structure:
    - Signals: signals.jsonl (has ts, symbol, predictions)
    - P&L: pnl_equity_log.jsonl.gz (has ts_ist, asset, pnl_total_usd)
    
    Matching strategy: Match by bar_id if available, otherwise use timestamp.
    
    Args:
        signal: Signal record with predictions, ts (ms), symbol
        pnl_records: List of P&L equity log records
    
    Returns:
        Tuple of (realized_pnl, is_win) or None if no match found
    """
    signal_ts = signal.get('ts')
    signal_symbol = signal.get('symbol')
    signal_bar_id = signal.get('bar_id')
    
    if not signal_symbol:
        return None
    
    # Try matching by bar_id first (most accurate)
    if signal_bar_id is not None:
        for pnl in pnl_records:
            # P&L uses 'asset' field instead of 'symbol'
            pnl_symbol = pnl.get('asset') or pnl.get('symbol')
            pnl_bar_id = pnl.get('bar_id')
            
            if pnl_symbol == signal_symbol and pnl_bar_id == signal_bar_id:
                # Extract P&L (could be pnl_total_usd or realized_pnl_usd)
                realized_pnl = pnl.get('pnl_total_usd') or pnl.get('realized_pnl_usd')
                
                if realized_pnl is not None:
                    return (float(realized_pnl), float(realized_pnl) > 0)
    
    # Fallback: match by timestamp (P&L logs may use ts_ist instead of ts)
    if signal_ts:
        TOLERANCE_MS = 30000  # ±30 seconds
        matches = []
        
        for pnl in pnl_records:
            pnl_symbol = pnl.get('asset') or pnl.get('symbol')
            if pnl_symbol != signal_symbol:
                continue
            
            # Try multiple timestamp fields
            pnl_ts = pnl.get('ts')
            if pnl_ts is None:
                # Convert ts_ist to milliseconds if it exists
                ts_ist = pnl.get('ts_ist')
                if ts_ist:
                    # Parse ISO timestamp to ms (if needed)
                    try:
                        from datetime import datetime
                        if isinstance(ts_ist, str):
                            dt = datetime.fromisoformat(ts_ist.replace('Z', '+00:00'))
                            pnl_ts = int(dt.timestamp() * 1000)
                        else:
                            pnl_ts = int(ts_ist) if ts_ist else None
                    except:
                        pnl_ts = None
            
            if pnl_ts:
                time_diff = abs(pnl_ts - signal_ts)
                if time_diff <= TOLERANCE_MS:
                    realized_pnl = pnl.get('pnl_total_usd') or pnl.get('realized_pnl_usd')
                    
                    if realized_pnl is not None:
                        matches.append((time_diff, float(realized_pnl)))
        
        # Return closest match by timestamp
        if matches:
            matches.sort()  # Sort by time difference
            _, pnl_value = matches[0]
            return (pnl_value, pnl_value > 0)
    
    return None


def scan_logs_for_signals_and_outcomes(logs_root: Path) -> List[SignalOutcome]:
    """Scan logs directory for signals and their outcomes.
    
    Production log structure:
    - Signals: date=YYYY-MM-DD/asset=SYMBOL/signals.jsonl
    - P&L: date=YYYY-MM-DD/asset=SYMBOL/pnl_equity_log.jsonl.gz (gzipped!)
    """
    
    outcomes: List[SignalOutcome] = []
    
    # Load all signal records
    signal_files = list(logs_root.rglob("signals.jsonl"))
    if not signal_files:
        print(f"⚠️  No signal files found in {logs_root}")
        return outcomes
    
    print(f"Found {len(signal_files)} signal file(s)")
    
    # Load P&L records from production logs (PRIMARY DATA SOURCE)
    # Path pattern: paper_trading_outputs/5m/logs/*/pnl_equity_log/date=*/asset=*/pnl_equity_log.jsonl.gz
    pnl_records = []
    pnl_files = list(logs_root.rglob("pnl_equity_log.jsonl.gz"))
    
    if not pnl_files:
        # Fallback: try alternate patterns
        pnl_files = (
            list(logs_root.rglob("pnl_equity_log/**/pnl_equity_log.jsonl.gz")) +
            list(logs_root.rglob("equity_log.jsonl.gz")) +
            list(logs_root.rglob("equity.jsonl"))
        )
    
    print(f"Found {len(pnl_files)} P&L file(s)")
    
    for pnl_file in pnl_files:
        records = read_jsonl_file(pnl_file)
        pnl_records.extend(records)
    
    print(f"Loaded {len(pnl_records)} P&L records for matching")
    
    # Process signals
    for sig_file in signal_files:
        try:
            with sig_file.open('r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    rec = json.loads(line)
                    signal = parse_signal_record(rec)
                    if not signal:
                        continue
                    
                    # Try to find realized outcome using P&L records
                    outcome_data = find_realized_outcome(signal, pnl_records)
                    
                    outcomes.append(SignalOutcome(
                        ts=signal['ts'],
                        symbol=signal['symbol'],
                        direction=signal['direction'],
                        confidence=signal['confidence'],
                        p_non_neutral=signal.get('p_non_neutral'),
                        conf_dir=signal.get('conf_dir'),
                        realized_pnl=outcome_data[0] if outcome_data else None,
                        win=outcome_data[1] if outcome_data else None,
                        exit_ts=None
                    ))
        except Exception as e:
            print(f"⚠️  Error processing {sig_file}: {e}")
    
    return outcomes


def analyze_calibration_readiness(outcomes: List[SignalOutcome]) -> Dict:
    """Analyze if we have sufficient data for calibration."""
    
    total_signals = len(outcomes)
    signals_with_outcomes = sum(1 for o in outcomes if o.win is not None)
    signals_without_outcomes = total_signals - signals_with_outcomes
    
    # Count by direction
    dir_counts = Counter(o.direction for o in outcomes)
    
    # Count outcomes
    wins = sum(1 for o in outcomes if o.win is True)
    losses = sum(1 for o in outcomes if o.win is False)
    
    # Confidence distribution
    conf_bins = defaultdict(int)
    for o in outcomes:
        if o.confidence is not None:
            bin_key = f"{int(o.confidence * 10) / 10:.1f}"
            conf_bins[bin_key] += 1
    
    # Win rate by confidence quartile
    quartile_stats = {}
    if signals_with_outcomes > 0:
        labeled = [o for o in outcomes if o.win is not None]
        labeled.sort(key=lambda x: x.confidence)
        
        for i, qname in enumerate(['Q1 (0-25%)', 'Q2 (25-50%)', 'Q3 (50-75%)', 'Q4 (75-100%)']):
            start = i * len(labeled) // 4
            end = (i + 1) * len(labeled) // 4
            quartile = labeled[start:end]
            
            if quartile:
                q_wins = sum(1 for o in quartile if o.win)
                q_total = len(quartile)
                q_win_rate = q_wins / q_total if q_total > 0 else 0
                quartile_stats[qname] = {
                    'count': q_total,
                    'wins': q_wins,
                    'win_rate': q_win_rate,
                    'conf_range': f"{min(o.confidence for o in quartile):.3f}-{max(o.confidence for o in quartile):.3f}"
                }
    
    return {
        'total_signals': total_signals,
        'signals_with_outcomes': signals_with_outcomes,
        'signals_without_outcomes': signals_without_outcomes,
        'labeled_percentage': 100 * signals_with_outcomes / total_signals if total_signals > 0 else 0,
        'direction_counts': dict(dir_counts),
        'wins': wins,
        'losses': losses,
        'win_rate': wins / (wins + losses) if (wins + losses) > 0 else 0,
        'confidence_bins': dict(conf_bins),
        'quartile_stats': quartile_stats,
        'calibration_ready': signals_with_outcomes >= 500,  # Minimum threshold
        'recommendation': _generate_recommendation(total_signals, signals_with_outcomes, wins, losses)
    }


def _generate_recommendation(total: int, labeled: int, wins: int, losses: int) -> str:
    """Generate recommendation based on data availability."""
    
    if labeled == 0:
        return ("🔴 BLOCKER: No labeled outcomes found. Check if P&L data is being recorded "
                "in executions/fills. Cannot proceed with calibration.")
    
    if labeled < 100:
        return (f"🔴 INSUFFICIENT: Only {labeled} labeled samples. Need 500+ for reliable calibration. "
                f"Estimate: {int((500 - labeled) / max(1, labeled / 7))} more days of trading needed (assuming ~{labeled} signals/week).")
    
    if labeled < 500:
        return (f"🟡 MARGINAL: {labeled} labeled samples. Calibration possible but may be unstable. "
                f"Recommend collecting {500 - labeled} more samples (~{int((500 - labeled) / max(1, labeled / 7))} more days).")
    
    # Check class balance
    if wins + losses > 0:
        minority_class = min(wins, losses)
        if minority_class < 100:
            return (f"🟡 IMBALANCED: {labeled} samples but minority class has only {minority_class}. "
                    "May need stratified sampling or more data.")
    
    return f"✅ READY: {labeled} labeled samples available. Sufficient for calibration."


def print_report(analysis: Dict):
    """Print calibration readiness report."""
    
    print("\n" + "="*70)
    print("CALIBRATION DATA ASSESSMENT REPORT")
    print("="*70)
    
    print(f"\n[DATA] Data Availability:")
    print(f"  Total signals found:         {analysis['total_signals']:,}")
    print(f"  Signals with outcomes:      {analysis['signals_with_outcomes']:,} ({analysis['labeled_percentage']:.1f}%)")
    print(f"  Signals without outcomes:   {analysis['signals_without_outcomes']:,}")
    
    # Add matching quality diagnostics
    match_rate = analysis['labeled_percentage']
    print(f"\n[MATCH] Signal-PnL Matching Quality:")
    if match_rate >= 80:
        quality = "✅ EXCELLENT"
    elif match_rate >= 50:
        quality = "🟢 GOOD"
    elif match_rate >= 30:
        quality = "🟡 ACCEPTABLE"
    elif match_rate >= 10:
        quality = "🟠 POOR"
    else:
        quality = "🔴 CRITICAL"
    print(f"  Match Rate: {match_rate:.1f}% {quality}")
    
    if match_rate < 80:
        print(f"  ⚠️  Note: {100-match_rate:.1f}% of signals could not be matched to P&L")
        if match_rate < 30:
            print(f"  💡 Common causes:")
            print(f"     - P&L logs missing or incomplete")
            print(f"     - Timestamp misalignment (>±30s drift)")
            print(f"     - Signals from different trading session than P&L")
    
    print(f"\n[OUTCOMES] Outcome Distribution:")
    print(f"  Wins:       {analysis['wins']:,}")
    print(f"  Losses:     {analysis['losses']:,}")
    if analysis['wins'] + analysis['losses'] > 0:
        print(f"  Win Rate:   {analysis['win_rate']:.1%}")
    
    print(f"\n[DIRECTION] Direction Distribution:")
    for direction, count in sorted(analysis['direction_counts'].items()):
        dir_label = {1: 'LONG', -1: 'SHORT', 0: 'NEUTRAL'}.get(direction, f'DIR_{direction}')
        print(f"  {dir_label:8s}: {count:,}")
    
    if analysis['quartile_stats']:
        print(f"\n[QUARTILES] Win Rate by Confidence Quartile:")
        for qname, stats in analysis['quartile_stats'].items():
            print(f"  {qname:15s}: {stats['win_rate']:6.1%} ({stats['wins']}/{stats['count']}) conf={stats['conf_range']}")
    
    print(f"\n[CONFIDENCE] Confidence Distribution (sample):")
    for conf, count in sorted(analysis['confidence_bins'].items())[:10]:
        print(f"  {conf}: {'█' * min(50, count // 2)} {count}")
    
    print(f"\n[STATUS] Calibration Status:")
    print(f"  Ready: {'✅ YES' if analysis['calibration_ready'] else '❌ NO'}")
    print(f"\n{analysis['recommendation']}")
    
    print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(description="Assess calibration data availability")
    parser.add_argument(
        '--logs-root',
        type=Path,
        default=Path('paper_trading_outputs/logs'),
        help='Root directory containing log files'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Optional JSON output file for analysis results'
    )
    
    args = parser.parse_args()
    
    if not args.logs_root.exists():
        print(f"❌ Error: Logs root does not exist: {args.logs_root}")
        print(f"\n💡 Tip: Specify --logs-root to point to your log directory")
        return 1
    
    print(f"Scanning logs in: {args.logs_root}")
    outcomes = scan_logs_for_signals_and_outcomes(args.logs_root)
    
    if not outcomes:
        print("\n❌ No signals found. Cannot assess calibration readiness.")
        print("\n💡 Possible reasons:")
        print("   - No trading activity yet")
        print("   - Logs directory is empty or wrong path")
        print("   - Signal files not in expected format (signals.jsonl)")
        return 1
    
    analysis = analyze_calibration_readiness(outcomes)
    print_report(analysis)
    
    if args.output:
        with args.output.open('w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        print(f"\n📝 Analysis written to: {args.output}")
    
    # Exit code: 0 if ready, 1 if not
    return 0 if analysis['calibration_ready'] else 1


if __name__ == '__main__':
    sys.exit(main())
