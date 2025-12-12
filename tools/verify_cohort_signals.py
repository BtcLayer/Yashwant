"""Validate cohort coverage and normalized scores in signals_with_cohorts.csv."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd

SOURCE_FILE = Path("signals_with_cohorts.csv")
OUTPUT_FILE = Path("cohort_stats.csv")
MIN_PCT = 0.005
MIN_STD = 0.1


def _get_cohort_column(df: pd.DataFrame) -> str:
    if "cohort" in df.columns:
        return "cohort"
    if "cohort_assigned" in df.columns:
        return "cohort_assigned"
    raise KeyError("Expected 'cohort' or 'cohort_assigned' column in signals_with_cohorts.csv")


def _require_columns(df: pd.DataFrame, columns: Tuple[str, ...]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise KeyError(f"Missing columns: {missing}")


def verify_cohorts(path: Path = SOURCE_FILE) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")

    df = pd.read_csv(path)
    cohort_col = _get_cohort_column(df)
    _require_columns(df, (cohort_col, "S_top_norm", "S_bot_norm"))

    total_rows = len(df)
    cohort_counts = df[cohort_col].value_counts(dropna=False).sort_index()
    print(f"Unique cohorts: {cohort_counts.shape[0]}")
    print(cohort_counts)

    s_top_mean = df["S_top_norm"].mean(skipna=True)
    s_top_std = df["S_top_norm"].std(skipna=True)
    s_bot_mean = df["S_bot_norm"].mean(skipna=True)
    s_bot_std = df["S_bot_norm"].std(skipna=True)

    print(
        f"S_top_norm mean={s_top_mean:.4f} std={s_top_std:.4f}; "
        f"S_bot_norm mean={s_bot_mean:.4f} std={s_bot_std:.4f}"
    )

    coverage = df["S_top_norm"].notna().sum() / max(total_rows, 1)
    print(f"Time coverage (non-null S_top_norm): {coverage:.2%}")

    if pd.isna(s_top_std) or s_top_std < MIN_STD:
        print(
            "WARNING: S_top_norm lacks variation (std missing or < 0.1). Suggestion: ensure "
            "pred_bps is populated for the top cohort or expand the sample window before "
            "normalizing."
        )

    low_cohort = cohort_counts[cohort_counts / max(total_rows, 1) < MIN_PCT]
    for cohort, count in low_cohort.items():
        pct = count / max(total_rows, 1)
        print(
            f"WARNING: Cohort {cohort} has only {pct:.2%} of rows."
            " Suggestion: adjust quantile buckets or inspect upstream assignment."
        )

    stats_rows = []
    for cohort, count in cohort_counts.items():
        mask = df[cohort_col] == cohort
        stats_rows.append(
            {
                "cohort": cohort,
                "count": int(count),
                "pct_rows": count / max(total_rows, 1),
                "s_top_mean": df.loc[mask, "S_top_norm"].mean(skipna=True),
                "s_top_std": df.loc[mask, "S_top_norm"].std(skipna=True),
                "s_bot_mean": df.loc[mask, "S_bot_norm"].mean(skipna=True),
                "s_bot_std": df.loc[mask, "S_bot_norm"].std(skipna=True),
            }
        )

    stats_df = pd.DataFrame(stats_rows)
    stats_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved cohort stats to {OUTPUT_FILE}")
    print("Cohort signals verification complete.")


if __name__ == "__main__":
    verify_cohorts()
