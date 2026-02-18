#!/usr/bin/env python3
"""Validate emitted JSONL records for required telemetry fields."""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class LogSpec:
    name: str
    filenames: Sequence[str]
    required_fields: Sequence[str]


LOG_SPECS: Tuple[LogSpec, ...] = (
    LogSpec(
        name="signals",
        filenames=("signals.jsonl",),
        required_fields=(
            "ts",
            "symbol",
            "features",
            "model_out",
            "decision",
            "cohort",
            "strategy_id",
            "schema_version",
        ),
    ),
    LogSpec(
        name="order_intent",
        filenames=("order_intent.jsonl",),
        required_fields=(
            "ts",
            "symbol",
            "result",
            "run_id",
            "bar_id",
            "strategy_id",
            "schema_version",
        ),
    ),
    LogSpec(
        name="costs",
        filenames=("costs.jsonl",),
        required_fields=(
            "ts",
            "symbol",
            "run_id",
            "bar_id",
            "strategy_id",
            "schema_version",
        ),
    ),
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate emitted JSONL records.")
    parser.add_argument(
        "--logs-root",
        type=Path,
        default=Path("paper_trading_outputs") / "logs",
        help="Root directory containing log subfolders (default: paper_trading_outputs/logs)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail with exit code 1 when any warnings are encountered.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=5,
        help="Maximum number of recent records to inspect per file (default: 5).",
    )
    return parser.parse_args()


def _tail_lines(path: Path, max_records: int) -> Deque[Tuple[int, str]]:
    tail: Deque[Tuple[int, str]] = deque(maxlen=max_records)
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            stripped = line.strip()
            if stripped:
                tail.append((idx, stripped))
    return tail


def _iter_candidate_files(log_root: Path, spec: LogSpec) -> Iterable[Path]:
    for filename in spec.filenames:
        yield from log_root.rglob(filename)


def cross_stream_checks(exec_records: List[Dict], costs_records: List[Dict], cfg: Dict) -> List[Tuple[str, str]]:
    """
    Validate execution→costs mapping and cost sanity.
    
    Args:
        exec_records: List of order_intent records
        costs_records: List of costs records
        cfg: Configuration dict with thresholds
    
    Returns:
        List of (level, message) tuples where level is "ERROR" or "WARN"
    """
    from collections import defaultdict
    
    issues = []
    
    # Build costs lookup by (run_id, bar_id, symbol)
    costs_map_by_runbar = defaultdict(list)
    
    for c in costs_records:
        run_id = c.get("run_id")
        bar_id = c.get("bar_id")
        symbol = c.get("symbol")
        if run_id is not None and bar_id is not None and symbol:
            costs_map_by_runbar[(run_id, bar_id, symbol)].append(c)
    
    # Thresholds
    COST_MAX_FRAC = cfg.get("COST_MAX_FRAC", 0.25)
    IMPACT_BPS_WARN = cfg.get("IMPACT_BPS_WARN", 500)
    IMPACT_BPS_ERROR = cfg.get("IMPACT_BPS_ERROR", 5000)
    
    for e in exec_records:
        # Check if execution was actually filled/placed
        result = e.get("result") or e.get("intent_action")
        executed = False
        if isinstance(result, str) and result.upper() in ("FILLED", "PLACED", "EXECUTED", "BUY", "SELL"):
            executed = True
        
        if not executed:
            continue
        
        # Look up costs by (run_id, bar_id, symbol)
        run_id = e.get("run_id")
        bar_id = e.get("bar_id")
        symbol = e.get("symbol")
        
        found_cost = None
        if run_id and (bar_id is not None) and symbol:
            clist = costs_map_by_runbar.get((run_id, bar_id, symbol), [])
            if clist:
                found_cost = clist[0]
        
        # Check if costs exist
        if not found_cost:
            issues.append(("ERROR", 
                f"Execution at run_id={run_id} bar_id={bar_id} symbol={symbol} has no costs record"))
            continue
        
        # Run cost sanity checks
        costs = found_cost.get("costs", {})
        tn = costs.get("trade_notional") or costs.get("notional_usd")
        cu = costs.get("cost_usd")
        ib = costs.get("impact_bps") or costs.get("impact_bps_est")
        
        try:
            # Check cost vs notional
            if tn is not None and cu is not None and tn > 0:
                if cu > COST_MAX_FRAC * tn:
                    issues.append(("ERROR", 
                        f"cost_usd {cu:.2f} exceeds {COST_MAX_FRAC*100}% of notional {tn:.2f}"))
            
            # Check impact bps
            if ib is not None:
                ibf = float(ib)
                if ibf > IMPACT_BPS_ERROR:
                    issues.append(("ERROR", 
                        f"impact_bps {ibf:.1f} > error threshold {IMPACT_BPS_ERROR}"))
                elif ibf > IMPACT_BPS_WARN:
                    issues.append(("WARN", 
                        f"impact_bps {ibf:.1f} > warning threshold {IMPACT_BPS_WARN}"))
        except Exception as ex:
            issues.append(("WARN", 
                f"Could not evaluate cost sanity: {ex}"))
    
    return issues


def _validate_record(payload: Dict, required_fields: Sequence[str]) -> List[str]:
    problems: List[str] = []
    for field in required_fields:
        if field not in payload:
            problems.append(f"missing field '{field}'")
        elif payload.get(field) in (None, ""):
            problems.append(f"field '{field}' is empty")
    return problems


def validate_logs(log_root: Path, *, strict: bool = False, max_records: int = 5) -> int:
    """Validate logs under log_root; returns number of issues discovered."""

    issues: List[str] = []
    if not log_root.exists():
        issues.append(f"logs root does not exist: {log_root}")
    else:
        for spec in LOG_SPECS:
            matches = list(_iter_candidate_files(log_root, spec))
            if not matches:
                issues.append(f"no files found for '{spec.name}' under {log_root}")
                continue
            for path in matches:
                try:
                    tail = _tail_lines(path, max_records)
                except OSError as exc:
                    issues.append(f"{path}: unable to read file ({exc})")
                    continue
                if not tail:
                    issues.append(f"{path}: contains no JSON lines")
                    continue
                for line_no, raw in tail:
                    try:
                        record = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        issues.append(f"{path}: line {line_no} invalid JSON ({exc})")
                        continue
                    problems = _validate_record(record, spec.required_fields)
                    for problem in problems:
                        issues.append(f"{path}: line {line_no} {problem}")
        
        # NEW: Cross-stream validation (execution→costs mapping and cost sanity)
        exec_records = []
        costs_records = []
        
        # Load all order_intent records
        for order_file in log_root.rglob("order_intent.jsonl"):
            try:
                with order_file.open('r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            exec_records.append(json.loads(line))
            except Exception as e:
                issues.append(f"Error reading {order_file}: {e}")
        
        # Load all costs records
        for costs_file in log_root.rglob("costs.jsonl"):
            try:
                with costs_file.open('r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            costs_records.append(json.loads(line))
            except Exception as e:
                issues.append(f"Error reading {costs_file}: {e}")
        
        # Run cross-stream checks if we have execution records
        if exec_records:
            # Align thresholds with cost guards in risk_and_exec.py
            # max_impact_bps_hard = 200.0 in production, but allow higher in validation
            # since backtests may have outliers
            config = {
                'COST_MAX_FRAC': 0.25,  # Cost should not exceed 25% of notional
                'IMPACT_BPS_WARN': 200,  # Warn at production hard limit
                'IMPACT_BPS_ERROR': 1000  # Error at 10x production limit (catch extreme cases)
            }
            cross_issues = cross_stream_checks(exec_records, costs_records, config)
            
            for level, msg in cross_issues:
                if level == "ERROR":
                    issues.append(msg)
                elif level == "WARN":
                    print(f"[validate_emitted_records] WARNING: {msg}")

    for msg in issues:
        print(f"[validate_emitted_records] WARNING: {msg}")

    if strict and issues:
        raise SystemExit(1)

    if not issues:
        print(f"[validate_emitted_records] OK: validated logs under {log_root}")

    return len(issues)


def main() -> None:
    args = _parse_args()
    validate_logs(args.logs_root, strict=args.strict, max_records=max(1, args.max_records))


if __name__ == "__main__":
    main()
