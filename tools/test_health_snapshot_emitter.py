"""Ad-hoc test for HealthSnapshotEmitter outputs."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytz

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from live_demo.emitters import HealthSnapshotEmitter

REQUIRED_FIELDS = [
    "ts_ist",
    "equity_value",
    "drawdown_current",
    "daily_pnl",
    "rolling_sharpe",
    "trade_count",
    "win_rate",
    "turnover",
    "error_counts",
    "risk_breaches",
]

IST = pytz.timezone("Asia/Kolkata")


def run_test() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base_logs = Path(tmpdir) / "logs"
        emitter = HealthSnapshotEmitter(base_logs_dir=str(base_logs))

        snapshot = {
            "equity_value": 1_000_000.0,
            "drawdown_current": -0.02,
            "daily_pnl": 1500.0,
            "rolling_sharpe": 1.5,
            "trade_count": 42,
            "win_rate": 0.55,
            "turnover": 120.0,
            "error_counts": 0,
            "risk_breaches": 0,
        }

        now = datetime(2025, 12, 12, 10, 0, tzinfo=IST)
        emitter.maybe_emit(snapshot, now=now)

        logs = {
            "1h": base_logs / "1h" / "health_snapshot" / "snapshot.jsonl",
            "24h": base_logs / "24h" / "health_snapshot" / "snapshot.jsonl",
        }

        for label, path in logs.items():
            if not path.exists():
                print(f"MISSING OUTPUT: {path}")
                continue
            print(f"{label} snapshot path: {path}")
            last_line = Path(path).read_text(encoding="utf-8").strip().splitlines()[-1]
            payload = json.loads(last_line)
            print(f"{label} JSON keys: {sorted(payload.keys())}")

            missing = [field for field in REQUIRED_FIELDS if field not in payload]
            if missing:
                print(
                    f"{label}: missing fields {missing}. "
                    "Fix: ensure HealthSnapshot provides these values before maybe_emit()."
                )
            else:
                print(f"{label}: all required fields present.")


if __name__ == "__main__":
    run_test()
