"""Signal and trade diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pandas as pd


def compute_signal_trade_metrics(
    equity_path: str | Path = "equity.csv",
    trade_path: str | Path = "trade_log.csv",
    signal_path: str | Path = "signals.csv",
) -> Dict[str, Optional[float]]:
    """Return summary metrics combining trade logs, signals, and equity curve.

    Any missing input simply leaves the corresponding metric as ``None``.
    """

    metrics: Dict[str, Optional[float]] = {
        "n_trades": None,
        "turnover_bps_day_approx": None,
        "avg_cost_bps": None,
        "total_cost_usd": None,
        "ic_roll200_mean": None,
    }

    # ------------------------------------------------------------------
    # Equity curve (for mean equity + realized returns)
    # ------------------------------------------------------------------
    equity_resampled = None
    mean_equity = None
    equity_file = Path(equity_path)
    if equity_file.exists():
        eq = pd.read_csv(equity_file)
        if {"ts", "equity_value"}.issubset(eq.columns):
            ts = pd.to_datetime(eq["ts"], utc=True, errors="coerce")
            eq = eq.assign(ts=ts).dropna(subset=["ts"])
            if not eq.empty:
                equity_resampled = (
                    eq.set_index("ts")
                    .sort_index()["equity_value"]
                    .resample("5min")
                    .last()
                    .ffill()
                )
                if not equity_resampled.empty:
                    mean_equity = equity_resampled.mean()

    # ------------------------------------------------------------------
    # Trade log metrics
    # ------------------------------------------------------------------
    trades_df = None
    trade_file = Path(trade_path)
    if trade_file.exists():
        trades_df = pd.read_csv(trade_file)
        if not trades_df.empty:
            metrics["n_trades"] = int(len(trades_df))
            if "transaction_cost" in trades_df.columns:
                total_cost = trades_df["transaction_cost"].dropna().sum()
                metrics["total_cost_usd"] = float(total_cost)
            if "cost_bps" in trades_df.columns:
                metrics["avg_cost_bps"] = float(trades_df["cost_bps"].dropna().mean())
            if (
                mean_equity
                and mean_equity != 0
                and {"qty", "price"}.issubset(trades_df.columns)
            ):
                notional = (trades_df["qty"] * trades_df["price"]).abs().dropna()
                if not notional.empty:
                    turnover = notional.mean() * 288.0 / mean_equity * 1e4
                    metrics["turnover_bps_day_approx"] = float(turnover)

    # ------------------------------------------------------------------
    # Rolling IC using next-bar realized returns vs signal predictions
    # ------------------------------------------------------------------
    signal_file = Path(signal_path)
    if equity_resampled is not None and signal_file.exists():
        sig = pd.read_csv(signal_file)
        if {"ts", "pred_bps"}.issubset(sig.columns):
            sig_ts = pd.to_datetime(sig["ts"], utc=True, errors="coerce")
            sig = (
                sig.assign(ts=sig_ts)
                .dropna(subset=["ts"])
                .set_index("ts")
                .sort_index()
            )
            if not sig.empty:
                realized = equity_resampled.pct_change().shift(-1).rename("realized")
                combined = sig[["pred_bps"]].join(realized, how="inner").dropna()
                if len(combined) >= 200:
                    rolling_ic = combined["pred_bps"].rolling(200).corr(combined["realized"])
                    ic_mean = rolling_ic.dropna().mean()
                    if pd.notna(ic_mean):
                        metrics["ic_roll200_mean"] = float(ic_mean)

    return metrics


if __name__ == "__main__":
    print(compute_signal_trade_metrics())
