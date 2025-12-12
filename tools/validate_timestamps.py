"""Timestamp health checks for evaluation CSVs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd
import pytz

IST = pytz.timezone("Asia/Kolkata")

FILE_SPECS: Dict[str, List[str]] = {
    "equity.csv": ["ts"],
    "trade_log.csv": ["decision_time", "exec_time"],
    "signals.csv": ["ts"],
}


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing")
    return pd.read_csv(path)


def to_ist(series: pd.Series) -> pd.Series:
    def _convert(value):
        if pd.isna(value):
            return pd.NaT
        dt = pd.to_datetime(value, errors="coerce")
        if dt is pd.NaT:
            return pd.NaT
        if dt.tzinfo is None:
            try:
                dt = dt.tz_localize(IST)
            except TypeError:
                dt = pd.NaT
        else:
            dt = dt.tz_convert(IST)
        return dt

    return series.apply(_convert)


def validate_timestamps(df: pd.DataFrame, columns: List[str], label: str) -> None:
    for column in columns:
        if column not in df.columns:
            print(f"{label}: missing column {column}")
            continue

        series = to_ist(df[column])

        if series.isna().any():
            print(f"{label}: timezone conversion produced NaT in column {column}")

        if not series.apply(lambda x: getattr(x, "tzinfo", None) is not None).all():
            print(f"{label}: Timezone missing in column {column}")

        if not series.is_monotonic_increasing:
            print(f"{label}: Timestamp out of order in column {column}")


def main(base_dir: str | Path = ".") -> None:
    base = Path(base_dir)
    for filename, columns in FILE_SPECS.items():
        path = base / filename
        try:
            df = load_csv(path)
        except FileNotFoundError as exc:
            print(str(exc))
            continue
        validate_timestamps(df, columns, filename)

    print("Timestamp validation complete.")


if __name__ == "__main__":
    main()
