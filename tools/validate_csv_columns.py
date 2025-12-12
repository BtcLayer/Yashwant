"""Quick CSV schema validator for evaluation outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

REQUIRED_COLUMNS: Dict[str, List[str]] = {
    "equity.csv": [],
    "trade_log.csv": [
        "decision_time",
        "exec_time",
        "side",
        "qty",
        "price",
        "transaction_cost",
    ],
    "signals.csv": [
        "ts",
        "pred_bps",
        "pred_raw",
        "S_top",
        "S_bot",
        "adv20",
    ],
}


def validate_csv_columns(base_dir: str | Path = Path(".")) -> Dict[str, Dict[str, object]]:
    """Validate required columns per file and return a simple report."""
    base_path = Path(base_dir)
    report: Dict[str, Dict[str, object]] = {}

    for filename, required in REQUIRED_COLUMNS.items():
        file_path = base_path / filename
        status = {
            "path": str(file_path),
            "exists": file_path.exists(),
            "missing": [],
        }

        if not file_path.exists():
            print(f"MISSING FILE: {filename}")
            status["pass"] = False
            report[filename] = status
            continue

        df = pd.read_csv(file_path, nrows=1) if required else None
        for column in required:
            if df is None or column not in df.columns:
                print(f"MISSING: {column} in {filename}")
                status["missing"].append(column)

        status["pass"] = status["exists"] and not status["missing"]
        report[filename] = status

    print("CSV validation complete.")
    return report


def main() -> None:
    report = validate_csv_columns()
    print(report)


if __name__ == "__main__":
    main()
