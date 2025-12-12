"""Utility to backfill equity/trade/signal CSVs from archived JSONL logs."""

from __future__ import annotations

import glob
import gzip
import json
import os
from pathlib import Path
import zipfile

import pandas as pd

# Output filenames relative to repo root
EQUITY_CSV = Path("equity.csv")
TRADE_CSV = Path("trade_log.csv")
SIGNALS_CSV = Path("signals.csv")
ZIP_BUNDLE = Path("./paper_trading_outputs/logs_emitters_all_timeframes_2025-12-07_to_2025-12-08.zip")
EXTRACT_DIR = Path("/tmp/logs_bundle")

NEEDED = (
    (EQUITY_CSV, "pnl_equity_log"),
    (TRADE_CSV, "execution_log"),
    (SIGNALS_CSV, "ensemble_log"),
)


def all_outputs_present() -> bool:
    """Return True if every required CSV already exists."""
    return all(path.exists() for path, _ in NEEDED)


def ensure_bundle_extracted() -> None:
    """Extract bundle into EXTRACT_DIR if it is not already populated."""
    if EXTRACT_DIR.exists() and any(EXTRACT_DIR.iterdir()):
        return
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_BUNDLE, "r") as zf:
        zf.extractall(EXTRACT_DIR)


def iter_records(topic: str):
    """Yield dicts from JSONL.gz files that match the topic name."""
    pattern = str(EXTRACT_DIR / "**" / f"{topic}*.jsonl.gz")
    for gz_path in glob.iglob(pattern, recursive=True):
        with gzip.open(gz_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                record = payload.get(topic, payload)
                record["_source_file"] = gz_path
                yield record


def build_equity_df() -> pd.DataFrame:
    rows = []
    for rec in iter_records("pnl_equity_log"):
        rows.append(
            {
                "ts": rec.get("ts_ist") or rec.get("ts"),
                "equity_value": rec.get("equity") or rec.get("equity_value"),
            }
        )
    return pd.DataFrame(rows)


def build_trade_df() -> pd.DataFrame:
    rows = []
    for rec in iter_records("execution_log"):
        transaction_cost = rec.get("fee")
        if transaction_cost is None:
            transaction_cost = rec.get("cost_bps")
        rows.append(
            {
                "decision_time": rec.get("decision_time_ist") or rec.get("decision_time"),
                "exec_time": rec.get("exec_time_ist") or rec.get("exec_time"),
                "side": rec.get("side"),
                "qty": rec.get("fill_qty") or rec.get("qty"),
                "price": rec.get("fill_price") or rec.get("price"),
                "transaction_cost": transaction_cost,
            }
        )
    return pd.DataFrame(rows)


def build_signals_df() -> pd.DataFrame:
    rows = []
    for rec in iter_records("ensemble_log"):
        rows.append(
            {
                "ts": rec.get("ts_ist") or rec.get("ts"),
                "pred_bps": rec.get("pred_bps"),
                "pred_raw": rec.get("pred_raw"),
                "S_top": rec.get("S_top"),
                "S_bot": rec.get("S_bot"),
                "adv20": rec.get("adv20"),
            }
        )
    return pd.DataFrame(rows)


BUILDERS = {
    EQUITY_CSV: build_equity_df,
    TRADE_CSV: build_trade_df,
    SIGNALS_CSV: build_signals_df,
}


def main() -> None:
    if all_outputs_present():
        print("All CSVs already exist; nothing to build.")
        return

    ensure_bundle_extracted()

    for csv_path, _ in NEEDED:
        if csv_path.exists():
            continue
        df = BUILDERS[csv_path]()
        df.to_csv(csv_path, index=False)
        print(f"Wrote {csv_path.name} with {len(df)} rows.")


if __name__ == "__main__":
    main()
