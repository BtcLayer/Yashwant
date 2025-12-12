"""Compute rolling IC diagnostics between signals and realized PnL."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd
import pytz

IST = pytz.timezone("Asia/Kolkata")
FIVE_MIN = "5min"
WINDOW = 200

REQUIRED_SIGNAL_COLS = {"ts", "pred_bps"}
EQUITY_VALUE_CANDIDATES = ["equity", "equity_value", "equity_usd"]


def _parse_ts(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, errors="coerce")
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(IST, nonexistent="shift_forward", ambiguous="NaT")
    else:
        ts = ts.dt.tz_convert(IST)
    return ts


def load_signals(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_SIGNAL_COLS - set(df.columns)
    if missing:
        raise KeyError(f"signals.csv missing columns: {sorted(missing)}")
    df["ts"] = _parse_ts(df["ts"])
    df = df.dropna(subset=["ts"]).sort_values("ts").set_index("ts")
    return df[["pred_bps"]]


def load_equity_resampled(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    value_col = None
    for candidate in EQUITY_VALUE_CANDIDATES:
        if candidate in df.columns:
            value_col = candidate
            break
    if value_col is None:
        raise KeyError(
            "equity.csv must include one of columns: "
            + ", ".join(EQUITY_VALUE_CANDIDATES)
        )
    df["ts"] = _parse_ts(df["ts"])
    df = df.dropna(subset=["ts", value_col]).sort_values("ts").set_index("ts")
    resampled = df.resample(FIVE_MIN).last().ffill()
    resampled["realized_bps"] = (
        resampled[value_col].shift(-1) / resampled[value_col] - 1.0
    ) * 10000.0
    return resampled[["realized_bps"]]


def compute_ic(signals: pd.DataFrame, realized: pd.DataFrame) -> Dict[str, object]:
    merged = signals.join(realized, how="inner")
    merged = merged.dropna(subset=["pred_bps", "realized_bps"])
    rolling_ic = merged["pred_bps"].rolling(WINDOW).corr(merged["realized_bps"])
    valid_windows = rolling_ic.dropna()

    summary = {
        "total_pairs": len(merged),
        "valid_windows": len(valid_windows),
        "ic_latest": valid_windows.iloc[-1] if not valid_windows.empty else None,
        "ic_null": valid_windows.empty,
    }

    if len(merged) < WINDOW:
        summary["reason"] = "insufficient overlapping bars (<200)"
    elif summary["ic_null"]:
        summary["reason"] = "rolling correlation produced NaNs"
    else:
        summary["reason"] = "OK"

    return summary


def main(base_dir: str | Path = ".") -> None:
    base = Path(base_dir)
    try:
        signals = load_signals(base / "signals.csv")
        equity = load_equity_resampled(base / "equity.csv")
    except (FileNotFoundError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return

    summary = compute_ic(signals, equity)

    if summary["ic_null"]:
        print("IC unavailable:", summary["reason"])
    else:
        print(
            "Rolling IC available: latest=%.4f, valid windows=%d"
            % (summary["ic_latest"], summary["valid_windows"])
        )
    print("Total aligned bars:", summary["total_pairs"])
    print("Diagnostic summary:", summary)


if __name__ == "__main__":
    main()
