import hashlib
import os
import json
from typing import Any, Dict, Optional

from ops.log_emitter import get_emitter
# Prefer top-level ops.llm_logging; fallback to package-local live_demo.ops.llm_logging for robustness
try:
    # Enforces IST timestamps, bar_id, gzip partitions, and size caps
    from ops.llm_logging import write_jsonl  # type: ignore
except Exception:  # ImportError or environment path issues
    try:
        from live_demo.ops.llm_logging import write_jsonl  # type: ignore
    except Exception:
        # Last-resort no-op to avoid hard crashes; callers will simply not emit LLM logs
        def write_jsonl(topic: str, record: dict, asset: str | None = None):  # type: ignore
            return
from datetime import datetime, timezone, timedelta


def _hash8(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, default=str)
    except Exception:
        s = str(obj)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def build_event_id(ts: Optional[float], asset: str, topic: str, payload: Dict[str, Any]) -> str:
    ts_i = int(ts) if isinstance(ts, (int, float)) else 0
    return f"{ts_i}:{asset}:{topic}:{_hash8(payload)}"


class LogRouter:
    """Routes log events to configured sinks per topic.

    Sinks supported:
    - emitter: ops.log_emitter.LogEmitter (sanitized, structured)
    - llm: compact JSONL via ops.llm_logging.write_jsonl

    Topics mapping example (strings combined with '+'):
        {
          "signals": "emitter",
          "executions": "emitter+llm",
          "costs": "emitter",
          "health": "emitter",
          "ensemble": "llm",
          "equity": "llm"
        }
    """

    def __init__(self, logging_cfg: Dict[str, Any], bot_version: Optional[str] = None, base_root: Optional[str] = None):
        self.sinks = (logging_cfg or {}).get("sinks", {
            "sheets": True,
            "emitter": True,
            "llm_jsonl": True,
        })
        self.topics = (logging_cfg or {}).get("topics", {})
        self.bot_version = bot_version
        self.emit_base = base_root
        # LLM logs alongside emitter base, segregated per bot_version if provided
        if base_root:
            self.llm_root = (os.path.join(base_root, bot_version) if bot_version else base_root)
        else:
            self.llm_root = None

    def _enabled(self, sink: str) -> bool:
        # sink keys: emitter, llm
        if sink == "emitter":
            return bool(self.sinks.get("emitter", True))
        if sink == "llm":
            return bool(self.sinks.get("llm_jsonl", True))
        return False

    def _targets_for(self, topic: str) -> Dict[str, bool]:
        spec = str(self.topics.get(topic, "")).lower()
        return {
            "emitter": self._enabled("emitter") and ("emitter" in spec),
            "llm": self._enabled("llm") and ("llm" in spec),
        }

    # Ensemble
    def emit_ensemble(self, *, ts: Optional[float], asset: str, raw_preds: Dict[str, Any], meta: Dict[str, Any]):
        targets = self._targets_for("ensemble")
        event_id = build_event_id(ts, asset, "ensemble", {"raw": raw_preds, "meta": meta})
        if targets.get("emitter"):
            try:
                emitter = get_emitter(self.bot_version, base_dir=self.emit_base)
                # Attach event_id inside meta for traceability
                meta2 = dict(meta or {})
                meta2["event_id"] = event_id
                emitter.emit_ensemble(ts=ts, symbol=asset, raw_preds=raw_preds, meta=meta2)
            except Exception:
                pass
        if targets.get("llm"):
            try:
                # compact fields, include event_id
                write_jsonl("ensemble_log", {
                    "asset": asset,
                    "event_id": event_id,
                    "pred_stack_bps": round(10000.0 * float(raw_preds.get("s_model", 0.0)), 1),
                }, asset=asset, root=self.llm_root)
            except Exception:
                pass

    # Executions
    def emit_execution(self, *, ts: Optional[float], asset: str, exec_resp: Dict[str, Any], risk_state: Dict[str, Any], bar_id: Optional[int] = None):
        targets = self._targets_for("executions")
        event_id = build_event_id(ts, asset, "executions", {"exec": exec_resp, "risk": risk_state, "bar_id": bar_id})
        if targets.get("emitter"):
            try:
                # Attach event_id into exec_resp copy for traceability
                exec2 = dict(exec_resp or {})
                exec2["event_id"] = event_id
                emitter = get_emitter(self.bot_version, base_dir=self.emit_base)
                emitter.emit_execution(ts=ts, symbol=asset, exec_resp=exec2, risk_state=risk_state)
            except Exception:
                pass
        # Emit LLM execution log only when explicitly enabled for this topic
        if targets.get("llm"):
            try:
                tz_ist = timezone(timedelta(hours=5, minutes=30))
                decision_time_ist = datetime.now(tz=tz_ist).isoformat()
                rec = {
                    "asset": asset,
                    "event_id": event_id,
                    "decision_time_ist": decision_time_ist,
                    "exec_time_ist": decision_time_ist,
                    "bar_id_exec": bar_id,
                    "side": exec_resp.get("side"),
                    "order_type": exec_resp.get("order_type", "MARKET"),
                    "limit_px": exec_resp.get("limit_px"),
                    "fill_px": exec_resp.get("price"),
                    "fill_qty": exec_resp.get("qty"),
                    "slip_bps": exec_resp.get("slip_bps"),
                    "router": exec_resp.get("route", "BINANCE"),
                    "rejections": exec_resp.get("rejections", 0),
                    "ioc_ms": exec_resp.get("ioc_ms"),
                }
                write_jsonl("execution_log", rec, asset=asset, root=self.llm_root)
            except Exception:
                pass

    # Costs
    def emit_costs(self, *, ts: Optional[float], asset: str, costs: Dict[str, Any]):
        targets = self._targets_for("costs")
        event_id = build_event_id(ts, asset, "costs", costs)
        if targets.get("emitter"):
            try:
                costs2 = dict(costs or {})
                costs2["event_id"] = event_id
                emitter = get_emitter(self.bot_version, base_dir=self.emit_base)
                emitter.emit_costs(ts=ts, symbol=asset, costs=costs2)
            except Exception:
                pass
        if targets.get("llm"):
            try:
                write_jsonl("costs_log", {**costs, "asset": asset, "event_id": event_id}, asset=asset, root=self.llm_root)
            except Exception:
                pass

    # Health (emitter-only default)
    def emit_health(self, *, ts: Optional[float], asset: str, health: Dict[str, Any]):
        targets = self._targets_for("health")
        if targets.get("emitter"):
            try:
                emitter = get_emitter(self.bot_version, base_dir=self.emit_base)
                emitter.emit_health(ts=ts, symbol=asset, health=health)
            except Exception:
                pass

    # Equity / PnL (llm default)
    def emit_equity(self, *, asset: str, ts: Optional[float], pnl_total_usd: Optional[float], equity_value: Optional[float], realized_return_bps: Optional[float] = None):
        targets = self._targets_for("equity")
        payload = {
            "asset": asset,
            "pnl_total_usd": None if pnl_total_usd is None else float(pnl_total_usd),
            "equity_value": None if equity_value is None else float(equity_value),
            "realized_return_bps": None if realized_return_bps is None else float(realized_return_bps),
        }
        event_id = build_event_id(ts, asset, "equity", payload)
        if targets.get("llm"):
            try:
                write_jsonl("pnl_equity_log", {**payload, "event_id": event_id}, asset=asset, root=self.llm_root)
            except Exception:
                pass

    # Overlay status (llm default)
    def emit_overlay_status(self, *, ts: Optional[float], asset: str, status: Dict[str, Any]):
        targets = self._targets_for("overlay_status")
        payload = {**status, "asset": asset}
        event_id = build_event_id(ts, asset, "overlay_status", payload)
        if targets.get("llm"):
            try:
                write_jsonl("overlay_status", {**payload, "event_id": event_id}, asset=asset, root=self.llm_root)
            except Exception:
                pass

    # Alerts (llm default; router does not send Slack/Email here)
    def emit_alert(self, *, ts: Optional[float], asset: str, alert: Dict[str, Any]):
        targets = self._targets_for("alerts")
        payload = {**alert, "asset": asset}
        event_id = build_event_id(ts, asset, "alerts", payload)
        if targets.get("llm"):
            try:
                write_jsonl("alerts", {**payload, "event_id": event_id}, asset=asset, root=self.llm_root)
            except Exception:
                pass

    # Hyperliquid user fills (llm default; optional emitter)
    def emit_hyperliquid_fill(self, *, ts: Optional[float], asset: str, fill: Dict[str, Any]):
        targets = self._targets_for("hyperliquid_fills")
        # Maintain a simple, Sheets-compatible shape in the log as well
        payload = {
            "asset": asset,
            "ts": fill.get("ts"),
            "address": fill.get("address"),
            "coin": fill.get("coin"),
            "side": fill.get("side"),
            "price": fill.get("price"),
            "size": fill.get("size"),
        }
        event_id = build_event_id(ts, asset, "hyperliquid_fills", payload)
        if targets.get("emitter"):
            try:
                emitter = get_emitter(self.bot_version, base_dir=self.emit_base)
                fill2 = dict(fill or {})
                fill2["event_id"] = event_id
                emitter.emit_hyperliquid_fill(ts=ts, symbol=asset, fill=fill2)
            except Exception:
                pass

    # Unified Trade Summary (bridge log)
    def emit_trade_summary(self, *, ts: Optional[float], asset: str, summary: Dict[str, Any]):
        targets = self._targets_for("trade_summary")
        event_id = build_event_id(ts, asset, "trade_summary", summary)
        if targets.get("emitter"):
            try:
                emitter = get_emitter(self.bot_version, base_dir=self.emit_base)
                # Production emitter uses the dict directly
                summary2 = dict(summary or {})
                summary2["event_id"] = event_id
                # LogRouter supports both legacy and production emitters
                if hasattr(emitter, 'emit_trade_summary'):
                    emitter.emit_trade_summary(summary2)
                else:
                    # Fallback for simple LogEmitter
                    emitter._write("trade_summary", {"sanitized": summary2}, ts=ts)
            except Exception:
                pass
        if targets.get("llm"):
            try:
                write_jsonl("trade_summary", {**summary, "asset": asset, "event_id": event_id}, asset=asset, root=self.llm_root)
            except Exception:
                pass
