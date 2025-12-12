"""Time-bucketed health snapshot emitter."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional

import pytz

IST = pytz.timezone("Asia/Kolkata")

KEY_ORDER = [
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
FLOAT_FIELDS = {
    "equity_value",
    "drawdown_current",
    "daily_pnl",
    "rolling_sharpe",
    "win_rate",
    "turnover",
}
INT_FIELDS = {"trade_count", "error_counts", "risk_breaches"}
PERIOD_KEY_FORMATS = {"1h": "%Y%m%d%H", "24h": "%Y%m%d"}


@dataclass
class HealthSnapshot:
    """Typed payload for periodic health snapshots."""

    equity_value: Optional[float] = None
    drawdown_current: Optional[float] = None
    daily_pnl: Optional[float] = None
    rolling_sharpe: Optional[float] = None
    trade_count: Optional[int] = None
    win_rate: Optional[float] = None
    turnover: Optional[float] = None
    error_counts: Optional[int] = None
    risk_breaches: Optional[int] = None


class HealthSnapshotEmitter:
    """Writes hourly and daily health snapshots to deterministic JSONL files."""

    def __init__(self, base_logs_dir: Optional[str] = None):
        self.logs_root = Path(base_logs_dir or self._default_logs_root())
        self.logs_root.mkdir(parents=True, exist_ok=True)
        self._locks = {period: RLock() for period in PERIOD_KEY_FORMATS}
        self._last_period_keys: Dict[str, Optional[str]] = {
            period: None for period in PERIOD_KEY_FORMATS
        }

    def maybe_emit(
        self,
        snapshot: HealthSnapshot | Dict[str, Any],
        now: Optional[datetime] = None,
    ) -> None:
        """Emit one record per period when a new hour/day boundary is observed."""
        ist_now = (now or datetime.now(IST)).astimezone(IST)
        record = self._normalize_snapshot(snapshot, ist_now)

        for period, fmt in PERIOD_KEY_FORMATS.items():
            period_key = ist_now.strftime(fmt)
            with self._locks[period]:
                if self._last_period_keys[period] == period_key:
                    continue
                self._last_period_keys[period] = period_key
                self._write_record(period, record)

    def _write_record(self, period: str, record: Dict[str, Any]) -> None:
        target_dir = self.logs_root / period / "health_snapshot"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / "snapshot.jsonl"
        line = json.dumps(record, separators=(",", ":")) + "\n"

        with open(file_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()

    def _normalize_snapshot(
        self, snapshot: HealthSnapshot | Dict[str, Any], now: datetime
    ) -> Dict[str, Any]:
        if isinstance(snapshot, HealthSnapshot):
            payload = asdict(snapshot)
        else:
            payload = dict(snapshot)
        ordered = {key: None for key in KEY_ORDER}
        ordered["ts_ist"] = now.isoformat()

        for key in KEY_ORDER:
            if key == "ts_ist":
                continue
            ordered[key] = self._coerce_value(key, payload.get(key))

        return ordered

    def _coerce_value(self, key: str, value: Any) -> Any:
        if value is None:
            return None
        if key in FLOAT_FIELDS:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        if key in INT_FIELDS:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return value

    def _default_logs_root(self) -> str:
        here = Path(__file__).resolve()
        repo_root = here.parents[1]
        repo_paper = (repo_root / "paper_trading_outputs").resolve()
        env_root = os.environ.get("PAPER_TRADING_ROOT")
        if env_root:
            try:
                env_path = Path(env_root).resolve()
                if str(env_path).startswith(str(repo_paper)):
                    base = env_path
                else:
                    base = repo_paper
            except OSError:
                base = repo_paper
        else:
            base = repo_paper
        return str(base / "logs")


__all__ = ["HealthSnapshot", "HealthSnapshotEmitter"]
