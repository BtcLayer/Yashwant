"""Assemble attachment-friendly markdown summary."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

MAX_WORDS = 400


def _fmt(value: Any, default: str = "n/a") -> str:
    if value is None:
        return default
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def build_summary(
    metrics: Dict[str, Any],
    data_summary: Iterable[Dict[str, str]],
    readiness_scores: Dict[str, Any],
    output_path: str | Path = "summary.md",
) -> None:
    """Create a concise markdown status summary (<=400 words)."""
    start_ts = _fmt(metrics.get("start_ts"))
    end_ts = _fmt(metrics.get("end_ts"))
    bars = _fmt(metrics.get("bars"))
    sharpe = _fmt(metrics.get("sharpe_ann"))
    dd_value = metrics.get("max_drawdown_frac")
    if dd_value is None:
        dd_value = metrics.get("max_drawdown")
    drawdown = _fmt(dd_value)
    turnover = _fmt(metrics.get("turnover_bps_day_approx"))
    costs = _fmt(metrics.get("total_cost_usd"))
    avg_cost = _fmt(metrics.get("avg_cost_bps"))
    win_value = metrics.get("win_rate_pct")
    if win_value is None:
        win_value = metrics.get("win_rate")
    win_rate = _fmt(win_value)
    ic = _fmt(metrics.get("ic_roll200_mean"))

    def summarize_data() -> str:
        lines = []
        for row in data_summary:
            name = row.get("file", "?")
            rows = row.get("rows", "?")
            span = f"{row.get('min_ts', 'n/a')} → {row.get('max_ts', 'n/a')}"
            lines.append(f"- `{name}`: {rows} rows, span {span}")
        return "\n".join(lines) or "- No data available"

    def summarize_readiness() -> str:
        lines = []
        for item, payload in readiness_scores.items():
            if isinstance(payload, (list, tuple)) and len(payload) == 2:
                score, reason = payload
            else:
                score, reason = payload, "No reason provided"
            lines.append(f"- {item}: **{score}** — {reason}")
        return "\n".join(lines) or "- No readiness inputs"

    statistical_power = (
        "⚠️ Limited sample: interpret Sharpe / IC cautiously." if bars == "?" or bars == "n/a" else ""
    )
    behavior_notes = f"Signals vs next-bar IC(200): {ic}."
    logging_health = readiness_scores.get("Instrumentation/logging", ("n/a", "No signal"))[1]

    sections = [
        f"**Date Range & Coverage**\n- Bars analyzed: {bars}\n- Range: {start_ts} → {end_ts}",
        f"**Performance Snapshot**\n- Sharpe (ann.): {sharpe}\n- Max drawdown: {drawdown}\n- Win rate: {win_rate}\n- Turnover (bps/day): {turnover}\n- Costs: avg {avg_cost} bps / total ${costs}",
        f"**Statistical Power**\n{statistical_power or 'Current sample considered adequate.'}",
        f"**Behavior Notes**\n{behavior_notes}",
        f"**Logging & Emitters**\n{logging_health}",
        f"**Data Health**\n{summarize_data()}",
        f"**Readiness**\n{summarize_readiness()}",
    ]

    content = "\n\n".join(s.strip() for s in sections if s.strip())
    words = content.split()
    if len(words) > MAX_WORDS:
        content = " ".join(words[:MAX_WORDS])
    Path(output_path).write_text(content + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_summary({}, [], {})
