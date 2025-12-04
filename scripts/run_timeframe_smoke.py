#!/usr/bin/env python
"""Multi-timeframe runtime smoke harness.

This helper is intentionally lightweight: it validates the JSON config for each
runtime timeframe, writes a heartbeat, and emits a sample signal into a
throw-away log tree. It mirrors the CI smoke checks so we get coverage for the
1h/12h/24h variants without needing to spin up the full bots.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]

import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from ops.heartbeat import write_heartbeat
from ops.log_emitter import get_emitter
CONFIG_ROOTS = {
    "1h": REPO_ROOT / "live_demo_1h" / "config.json",
    "12h": REPO_ROOT / "live_demo_12h" / "config.json",
    "24h": REPO_ROOT / "live_demo_24h" / "config.json",
}
INTERVAL_ALIASES = {
    "24h": {"24h", "1d"},
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run timeframe smoke verifications.")
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=["1h", "12h", "24h"],
        help="List of timeframes to validate (default: 1h 12h 24h)",
    )
    parser.add_argument(
        "--logs-root",
        type=str,
        default=None,
        help="Optional directory to place smoke outputs; defaults to a temp dir.",
    )
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep generated log artifacts even when a temp directory is used.",
    )
    return parser.parse_args()


def _load_config(tf: str) -> Dict:
    cfg_path = CONFIG_ROOTS.get(tf)
    if not cfg_path:
        raise SystemExit(f"No config.json mapping for timeframe '{tf}'")
    if not cfg_path.exists():
        raise SystemExit(f"Missing config file for {tf}: {cfg_path}")
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {cfg_path}: {exc}") from exc


def _ensure_interval_matches(tf: str, cfg: Dict):
    data = cfg.get("data", {})
    interval = str(data.get("interval", "")).strip().lower()
    valid = INTERVAL_ALIASES.get(tf, {tf.lower()})
    if interval not in valid:
        raise SystemExit(
            f"Config interval mismatch for {tf}: expected '{tf}', got '{interval or 'missing'}'"
        )


def _prepare_logs_root(base_root: Path, tf: str) -> Path:
    logs_dir = base_root / tf / "logs" / tf
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _write_heartbeat(logs_dir: Path, tf: str, strategy_id: str, schema_version: str) -> Path:
    os.environ["STRATEGY_ID"] = strategy_id
    os.environ["SCHEMA_VERSION"] = schema_version
    hb_path = Path(write_heartbeat(base_dir=str(logs_dir), bot_version=None, last_bar_id=42))
    payload = json.loads(hb_path.read_text(encoding="utf-8"))
    if payload.get("strategy_id") != strategy_id or payload.get("schema_version") != schema_version:
        raise SystemExit(f"Heartbeat metadata mismatch for {tf}")
    return hb_path


def _emit_signal(logs_dir: Path, tf: str, strategy_id: str, schema_version: str) -> Path:
    os.environ["STRATEGY_ID"] = strategy_id
    os.environ["SCHEMA_VERSION"] = schema_version
    emitter = get_emitter(bot_version=tf, base_dir=str(logs_dir))
    emitter.emit_signals(
        ts=1234567890,
        symbol="BTCUSDT",
        features={"close": 100.0},
        model_out={"s_model": 0.1},
        decision={"dir": 1, "alpha": 0.5},
        cohort={"pros": 0.2, "amateurs": -0.1},
    )
    signals_path = logs_dir / "signals" / "signals.jsonl"
    if not signals_path.exists():
        raise SystemExit(f"Signal log missing for {tf}: {signals_path}")
    lines = [ln.strip() for ln in signals_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise SystemExit(f"Signal log empty for {tf}")
    record = json.loads(lines[-1])
    if record.get("strategy_id") != strategy_id or record.get("schema_version") != schema_version:
        raise SystemExit(f"Signal metadata mismatch for {tf}")
    return signals_path


def _run_for_timeframe(tf: str, base_root: Path) -> Dict[str, str]:
    cfg = _load_config(tf)
    _ensure_interval_matches(tf, cfg)
    logs_dir = _prepare_logs_root(base_root, tf)
    strategy_id = f"ci_smoke_{tf}"
    schema_version = f"smoke_{tf}"
    hb_path = _write_heartbeat(logs_dir, tf, strategy_id, schema_version)
    signals_path = _emit_signal(logs_dir, tf, strategy_id, schema_version)
    return {
        "timeframe": tf,
        "heartbeat": str(hb_path),
        "signals": str(signals_path),
    }


def main():
    args = _parse_args()
    timeframes = [tf.strip() for tf in args.timeframes if tf.strip()]
    if not timeframes:
        raise SystemExit("No timeframes provided")

    if args.logs_root:
        base_root = Path(args.logs_root).expanduser().resolve()
        base_root.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        base_root = Path(tempfile.mkdtemp(prefix="timeframe_smoke_"))
        cleanup = not args.keep_artifacts

    results: List[Dict[str, str]] = []
    try:
        for tf in timeframes:
            results.append(_run_for_timeframe(tf, base_root))
    finally:
        if cleanup:
            shutil.rmtree(base_root, ignore_errors=True)

    print("timeframe smoke summary:")
    for row in results:
        print(f" - {row['timeframe']}: heartbeat={row['heartbeat']} signals={row['signals']}")


if __name__ == "__main__":
    main()
