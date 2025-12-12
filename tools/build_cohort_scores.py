"""Assign cohorts and compute normalized top/bottom scores for signals."""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

# Quantiles split the population into five equal buckets: bottom 20% .. top 20%.
# We keep the labels ordered so "Q1" is the weakest cohort and "Q5" is the strongest.
QUANTILE_BOUNDS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
COHORT_LABELS = ["Q1", "Q2", "Q3", "Q4", "Q5"]
OUTPUT_FILE = "signals_with_cohorts.csv"


def _normalize(series: pd.Series) -> pd.Series:
    """Return zero-mean/unit-std z-scores while preserving NaNs."""
    if series.dropna().empty:
        return pd.Series([pd.NA] * len(series), index=series.index)
    std = series.std(skipna=True, ddof=0)
    if std is None or pd.isna(std) or std == 0:
        return pd.Series([pd.NA] * len(series), index=series.index)
    return (series - series.mean(skipna=True)) / std


def _assign_cohorts(df: pd.DataFrame) -> pd.Series:
    """Assign cohorts via quantiles if missing; otherwise reuse provided cohort column."""
    # Respect upstream cohort annotations when available; otherwise fall back
    # to a quantile cut on pred_raw so we still get top/bottom bands.
    if "cohort" in df.columns and df["cohort"].notna().any():
        return df["cohort"].astype(str)

    if "pred_raw" not in df.columns:
        raise KeyError("pred_raw column required when cohort assignment is absent")

    valid = df["pred_raw"].dropna()
    if valid.nunique() < 2:
        cohorts = pd.Series("Q3", index=df.index, dtype=object)
        return cohorts

    try:
        # qcut applies the explicit quantile edges above; duplicates="drop"
        # keeps the code resilient when all pred_raw values collapse to a
        # narrower range than the requested bins.
        quant_cohorts = pd.qcut(
            valid,
            q=QUANTILE_BOUNDS,
            labels=COHORT_LABELS[: len(QUANTILE_BOUNDS) - 1],
            duplicates="drop",
        )
    except ValueError:
        # Edge-case fallback when pred_raw is constant: rank the rows and
        # re-run qcut so the cohorts remain well-defined.
        ranks = valid.rank(method="first")
        quant_cohorts = pd.qcut(
            ranks,
            q=len(COHORT_LABELS),
            labels=COHORT_LABELS,
            duplicates="drop",
        )

    cohorts = pd.Series(pd.NA, index=df.index, dtype=object)
    cohorts.loc[quant_cohorts.index] = quant_cohorts.astype(str)
    return cohorts


def build_cohort_scores(signals_path: Path = Path("signals.csv")) -> Path:
    df = pd.read_csv(signals_path)
    if "pred_bps" not in df.columns:
        raise KeyError("signals.csv must contain pred_bps")

    df["cohort_assigned"] = _assign_cohorts(df)

    cohort_order: List[str] = [
        label for label in COHORT_LABELS if label in df["cohort_assigned"].unique()
    ]
    if not cohort_order:
        raise ValueError("No cohorts available after assignment")

    top_label = cohort_order[-1]
    bot_label = cohort_order[0]

    df["S_top"] = df["pred_bps"].where(df["cohort_assigned"] == top_label)
    df["S_bot"] = df["pred_bps"].where(df["cohort_assigned"] == bot_label)

    df["S_top_norm"] = _normalize(df["S_top"])
    df["S_bot_norm"] = _normalize(df["S_bot"])

    output_path = signals_path.parent / OUTPUT_FILE
    df.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    out = build_cohort_scores()
    print(f"Wrote {out}")
