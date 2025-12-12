"""Turn-key evaluator for Ensemble 1.0 dry runs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple

import pandas as pd

from tools import build_paper_csvs as csv_builder
from tools.build_summary import build_summary
from tools.data_summary import FILES, generate_data_summary, summarize_file
from tools.evaluate_equity import evaluate_equity
from tools.readiness_table import write_readiness_table
from tools.signal_trade_metrics import compute_signal_trade_metrics
from tools.write_metrics_json import write_metrics_json

# Simple default readiness snapshot; edit as needed before sharing.
DEFAULT_READINESS: Dict[str, Tuple[str, str]] = {
    "Cohort signals": ("TBD", "Awaiting latest cohort attribution."),
    "OOF stacking": ("TBD", "OOF stack verification queued."),
    "Calibration + band": ("TBD", "Band thresholds not re-validated yet."),
    "Microstructure overlays": ("TBD", "Overlay regen pending."),
    "BMA/bandit": ("TBD", "Need live arm telemetry."),
    "Purged/embargoed WF-CV": ("TBD", "WF-CV artifacts not re-run."),
    "Risk controls": ("TBD", "Risk guardrails mirrored from prior release."),
    "Instrumentation/logging": ("TBD", "Emitter/stateful logging smoke TBD."),
    "Logs v2 + snapshots": ("TBD", "Snapshot writer not smoke-tested."),
}


def ensure_canonical_csvs() -> None:
    """Create canonical equity/trade/signal CSVs if they are missing."""
    if csv_builder.all_outputs_present():
        return
    csv_builder.ensure_bundle_extracted()
    for csv_path, _ in csv_builder.NEEDED:
        if csv_path.exists():
            continue
        df = csv_builder.BUILDERS[csv_path]()
        df.to_csv(csv_path, index=False)
        print(f"Wrote {csv_path.name} with {len(df)} rows.")


def load_equity_metadata(equity_path: Path) -> Dict[str, str]:
    df = pd.read_csv(equity_path)
    ts = pd.to_datetime(df["ts"], errors="coerce")
    ts = ts.dropna()
    if ts.empty:
        return {"bars": "n/a", "start_ts": "n/a", "end_ts": "n/a"}
    return {
        "bars": len(df),
        "start_ts": ts.min().isoformat(),
        "end_ts": ts.max().isoformat(),
    }


def collect_data_rows() -> Iterable[Dict[str, str]]:
    return [summarize_file(Path(name), cols) for name, cols in FILES.items()]


def main() -> None:
    ensure_canonical_csvs()

    equity_metrics = evaluate_equity()
    trade_signal_metrics = compute_signal_trade_metrics()

    equity_meta = load_equity_metadata(csv_builder.EQUITY_CSV)

    metrics = {
        "bars": equity_meta["bars"],
        "start_ts": equity_meta["start_ts"],
        "end_ts": equity_meta["end_ts"],
        "sharpe_ann": equity_metrics.get("annualized_sharpe"),
        "max_drawdown_frac": equity_metrics.get("max_drawdown"),
        "win_rate_pct": equity_metrics.get("win_rate_pct"),
    }
    metrics.update(trade_signal_metrics)

    write_metrics_json(metrics)

    data_rows = collect_data_rows()
    generate_data_summary()
    write_readiness_table(DEFAULT_READINESS)
    build_summary(metrics, data_rows, DEFAULT_READINESS)
    print("evaluation complete")


if __name__ == "__main__":
    main()
