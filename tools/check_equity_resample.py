"""Convenience script to inspect 5-minute continuity in equity.csv."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd
import pytz

IST = pytz.timezone("Asia/Kolkata")
FIVE_MIN = pd.Timedelta(minutes=5)


def load_equity(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing")
    df = pd.read_csv(path)
    if "ts" not in df.columns:
        raise KeyError("equity.csv must contain a 'ts' column")
    ts = pd.to_datetime(df["ts"], errors="coerce", utc=False)
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(IST, nonexistent="shift_forward", ambiguous="NaT")
    else:
        ts = ts.dt.tz_convert(IST)
    df["ts"] = ts
    df = df.dropna(subset=["ts"]).sort_values("ts")
    df = df.set_index("ts")
    return df


def find_gaps(index: pd.DatetimeIndex) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    diffs = index.to_series().diff()
    gaps = diffs[diffs > FIVE_MIN]
    out: List[Tuple[pd.Timestamp, pd.Timestamp]] = []
    for ts, delta in gaps.items():
        start = ts - delta + FIVE_MIN
        out.append((start, ts))
    return out


def check_resample(path: Path = Path("equity.csv")) -> None:
    df = load_equity(path)
    resampled = df.resample("5min").last().ffill()

    gaps = find_gaps(df.index)
    expected_bars = int(((resampled.index[-1] - resampled.index[0]) / FIVE_MIN) + 1)
    actual_bars = len(resampled)

    anomalies = False
    if gaps:
        anomalies = True
        print("Detected gaps in source equity timestamps:")
        for start, end in gaps[:10]:
            print(f"  Gap from {start} to {end}")
        if len(gaps) > 10:
            print(f"  ... {len(gaps) - 10} more gaps")
    if actual_bars != expected_bars:
        anomalies = True
        print(
            "Bar count mismatch: actual resampled bars ="
            f" {actual_bars}, expected = {expected_bars}"
        )

    if not anomalies:
        print("Resample OK")
    else:
        print("Resample anomalies detected.")


if __name__ == "__main__":
    check_resample()
