#!/usr/bin/env python3
"""
Cost Guard Replay Validator - Ensemble 1.1 Day 5 Task 3

This script replays cost guard logic on historical signals to validate:
1. Impact estimates were calculated correctly
2. High-impact trades were properly vetoed
3. No allowed trade caused >10% drawdown (proxy: >200 bps impact)
4. Cost guard veto count > 0 (proving it's active)

KPIs:
- No allowed trade with estimated impact >200 bps (10% drawdown proxy)
- Cost guard veto count > 0 (proves guard is active)
- Veto rate: % of signals blocked by cost guard

Author: Ensemble 1.1 Validation Team
Date: 2025
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime


class CostGuardReplayer:
    """Replays cost guard logic on historical signals."""
    
    def __init__(
        self,
        max_impact_bps_hard: float = 200.0,
        impact_k: float = 0.001,
        base_notional: float = 1000.0,
    ):
        """
        Initialize replayer with cost guard parameters.
        
        Args:
            max_impact_bps_hard: Hard threshold for impact veto (bps)
            impact_k: Impact coefficient (k)
            base_notional: Base notional for position sizing ($)
        """
        self.max_impact_bps_hard = max_impact_bps_hard
        self.impact_k = impact_k
        self.base_notional = base_notional
    
    def estimate_impact_bps(
        self,
        dir_val: int,
        alpha: float,
        last_price: float,
        current_pos: float = 0.0,
    ) -> float:
        """
        Estimate impact in basis points using the hard veto formula.
        
        Args:
            dir_val: Direction (-1, 0, 1)
            alpha: Position size multiplier
            last_price: Current price
            current_pos: Current position fraction
        
        Returns:
            Estimated impact in basis points
        """
        if dir_val == 0 or last_price <= 0:
            return 0.0
        
        # Target position calculation (from risk_and_exec.py logic)
        target = dir_val * abs(alpha)
        pos_delta_frac = abs(target - current_pos)
        
        # Estimate notional and quantity
        est_notional = pos_delta_frac * max(1e-6, self.base_notional)
        est_qty = est_notional / max(1e-6, last_price)
        
        # Hard veto formula: impact_est = impact_k * (est_qty ** 2) * last_price
        impact_est = self.impact_k * (est_qty ** 2) * last_price
        
        # Convert to basis points
        impact_bps_est = (impact_est / est_notional) * 10000.0 if est_notional > 0 else 0.0
        
        return impact_bps_est
    
    def replay_signal(
        self,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Replay cost guard logic on a single signal.
        
        Args:
            signal: Signal record from JSONL
        
        Returns:
            Dict with replay results:
                - was_executed: Was trade allowed
                - was_vetoed_cost: Was vetoed by cost guard
                - estimated_impact_bps: Estimated impact
                - would_veto: Would our replay logic veto
                - veto_reason: Original veto reason (if any)
        """
        decision = signal.get('decision', {})
        details = decision.get('details', {})
        veto = signal.get('veto_reasons', {})
        
        dir_val = decision.get('dir', 0)
        alpha = decision.get('alpha', 0.0)
        
        # Extract price (try multiple fields)
        last_price = signal.get('last_price')
        if last_price is None:
            last_price = signal.get('price', signal.get('close', 0.0))
        
        # Check if originally vetoed by cost guard
        veto_mode = veto.get('mode', '') or details.get('mode', '')
        was_vetoed_cost = 'impact' in veto_mode.lower() if veto_mode else False
        
        # Check if trade was executed (dir != 0 and not vetoed)
        was_executed = (dir_val != 0) and not veto
        
        # Estimate impact using our formula
        estimated_impact_bps = self.estimate_impact_bps(
            dir_val=dir_val,
            alpha=alpha,
            last_price=float(last_price) if last_price else 0.0,
        )
        
        # Would our replay logic veto?
        would_veto = estimated_impact_bps > self.max_impact_bps_hard
        
        return {
            'was_executed': was_executed,
            'was_vetoed_cost': was_vetoed_cost,
            'estimated_impact_bps': estimated_impact_bps,
            'would_veto': would_veto,
            'veto_reason': veto_mode,
            'dir': dir_val,
            'alpha': alpha,
            'last_price': float(last_price) if last_price else 0.0,
            'timestamp': signal.get('timestamp', ''),
        }


def load_signals(logs_root: Path) -> List[Dict[str, Any]]:
    """Load all signals from log directory."""
    signals = []
    
    signals_files = sorted(logs_root.rglob("signals.jsonl"))
    
    if not signals_files:
        print(f"⚠️  No signals.jsonl files found in {logs_root}")
        return signals
    
    print(f"📂 Found {len(signals_files)} signals file(s)")
    
    for signals_file in signals_files:
        try:
            with signals_file.open('r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        signals.append(json.loads(line))
        except Exception as e:
            print(f"❌ Error reading {signals_file}: {e}")
    
    return signals


def analyze_replay_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze replay results and generate statistics."""
    total_signals = len(results)
    
    # Count categories
    executed = [r for r in results if r['was_executed']]
    vetoed_cost = [r for r in results if r['was_vetoed_cost']]
    high_impact_executed = [r for r in executed if r['estimated_impact_bps'] > 200.0]
    would_veto = [r for r in results if r['would_veto']]
    
    # Calculate statistics
    veto_count = len(vetoed_cost)
    veto_rate = (veto_count / total_signals * 100) if total_signals > 0 else 0.0
    
    executed_count = len(executed)
    high_impact_executed_count = len(high_impact_executed)
    
    # KPI checks
    kpi_no_high_impact = high_impact_executed_count == 0
    kpi_guard_active = veto_count > 0
    
    # Find top impact trades
    all_results_sorted = sorted(results, key=lambda r: r['estimated_impact_bps'], reverse=True)
    top_impact = all_results_sorted[:5]
    
    return {
        'total_signals': total_signals,
        'executed_count': executed_count,
        'vetoed_cost_count': veto_count,
        'veto_rate_pct': veto_rate,
        'high_impact_executed_count': high_impact_executed_count,
        'kpi_no_high_impact': kpi_no_high_impact,
        'kpi_guard_active': kpi_guard_active,
        'top_impact_trades': top_impact,
    }


def print_summary(analysis: Dict[str, Any]):
    """Print formatted summary of replay results."""
    print("\n" + "=" * 80)
    print("COST GUARD REPLAY RESULTS")
    print("=" * 80)
    
    print(f"\nTotal Signals:              {analysis['total_signals']}")
    print(f"Executed Trades:            {analysis['executed_count']}")
    print(f"Cost Guard Vetoes:          {analysis['vetoed_cost_count']} ({analysis['veto_rate_pct']:.1f}%)")
    print(f"High Impact Executed:       {analysis['high_impact_executed_count']}")
    
    print("\n" + "-" * 80)
    print("KPI CHECKS")
    print("-" * 80)
    
    status_1 = "✅ PASS" if analysis['kpi_no_high_impact'] else "❌ FAIL"
    print(f"No High Impact (>200 bps):  {status_1}")
    if not analysis['kpi_no_high_impact']:
        print(f"   {analysis['high_impact_executed_count']} trades executed with >200 bps impact!")
    
    status_2 = "✅ PASS" if analysis['kpi_guard_active'] else "❌ FAIL"
    print(f"Cost Guard Active:          {status_2}")
    if not analysis['kpi_guard_active']:
        print(f"   Cost guard never triggered (veto count = 0)")
    
    # Show top impact trades
    print("\n" + "-" * 80)
    print("TOP 5 HIGHEST IMPACT TRADES")
    print("-" * 80)
    print(f"{'Rank':<6} {'Impact (bps)':<15} {'Status':<20} {'Dir':<5} {'Alpha':<10}")
    print("-" * 80)
    
    for i, trade in enumerate(analysis['top_impact_trades'], 1):
        status = "EXECUTED" if trade['was_executed'] else "VETOED"
        if trade['was_vetoed_cost']:
            status = "VETOED (cost)"
        
        print(
            f"{i:<6} "
            f"{trade['estimated_impact_bps']:<15.2f} "
            f"{status:<20} "
            f"{trade['dir']:<5} "
            f"{trade['alpha']:<10.4f}"
        )
    
    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    
    if analysis['kpi_no_high_impact'] and analysis['kpi_guard_active']:
        print("✅ Cost guard is working correctly:")
        print("   - No high-impact trades were executed")
        print("   - Cost guard actively vetoed risky trades")
    elif not analysis['kpi_guard_active']:
        print("⚠️  Cost guard appears inactive:")
        print("   - No vetoes recorded")
        print("   - May indicate misconfiguration or all trades below threshold")
    else:
        print("❌ Cost guard failed to prevent high-impact trades:")
        print(f"   - {analysis['high_impact_executed_count']} trades with >200 bps impact executed")
        print("   - Risk of >10% drawdown present")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Replay cost guard logic on historical signals"
    )
    parser.add_argument(
        '--logs-root',
        type=Path,
        default=Path('paper_trading_outputs'),
        help='Root directory for paper trading logs'
    )
    parser.add_argument(
        '--max-impact-bps-hard',
        type=float,
        default=200.0,
        help='Hard threshold for impact veto (bps)'
    )
    parser.add_argument(
        '--impact-k',
        type=float,
        default=0.001,
        help='Impact coefficient (k)'
    )
    parser.add_argument(
        '--base-notional',
        type=float,
        default=1000.0,
        help='Base notional for position sizing ($)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('cost_guard_replay_report.json'),
        help='Output file for JSON report'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("COST GUARD REPLAY VALIDATOR - Ensemble 1.1 Day 5 Task 3")
    print("=" * 80)
    print(f"\nAnalyzing logs from: {args.logs_root}")
    print(f"\nParameters:")
    print(f"  Max Impact (hard): {args.max_impact_bps_hard} bps")
    print(f"  Impact K:          {args.impact_k}")
    print(f"  Base Notional:     ${args.base_notional}")
    
    # Load signals
    print("\n" + "-" * 80)
    print("Loading signals...")
    print("-" * 80)
    signals = load_signals(args.logs_root)
    
    if not signals:
        print("\n❌ No signals found. Cannot perform replay validation.")
        return 1
    
    print(f"✅ Loaded {len(signals)} signals")
    
    # Initialize replayer
    replayer = CostGuardReplayer(
        max_impact_bps_hard=args.max_impact_bps_hard,
        impact_k=args.impact_k,
        base_notional=args.base_notional,
    )
    
    # Replay each signal
    print("\n" + "-" * 80)
    print("Replaying cost guard logic...")
    print("-" * 80)
    
    results = []
    for signal in signals:
        result = replayer.replay_signal(signal)
        results.append(result)
    
    print(f"✅ Replayed {len(results)} signals")
    
    # Analyze results
    analysis = analyze_replay_results(results)
    
    # Print summary
    print_summary(analysis)
    
    # Save JSON report
    report = {
        'timestamp': datetime.now().isoformat(),
        'parameters': {
            'max_impact_bps_hard': args.max_impact_bps_hard,
            'impact_k': args.impact_k,
            'base_notional': args.base_notional,
        },
        'summary': {
            'total_signals': analysis['total_signals'],
            'executed_count': analysis['executed_count'],
            'vetoed_cost_count': analysis['vetoed_cost_count'],
            'veto_rate_pct': analysis['veto_rate_pct'],
            'high_impact_executed_count': analysis['high_impact_executed_count'],
        },
        'kpi_checks': {
            'no_high_impact_trades': {
                'threshold_bps': 200.0,
                'passed': analysis['kpi_no_high_impact'],
                'violations': analysis['high_impact_executed_count'],
            },
            'cost_guard_active': {
                'passed': analysis['kpi_guard_active'],
                'veto_count': analysis['vetoed_cost_count'],
            },
        },
        'top_impact_trades': [
            {
                'rank': i + 1,
                'estimated_impact_bps': t['estimated_impact_bps'],
                'was_executed': t['was_executed'],
                'was_vetoed_cost': t['was_vetoed_cost'],
                'dir': t['dir'],
                'alpha': t['alpha'],
                'timestamp': t['timestamp'],
            }
            for i, t in enumerate(analysis['top_impact_trades'])
        ],
    }
    
    with args.output.open('w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Results saved to: {args.output}\n")
    
    # Return exit code based on KPI checks
    if analysis['kpi_no_high_impact'] and analysis['kpi_guard_active']:
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
