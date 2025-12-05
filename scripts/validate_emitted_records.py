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
