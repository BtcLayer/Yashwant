"""Utilities to persist summary metrics as JSON."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:  # Optional pandas import for Timestamp handling without hard dependency.
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover
    pd = None  # type: ignore


ISO_KEYS: Iterable[str] = ("start_ts", "end_ts")
JSON_KEYS: Iterable[str] = (
    "bars",
    "start_ts",
    "end_ts",
    "sharpe_ann",
    "max_drawdown_frac",
    "n_trades",
    "win_rate",
    "ic_roll200_mean",
    "turnover_bps_day_approx",
    "avg_cost_bps",
    "total_cost_usd",
)


def _to_iso(value: Any) -> Optional[str]:
    """Convert supported timestamp types into ISO strings."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if pd is not None and isinstance(value, pd.Timestamp):
        return value.isoformat()
    # Attempt generic conversion for objects exposing isoformat.
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    return str(value)


def write_metrics_json(metrics: Dict[str, Any], path: str | Path = "metrics.json") -> None:
    """Write the selected metrics to JSON, defaulting missing values to None."""
    payload: Dict[str, Any] = {}
    for key in JSON_KEYS:
        value = metrics.get(key)
        if key in ISO_KEYS:
            payload[key] = _to_iso(value)
        else:
            payload[key] = value if value is not None else None
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    # Example usage with partial metrics (missing values remain None in JSON).
    example = {
        "bars": 500,
        "start_ts": datetime.now(UTC),
        "end_ts": datetime.now(UTC),
        "sharpe_ann": 1.25,
        "n_trades": 42,
    }
    write_metrics_json(example)
    print(Path("metrics.json").read_text())
