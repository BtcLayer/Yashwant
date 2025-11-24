from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import gzip
import json
import pandas as pd

# Ensure repo root on path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.llm_logging import _unified_logs_root, _read_jsonl_gz, _normalize_df_columns  # type: ignore


def _collect_stream_df(stream: str, hours: int) -> pd.DataFrame:
    cutoff = datetime.now() - timedelta(hours=hours)
    root = _unified_logs_root()
    globs = []
    globs.extend(root.rglob(f"{stream}.jsonl.gz"))
    globs.extend(root.rglob(f"{stream}.jsonl"))
    frames = []
    for g in globs:
        df = None
        p = Path(g)
        if p.suffix == ".gz":
            df = _read_jsonl_gz(p)
        else:
            try:
                df = pd.read_json(p, lines=True)
            except Exception:
                df = None
        if df is None:
            continue
        if "ts_ist" not in df.columns:
            df = _normalize_df_columns(df)
        if "ts_ist" not in df.columns:
            continue
        try:
            df["ts_ist"] = pd.to_datetime(df["ts_ist"], errors="coerce")
            frames.append(df[df["ts_ist"] >= cutoff])
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _infer_cadence(bar_ids: pd.Series) -> int:
    # Attempt to detect minute cadence from median diff of consecutive bar_ids
    # bar_id approximates (timestamp floored to freq)
    if bar_ids.empty:
        return 5
    diffs = bar_ids.diff().dropna()
    if diffs.empty:
        return 5
    med = diffs.median()
    # Heuristics: 12h bars very large numbers apart; but we rely on env bar assignment
    # Instead of deriving minutes directly, classify by common minute multiples
    if med <= 5_000_000_000_000:  # nanoseconds for 5m (approx)
        return 5
    if med <= 60_000_000_000_000:  # 1h
        return 60
    return 720


def split_by_timeframe(stream_dfs: dict[str, pd.DataFrame]) -> dict[str, dict[str, pd.DataFrame]]:
    # Group records by run_id and classify run_id into a timeframe using cadence of bar_id deltas
    packs: dict[str, dict[str, pd.DataFrame]] = {"5m": {}, "1h": {}, "12h": {}}
    for stream, df in stream_dfs.items():
        if df.empty:
            continue
        if "run_id" not in df.columns:
            continue
        for run_id, sub in df.groupby("run_id"):
            cadence = _infer_cadence(sub.get("bar_id", pd.Series([])))
            tf = "5m" if cadence == 5 else ("1h" if cadence == 60 else "12h")
            if stream not in packs[tf]:
                packs[tf][stream] = sub.copy()
            else:
                packs[tf][stream] = pd.concat([packs[tf][stream], sub.copy()], ignore_index=True)
    return packs


def slim_frame(df: pd.DataFrame, stream: str, top_k: int) -> list[dict]:
    keep_common = ["ts_ist", "bar_id", "asset", "run_id"]
    per_stream_cols = {
        "market_ingest_log": ["mid", "spread_bps"],
        "calibration_log": ["a", "b", "pred_cal_bps", "in_band_flag", "band_bps"],
        "ensemble_log": ["pred_stack_bps"],
        "execution_log": ["fill_px", "fill_qty", "slip_bps"],
        "costs_log": ["cost_bps_total"],
        "pnl_equity_log": ["pnl_total_usd", "equity_value", "realized_return_bps"],
        "sizing_risk_log": ["position_after", "overlay_conf", "raw_score_bps"],
    }
    keep = [c for c in keep_common + per_stream_cols.get(stream, []) if c in df.columns]
    dff = df.sort_values("ts_ist").tail(int(top_k))[keep]
    try:
        dff["ts_ist"] = pd.to_datetime(dff["ts_ist"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        pass
    return dff.to_dict(orient="records")


def build_multi(hours: int, top_k: int, out_dir: Path) -> dict[str, str]:
    streams = [
        "market_ingest_log",
        "calibration_log",
        "ensemble_log",
        "execution_log",
        "costs_log",
        "pnl_equity_log",
        "sizing_risk_log",
    ]
    stream_dfs = {s: _collect_stream_df(s, hours) for s in streams}
    packs_by_tf = split_by_timeframe(stream_dfs)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for tf, maps in packs_by_tf.items():
        payload = {"timeframe": tf, "generated_utc": datetime.utcnow().isoformat() + "Z", "streams": {}}
        for stream, df in maps.items():
            payload["streams"][stream] = slim_frame(df, stream, top_k)
        out_path = out_dir / f"llm_context_{tf}.json.gz"
        with gzip.open(out_path, "wb") as f:
            f.write(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        written[tf] = str(out_path)
    return written


def main():
    ap = argparse.ArgumentParser(description="Build per-timeframe LLM context packs")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--top-k", type=int, default=500)
    ap.add_argument("--out-dir", type=str, default=str(Path("paper_trading_outputs") / "logs" / "llm_context"))
    args = ap.parse_args()
    out_dir = Path(args.out_dir).resolve()
    result = build_multi(hours=int(args.hours), top_k=int(args.top_k), out_dir=out_dir)
    for tf, path in result.items():
        print(f"{tf}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
