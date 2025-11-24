"""
Lightweight IST JSONL emitters, validator, and LLM context-pack builder.

Usage:
  from ops.llm_logging import write_jsonl, validate_file, build_llm_context_pack

Conventions:
  - Timestamps are Asia/Kolkata (IST) ISO-8601 strings.
  - Each record includes bar_id derived from 5m bars by default.
  - Files are gzip-compressed JSONL, partitioned by date and asset.
  - Per-record size caps (<= 32 fields, <= 1.5KB) enforced best-effort.

These utilities are additive and do not change existing logging; they write
into logs/<stream>/date=YYYY-MM-DD/asset=<ASSET>/<stream>.jsonl.gz
"""

from __future__ import annotations

import gzip
import json
import os
import pathlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import pytz

IST = pytz.timezone("Asia/Kolkata")
RUN_ID = os.environ.get("RUN_ID", str(uuid.uuid4()))

# Per-record budget and per-stream daily budget guard (soft)
SIZE_BUDGET = dict(max_fields=32, max_bytes=1500)  # bytes after JSON serialization
STREAM_BUDGET_MB = 200  # soft daily ceiling per asset per stream


def ist_now() -> str:
    """Current IST timestamp in ISO-8601."""
    return datetime.now(IST).isoformat()


def bar_id_from_ts(ts_ist: str, freq_minutes: int = 5) -> int:
    """Compute a monotonically increasing bar_id aligned to IST at freq_minutes granularity.

    Note: This is a deterministic mapping for logging; for trading logic use
    your existing bar sequencing.
    """
    ts = pd.to_datetime(ts_ist)
    # Floor to frequency
    nanos = int(freq_minutes) * 60 * 1_000_000_000
    return int(ts.value // nanos)


def _ensure_caps(rec: Dict) -> Dict:
    """Trim a record to stay within field and byte budgets."""
    # Drop extra fields beyond the first N (stable order on insertion in Python 3.7+)
    keys = list(rec.keys())
    if len(keys) > SIZE_BUDGET["max_fields"]:
        for k in keys[SIZE_BUDGET["max_fields"]:]:
            rec.pop(k, None)
    # Truncate very long strings
    for k, v in list(rec.items()):
        if isinstance(v, str) and len(v) > 256:
            rec[k] = v[:256]
    # Check serialized size and drop optional bulky keys if needed
    s = json.dumps(rec, separators=(",", ":"))
    if len(s.encode("utf-8")) > SIZE_BUDGET["max_bytes"]:
        for k in [
            "reason_codes",
            "bandit_weights",
            "bandit_weights_slim",
            "feature_dump",
            "extra",
        ]:
            if k in rec:
                rec.pop(k, None)
    return rec


def _unified_logs_root() -> pathlib.Path:
    """Resolve the absolute logs root.

    Priority:
      1) PAPER_TRADING_ROOT/logs if PAPER_TRADING_ROOT is set
      2) <repo>/paper_trading_outputs/logs
    """
    env_root = os.environ.get("PAPER_TRADING_ROOT")
    try:
        if env_root:
            base = pathlib.Path(env_root).resolve() / "logs"
            return base
    except Exception:
        pass
    here = pathlib.Path(__file__).resolve()
    repo_root = here.parent.parent
    return (repo_root / "paper_trading_outputs" / "logs").resolve()


def part_path(stream: str, ts_ist: str, asset: str = "ALL", *, base_root: Optional[str] = None) -> str:
    dt = pd.to_datetime(ts_ist)
    # If a base_root is provided, honor it; otherwise use unified logs root
    base_dir = pathlib.Path(base_root).resolve() if base_root else _unified_logs_root()
    base = base_dir / stream / f"date={dt.date()}" / f"asset={asset}"
    return str((base / f"{stream}.jsonl.gz").resolve())


def write_jsonl(stream: str, rec: Dict, asset: str = "ALL", *, freq_minutes: int = 5, root: Optional[str] = None) -> str:
    """Append a single JSON record to the gzipped JSONL partition for (stream, date, asset).

    Returns: absolute path written to (string)
    """
    # Minimal envelope
    rec = {"run_id": RUN_ID, **rec}
    rec.setdefault("ts_ist", ist_now())
    rec.setdefault("schema_v", "1")
    # Allow overriding bar frequency for bar_id via environment (e.g., 60 for 1h, 720 for 12h)
    try:
        env_freq = os.environ.get("LLM_FREQ_MINUTES")
        fm = int(env_freq) if env_freq is not None else int(freq_minutes)
    except Exception:
        fm = int(freq_minutes)
    rec.setdefault("bar_id", bar_id_from_ts(rec["ts_ist"], freq_minutes=fm))
    rec = _ensure_caps(rec)
    p = pathlib.Path(part_path(stream, rec["ts_ist"], asset, base_root=root))
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "ab") as f:
        f.write((json.dumps(rec, separators=(",", ":")) + "\n").encode("utf-8"))
    return str(p.resolve())


def _read_jsonl_gz(path: pathlib.Path) -> Optional[pd.DataFrame]:
    try:
        return pd.read_json(path, lines=True, compression="gzip")
    except Exception:
        return None


def _normalize_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort normalization to ensure ts_ist/asset/bar_id exist.
    - ts_ist: try ts_ist, then ts_iso, then nested sanitized.*.ts_ist, then numeric ts
    - asset: fallback to symbol
    - bar_id: derive from ts_ist if missing (5m default)
    """
    df = df.copy()
    # ts_ist
    if "ts_ist" not in df.columns:
        if "ts_iso" in df.columns:
            try:
                df["ts_ist"] = pd.to_datetime(df["ts_iso"], errors="coerce")
            except Exception:
                df["ts_ist"] = pd.NaT
        elif "sanitized" in df.columns:
            def _extract_ts_from_sanitized(v):
                if isinstance(v, dict):
                    # search for nested dict with ts_ist
                    for sub in v.values():
                        if isinstance(sub, dict) and ("ts_ist" in sub):
                            return sub.get("ts_ist")
                return None
            try:
                df["ts_ist"] = pd.to_datetime(df["sanitized"].apply(_extract_ts_from_sanitized), errors="coerce")
            except Exception:
                df["ts_ist"] = pd.NaT
        elif "ts" in df.columns:
            def _from_ts(val):
                try:
                    t = float(val)
                except Exception:
                    return pd.NaT
                try:
                    if t > 1e12:
                        return pd.to_datetime(t, unit="ms", utc=True).tz_convert("Asia/Kolkata")
                    elif t > 1e9:
                        return pd.to_datetime(t, unit="s", utc=True).tz_convert("Asia/Kolkata")
                except Exception:
                    return pd.NaT
                return pd.NaT
            try:
                df["ts_ist"] = df["ts"].apply(_from_ts)
            except Exception:
                df["ts_ist"] = pd.NaT
        else:
            df["ts_ist"] = pd.NaT
    else:
        try:
            df["ts_ist"] = pd.to_datetime(df["ts_ist"], errors="coerce")
        except Exception:
            df["ts_ist"] = pd.NaT

    # asset fallback from symbol
    if "asset" not in df.columns and "symbol" in df.columns:
        try:
            df["asset"] = df["symbol"]
        except Exception:
            pass

    # bar_id from ts_ist if missing
    if "bar_id" not in df.columns:
        try:
            nanos = 5 * 60 * 1_000_000_000
            df["bar_id"] = df["ts_ist"].apply(lambda x: int(pd.Timestamp(x).value // nanos) if pd.notna(x) else None)
        except Exception:
            pass
    return df


def validate_file(path: str) -> Dict:
    """Lightweight validator for a gzipped JSONL file. Prints a summary dict and returns it."""
    p = pathlib.Path(path)
    df = _read_jsonl_gz(p)
    issues: Dict = {"file": str(p)}
    if df is None:
        issues.update({"error": "read_failed"})
        print(issues)
        return issues
    issues["rows"] = int(len(df))
    # Required fields per stream (subset checks)
    req = {
        "market_ingest_log": ["ts_ist", "bar_id", "asset", "mid", "spread_bps", "obi_10", "book_lag_ms"],
        "prediction_log": ["ts_ist", "bar_id", "asset", "pred_stack_bps"],
        "calibration_log": ["ts_ist", "bar_id", "asset", "a", "b", "pred_cal_bps", "in_band_flag", "band_bps"],
        "ensemble_log": ["ts_ist", "bar_id", "asset", "bandit_arm", "pred_stack_bps"],
        "sizing_risk_log": ["ts_ist", "bar_id", "asset", "position_before", "position_after", "notional_usd"],
        "execution_log": ["exec_time_ist", "bar_id_exec", "asset", "fill_px", "fill_qty"],
        "pnl_equity_log": ["ts_ist", "bar_id", "asset", "pnl_total_usd", "equity_value"],
    }
    for k, need in req.items():
        if k in str(p):
            for c in need:
                issues[c] = int(df[c].isna().sum()) if c in df else "MISSING"
    if "bar_id" in df:
        mono = (df["bar_id"].diff().fillna(1) >= 0).all()
        issues["non_monotonic_bar_id"] = bool(not mono)
    try:
        size_bytes = p.stat().st_size
        issues["file_size_mb"] = round(size_bytes / 1_048_576, 2)
    except OSError:
        pass
    print(issues)
    return issues


def build_llm_context_pack(
    root: str = "logs",
    hours: int = 24,
    top_k: int = 500,
    out: str = "llm_context/context_pack.json.gz",
) -> str:
    """Build a compact, gzipped JSON context pack (<= ~2MB) for LLM analysis.

    Aggregates the last `hours` of selected streams, keeps slim column subsets,
    and caps rows per stream to `top_k` most recent.
    Returns output path.
    """
    # Normalize root: if default placeholder 'logs' is provided, use unified base
    logs_root = _unified_logs_root()
    if not root or str(root).strip().lower() == "logs":
        root = str(logs_root)
    cutoff = datetime.now(IST) - timedelta(hours=hours)
    # Supported streams and synonyms for structured emitters (non-gz/plain names)
    streams = [
        "market_ingest_log",
        "calibration_log",
        "ensemble_log",
        "execution_log",
        "costs_log",
        "pnl_equity_log",
    ]
    synonyms = {
        "market_ingest_log": ["market_ingest"],
        "calibration_log": ["calibration"],
        "pnl_equity_log": ["pnl_equity"],
        "execution_log": ["executions", "execution"],
        "costs_log": ["costs"],
        "ensemble_log": ["ensemble"],
    }
    records: Dict[str, List[Dict]] = {}
    root_path = pathlib.Path(root)
    frames_map: Dict[str, List[pd.DataFrame]] = {}
    for stream in streams:
        # Gather both gz and plain JSONL, and consider synonyms
        names = [stream] + synonyms.get(stream, [])
        globs = []
        for name in names:
            globs.extend(root_path.rglob(f"{name}.jsonl.gz"))
            globs.extend(root_path.rglob(f"{name}.jsonl"))
        if not globs:
            continue
        frames: List[pd.DataFrame] = []
        for g in globs:
            df = None
            pth = pathlib.Path(g)
            if str(pth).endswith(".jsonl.gz"):
                df = _read_jsonl_gz(pth)
            else:
                # Plain JSONL fallback
                try:
                    df = pd.read_json(pth, lines=True)
                except Exception:
                    df = None
            if df is None or "ts_ist" not in df:
                # Try to normalize columns to derive ts_ist/asset/bar_id
                if df is not None:
                    df = _normalize_df_columns(df)
                if df is None or "ts_ist" not in df:
                    continue
            try:
                df["ts_ist"] = pd.to_datetime(df["ts_ist"], errors="coerce")
                frames.append(df[df["ts_ist"] >= cutoff])
            except Exception:
                continue
        if not frames:
            continue
        dff = pd.concat(frames, ignore_index=True).sort_values("ts_ist")
        keep = [
            # common
            "ts_ist",
            "bar_id",
            "asset",
            # selected per-stream slim columns
            "mid",
            "spread_bps",
            "obi_10",
            "a",
            "b",
            "pred_cal_bps",
            "in_band_flag",
            "band_bps",
            "bandit_arm",
            "pred_stack_bps",
            "fill_px",
            "fill_qty",
            "slip_bps",
            "cost_bps_total",
            "pnl_total_usd",
            "equity_value",
            "realized_return_bps",
        ]
        keep = [c for c in keep if c in dff.columns]
        dff = dff[keep].tail(int(top_k))
        # compact timestamp strings
        try:
            dff["ts_ist"] = dff["ts_ist"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            pass
        frames_map[stream] = [dff]
        records[stream] = dff.to_dict(orient="records")

    # Optional overlay_status: not part of raw records (to keep pack size small),
    # but we use it for aggregate diagnostics if available.
    overlay_globs = []
    overlay_globs.extend(root_path.rglob("overlay_status.jsonl.gz"))
    overlay_globs.extend(root_path.rglob("overlay_status.jsonl"))
    overlay_frames: List[pd.DataFrame] = []
    for g in overlay_globs:
        df = _read_jsonl_gz(g)
        if df is None or "ts_ist" not in df:
            continue
        try:
            df["ts_ist"] = pd.to_datetime(df["ts_ist"], errors="coerce")
            overlay_frames.append(df[df["ts_ist"] >= cutoff])
        except Exception:
            continue

    # Build aggregate diagnostics and a short narrative
    diagnostics: Dict[str, Dict] = {}

    # Session overview
    try:
        # Count bars from any available stream (prefer ensemble or pnl_equity)
        def _count_rows(name: str) -> int:
            if name in records:
                return len(records[name])
            return 0
        bars_seen = max(_count_rows("ensemble_log"), _count_rows("pnl_equity_log"), _count_rows("market_ingest_log"))
        assets = list({rec.get("asset") for lst in records.values() for rec in lst if isinstance(rec, dict) and rec.get("asset") is not None})
        diagnostics["session_overview"] = {
            "hours": int(hours),
            "top_k": int(top_k),
            "bars_seen": int(bars_seen),
            "assets": assets,
            "generated_ist": ist_now(),
        }
    except Exception:
        diagnostics["session_overview"] = {"hours": int(hours), "top_k": int(top_k)}

    # PnL decomposition (from costs_log and pnl_equity_log)
    try:
        import numpy as _np
        df_cost = None
        if "costs_log" in frames_map:
            df_cost = pd.concat(frames_map["costs_log"], ignore_index=True)
        df_eq = None
        if "pnl_equity_log" in frames_map:
            df_eq = pd.concat(frames_map["pnl_equity_log"], ignore_index=True)
        totals = {}
        if df_eq is not None and len(df_eq) > 0:
            try:
                eq_vals = pd.to_numeric(df_eq.get("equity_value"), errors="coerce")
                totals["equity_last"] = float(eq_vals.dropna().iloc[-1]) if eq_vals.dropna().shape[0] > 0 else None
                # Max DD from equity within window
                if eq_vals.dropna().shape[0] > 1:
                    roll_max = eq_vals.cummax()
                    dd = (eq_vals - roll_max) / roll_max
                    totals["max_dd_pct"] = round(float(dd.min() * -100.0), 2)
            except Exception:
                pass
        if df_cost is not None and len(df_cost) > 0:
            c_bps = pd.to_numeric(df_cost.get("cost_bps_total"), errors="coerce")
            diagnostics["execution_quality"] = {
                "slip_bps_median": float(pd.to_numeric(df_cost.get("slip_bps"), errors="coerce").median(skipna=True)) if "slip_bps" in df_cost else None,
                "slip_bps_p90": float(pd.to_numeric(df_cost.get("slip_bps"), errors="coerce").quantile(0.9)) if "slip_bps" in df_cost else None,
                "cost_bps_total_median": float(c_bps.median(skipna=True)) if c_bps is not None else None,
                "cost_bps_total_p90": float(c_bps.quantile(0.9)) if c_bps is not None else None,
            }
            try:
                totals["fees_usd"] = float(pd.to_numeric(df_cost.get("fee_usd"), errors="coerce").sum()) if "fee_usd" in df_cost else None
                totals["slip_usd"] = float(pd.to_numeric(df_cost.get("slip_usd"), errors="coerce").sum()) if "slip_usd" in df_cost else None
                totals["impact_usd"] = float(pd.to_numeric(df_cost.get("impact_usd"), errors="coerce").sum()) if "impact_usd" in df_cost else None
                totals["cost_usd"] = float(pd.to_numeric(df_cost.get("cost_usd"), errors="coerce").sum()) if "cost_usd" in df_cost else None
            except Exception:
                pass
        diagnostics["pnl_decomposition"] = totals
    except Exception:
        pass

    # Calibration summary
    try:
        if "calibration_log" in frames_map:
            df_cal = pd.concat(frames_map["calibration_log"], ignore_index=True)
            inband = pd.to_numeric(df_cal.get("in_band_flag"), errors="coerce") if "in_band_flag" in df_cal else None
            pred_cal = pd.to_numeric(df_cal.get("pred_cal_bps"), errors="coerce") if "pred_cal_bps" in df_cal else None
            band_bps = pd.to_numeric(df_cal.get("band_bps"), errors="coerce") if "band_bps" in df_cal else None
            diagnostics["alpha_and_calibration"] = {
                "in_band_share": float(inband.mean()) if inband is not None and inband.size > 0 else None,
                "pred_cal_bps_median": float(pred_cal.median(skipna=True)) if pred_cal is not None else None,
                "band_bps_median": float(band_bps.median(skipna=True)) if band_bps is not None else None,
            }
    except Exception:
        pass

    # Overlay alignment summary (from overlay_status)
    try:
        if overlay_frames:
            dfo = pd.concat(overlay_frames, ignore_index=True)
            # conflict: if d5 and d15 have non-zero and differ
            def _conflict(row):
                ind = row.get("individual_signals")
                if isinstance(ind, dict):
                    d5 = int(((ind.get("5m") or {}).get("dir")) or 0)
                    d15 = int(((ind.get("15m") or {}).get("dir")) or 0)
                    return int(d5 != 0 and d15 != 0 and d5 != d15)
                return 0
            try:
                conflicts = dfo.apply(_conflict, axis=1)
                diagnostics["gating_and_alignment"] = {
                    "overlay_conflict_rate": float(conflicts.mean()) if conflicts.size > 0 else None,
                    "overlay_confidence_median": float(pd.to_numeric(dfo.get("confidence"), errors="coerce").median(skipna=True)) if "confidence" in dfo else None,
                }
            except Exception:
                pass
    except Exception:
        pass

    # Anomalies (top-N)
    try:
        anomalies: Dict[str, List[Dict]] = {}
        if "costs_log" in frames_map:
            dfc = pd.concat(frames_map["costs_log"], ignore_index=True)
            if "cost_bps_total" in dfc:
                top = dfc.sort_values(pd.to_numeric(dfc["cost_bps_total"], errors="coerce"), ascending=False).head(10)
                try:
                    top["ts_ist"] = pd.to_datetime(top["ts_ist"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                except Exception:
                    pass
                anomalies["by_cost_bps"] = top.to_dict(orient="records")
        diagnostics["anomalies"] = anomalies
    except Exception:
        pass

    # Narrative
    try:
        eq_last = diagnostics.get("pnl_decomposition", {}).get("equity_last")
        max_dd = diagnostics.get("pnl_decomposition", {}).get("max_dd_pct")
        slip_med = diagnostics.get("execution_quality", {}).get("slip_bps_median") if diagnostics.get("execution_quality") else None
        cost_med = diagnostics.get("execution_quality", {}).get("cost_bps_total_median") if diagnostics.get("execution_quality") else None
        inband_share = diagnostics.get("alpha_and_calibration", {}).get("in_band_share")
        overlay_conflict = diagnostics.get("gating_and_alignment", {}).get("overlay_conflict_rate") if diagnostics.get("gating_and_alignment") else None
        narrative = [
            f"Equity last: {eq_last}",
            f"Max DD %: {max_dd}",
            f"Median slip (bps): {slip_med}",
            f"Median total cost (bps): {cost_med}",
            f"In-band share: {inband_share}",
            f"Overlay conflict rate: {overlay_conflict}",
        ]
        diagnostics["narrative"] = "; ".join([str(x) for x in narrative if x is not None])
    except Exception:
        diagnostics["narrative"] = ""
    # If caller used the default relative 'llm_context/..', place it under the PAPER_TRADING_ROOT
    # next to logs, so all artifacts live under a single paper_trading_outputs folder.
    if out == "llm_context/context_pack.json.gz" or (not os.path.isabs(out) and out.startswith("llm_context")):
        out_path = logs_root.parent / out
    else:
        out_path = pathlib.Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    packed = {**records, "diagnostics": diagnostics}
    with gzip.open(out_path, "wb") as f:
        f.write(json.dumps(packed, separators=(",", ":")).encode("utf-8"))
    return str(out_path.resolve())


def _collect_all_stream_files(root_path: pathlib.Path) -> List[pathlib.Path]:
    """Return list of all *.jsonl and *.jsonl.gz under logs root."""
    files: List[pathlib.Path] = []
    files.extend(root_path.rglob("*.jsonl.gz"))
    files.extend(root_path.rglob("*.jsonl"))
    return files


def _parse_stream_name(path: pathlib.Path, logs_root: pathlib.Path) -> str:
    """Best-effort extraction of stream name from path.
    Expected structures:
      logs/<stream>/date=YYYY-..../asset=.../<stream>.jsonl[.gz]
      or arbitrary folders ending with <name>.jsonl[.gz]
    """
    try:
        rel = path.relative_to(logs_root)
    except Exception:
        rel = path.name
        return str(rel).split(".")[0]
    parts = list(rel.parts)
    # Prefer the first directory under logs as stream
    if parts:
        # if last filename is like foo.jsonl.gz -> stream is stem without .jsonl(.gz)
        fname = parts[-1]
        stem = str(fname)
        if stem.endswith(".jsonl.gz"):
            stem = stem[:-9]
        elif stem.endswith(".jsonl"):
            stem = stem[:-6]
        # sanity: if first folder equals stem, that's the stream
        if parts[0] == stem:
            return stem
        # else fall back to stem
        return stem
    return path.stem


def _read_any_jsonl(path: pathlib.Path) -> Optional[pd.DataFrame]:
    if str(path).endswith(".jsonl.gz"):
        return _read_jsonl_gz(path)
    try:
        return pd.read_json(path, lines=True)
    except Exception:
        return None


def _collect_stream_arrays(logs_root: pathlib.Path, hours: int, top_k: int) -> Dict[str, List[Dict]]:
    """Collect top_k recent rows per discovered stream within the last `hours`.
    Returns a dict: stream_name -> list[records].
    """
    all_files = _collect_all_stream_files(logs_root)
    cutoff = datetime.now(IST) - timedelta(hours=hours)
    arrays: Dict[str, List[Dict]] = {}
    stream_frames: Dict[str, List[pd.DataFrame]] = {}
    for p in all_files:
        df = _read_any_jsonl(p)
        if df is None or len(df) == 0:
            continue
        df = _normalize_df_columns(df)
        stream = _parse_stream_name(p, logs_root)
        # If we have a usable ts_ist column, filter by cutoff; else include as-is
        if "ts_ist" in df.columns:
            try:
                df["ts_ist"] = pd.to_datetime(df["ts_ist"], errors="coerce")
                df = df[df["ts_ist"] >= cutoff]
            except Exception:
                pass
        # Keep if any rows remain (or if no ts_ist at all)
        if len(df) == 0:
            continue
        stream_frames.setdefault(stream, []).append(df)
    for stream, frs in stream_frames.items():
        try:
            dff = pd.concat(frs, ignore_index=True).sort_values("ts_ist").tail(int(top_k))
            try:
                dff["ts_ist"] = pd.to_datetime(dff["ts_ist"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S%z")
            except Exception:
                pass
            arrays[stream] = dff.to_dict(orient="records")
        except Exception:
            continue
    return arrays


def build_llm_context_bundle(
    root: str = "logs",
    hours: int = 24,
    top_k: int = 500,
    out_zip: str = "llm_context/context_bundle.zip",
    include_arrays: bool = True,
    json_only_flat: bool = True,
) -> str:
    """Create a ZIP bundle with:
      - context_pack.json (uncompressed), identical to context_pack.json.gz content
      - raw_logs/ (all emission *.jsonl/.jsonl.gz files within the logs root)
      - arrays/<stream>.json (optional): top_k recent rows per stream as JSON arrays for easy pasting

    Returns absolute path to the created ZIP file.
    """
    import zipfile

    logs_root = _unified_logs_root()
    if not root or str(root).strip().lower() == "logs":
        root = str(logs_root)
    logs_root = pathlib.Path(root)

    # 1) Build or load the compact pack to embed as context_pack.json
    pack_gz_path = build_llm_context_pack(root=str(logs_root), hours=hours, top_k=top_k, out="llm_context/context_pack.json.gz")
    pack_gz_path = pathlib.Path(pack_gz_path)
    # Read JSON from gz to include an uncompressed copy
    with gzip.open(pack_gz_path, "rb") as f:
        pack_json_bytes = f.read()

    # 2) Collect raw log files
    all_files = _collect_all_stream_files(logs_root)

    # 3) Prepare arrays per stream (top_k, within hours cutoff)
    arrays: Dict[str, List[Dict]] = _collect_stream_arrays(logs_root, hours, top_k) if include_arrays else {}

    # 4) Write ZIP bundle next to logs (under llm_context)
    logs_base = _unified_logs_root()
    if out_zip == "llm_context/context_bundle.zip" or (not os.path.isabs(out_zip) and out_zip.startswith("llm_context")):
        out_zip_path = logs_base.parent / out_zip
    else:
        out_zip_path = pathlib.Path(out_zip)
    out_zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Always include the uncompressed compact pack
        zf.writestr("context_pack.json", pack_json_bytes)
        if json_only_flat:
            # Include only JSON files at the root (no folders)
            if include_arrays and arrays:
                try:
                    zf.writestr("all_streams.json", json.dumps(arrays, separators=(",", ":")).encode("utf-8"))
                except Exception:
                    pass
                for stream, recs in arrays.items():
                    try:
                        zf.writestr(f"{stream}.json", json.dumps(recs, separators=(",", ":")).encode("utf-8"))
                    except Exception:
                        continue
        else:
            # Legacy layout: arrays/ subfolder, raw_logs/ with original files, and README
            if include_arrays and arrays:
                for stream, recs in arrays.items():
                    try:
                        zf.writestr(f"arrays/{stream}.json", json.dumps(recs, separators=(",", ":")).encode("utf-8"))
                    except Exception:
                        continue
                try:
                    zf.writestr("all_streams.json", json.dumps(arrays, separators=(",", ":")).encode("utf-8"))
                except Exception:
                    pass
            # Add raw files preserving relative structure under raw_logs/
            for p in all_files:
                try:
                    rel = pathlib.Path(p).resolve()
                    try:
                        rel = rel.relative_to(logs_root)
                    except Exception:
                        rel = pathlib.Path(p).name
                    arcname = pathlib.Path("raw_logs") / rel
                    zf.write(p, arcname=str(arcname))
                except Exception:
                    continue
            # README (non-JSON) only in legacy mode
            readme = (
                "This bundle contains:\n"
                "- context_pack.json: a compact summary for LLMs (also available as .json.gz).\n"
                "- arrays/: per-stream top_k recent rows as JSON arrays (paste-friendly).\n"
                "- raw_logs/: original emission files (*.jsonl/.jsonl.gz) preserving folder structure.\n"
                f"Generated IST: {ist_now()}\n"
            )
            zf.writestr("README.txt", readme.encode("utf-8"))

    return str(out_zip_path.resolve())


def build_llm_paste_pack(
    root: str = "logs",
    hours: int = 24,
    top_k: int = 500,
    out: str = "llm_context/paste_pack.json.gz",
) -> str:
    """Build a single paste-friendly JSON(.gz) with no folder structure:
    {
      "generated_ist": "...",
      "hours": 24,
      "top_k": 500,
      "streams": {
         "market_ingest": [...],
         "signals": [...],
         ...
      }
    }
    """
    logs_root = _unified_logs_root()
    if not root or str(root).strip().lower() == "logs":
        root = str(logs_root)
    logs_root = pathlib.Path(root)
    arrays = _collect_stream_arrays(logs_root, hours, top_k)
    packed = {
        "generated_ist": ist_now(),
        "hours": int(hours),
        "top_k": int(top_k),
        "streams": arrays,
    }
    # Place output next to logs under llm_context by default
    out_path = logs_root.parent / out if (out == "llm_context/paste_pack.json.gz" or (not os.path.isabs(out) and out.startswith("llm_context"))) else pathlib.Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_path, "wb") as f:
        f.write(json.dumps(packed, separators=(",", ":")).encode("utf-8"))
    return str(out_path.resolve())


__all__ = [
    "ist_now",
    "bar_id_from_ts",
    "write_jsonl",
    "validate_file",
    "build_llm_context_pack",
    "build_llm_context_bundle",
    "build_llm_paste_pack",
]
