"""Generate markdown summary for core data files."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

FILES = {
    "equity.csv": ["ts", "equity_value"],
    "trade_log.csv": ["decision_time", "exec_time", "side", "qty", "price", "transaction_cost"],
    "signals.csv": ["ts", "pred_bps", "pred_raw", "S_top", "S_bot", "adv20"],
}


def summarize_file(path: Path, required_cols: List[str]) -> Dict[str, str]:
    if not path.exists():
        return {
            "file": path.name,
            "rows": "missing",
            "min_ts": "n/a",
            "max_ts": "n/a",
            "nan_counts": "n/a",
        }
    df = pd.read_csv(path)
    summary: Dict[str, str] = {
        "file": path.name,
        "rows": str(len(df)),
        "min_ts": "n/a",
        "max_ts": "n/a",
        "nan_counts": "",
    }
    if "ts" in df.columns:
        ts_series = pd.to_datetime(df["ts"], errors="coerce")
    elif "decision_time" in df.columns:
        ts_series = pd.to_datetime(df["decision_time"], errors="coerce")
    else:
        ts_series = None
    if ts_series is not None and not ts_series.dropna().empty:
        summary["min_ts"] = ts_series.min().isoformat()
        summary["max_ts"] = ts_series.max().isoformat()
    nan_info = []
    for col in required_cols:
        count = df[col].isna().sum() if col in df.columns else len(df)
        nan_info.append(f"{col}: {count}")
    summary["nan_counts"] = ", ".join(nan_info)
    return summary


def generate_data_summary(output: str | Path = "data_summary.md") -> None:
    rows = []
    for file_name, cols in FILES.items():
        rows.append(summarize_file(Path(file_name), cols))
    lines = ["| File | Rows | Min TS | Max TS | NaN counts |", "| --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row['file']} | {row['rows']} | {row['min_ts']} | {row['max_ts']} | {row['nan_counts']} |")
    Path(output).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    generate_data_summary()
