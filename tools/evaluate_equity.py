"""Equity curve evaluation helpers."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict

import pandas as pd


def evaluate_equity(path: str | Path = "equity.csv") -> Dict[str, float]:
    """Compute basic performance diagnostics from an equity curve.

    Parameters
    ----------
    path: Path-like
        Location of the CSV containing columns ``ts`` and ``equity_value``.

    Returns
    -------
    Dict[str, float]
        Rounded metrics: annualized Sharpe, max drawdown fraction, win rate pct.
    """

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("equity.csv is empty")

    ts = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    if ts.isna().all():
        raise ValueError("Unable to parse any timestamps in equity.csv")

    df = df.assign(ts=ts.dt.tz_convert("Asia/Kolkata"))
    df = df.set_index("ts").sort_index()

    # Resample to 5-minute bars using last observation per window; fill gaps forward.
    equity = df["equity_value"].resample("5min").last().ffill()
    if equity.isna().all():
        raise ValueError("Equity series is entirely NaN after resampling")

    returns = equity.pct_change().dropna()
    if returns.empty:
        raise ValueError("Not enough observations to compute returns")

    ann_factor = math.sqrt(252 * 288)
    std = returns.std(ddof=0)
    sharpe = (returns.mean() / std) * ann_factor if std > 0 else float("nan")

    cumulative = (1 + returns).cumprod()
    roll_max = cumulative.cummax()
    drawdown = cumulative / roll_max - 1
    max_drawdown = drawdown.min()

    win_rate = (returns > 0).mean() * 100.0

    return {
        "annualized_sharpe": round(float(sharpe), 4) if not math.isnan(sharpe) else float("nan"),
        "max_drawdown": round(float(max_drawdown), 4),
        "win_rate_pct": round(float(win_rate), 2),
    }


if __name__ == "__main__":
    print(evaluate_equity())
