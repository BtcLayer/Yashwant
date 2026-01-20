import json
import os
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable, Optional

SENSITIVE_KEYS = {"api_key", "api_secret", "secret", "password", "creds_json", "token"}


def _hash_val(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()[:16]


def sanitize(obj: Any) -> Any:
    """Recursively sanitize a JSON-serializable object by redacting sensitive keys and hashing identifiers.

    Keeps types simple (dict, list, primitives)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k and isinstance(k, str) and k.lower() in SENSITIVE_KEYS:
                out[k] = "<REDACTED>"
            elif (
                k
                and isinstance(k, str)
                and (
                    "key" in k.lower()
                    or "secret" in k.lower()
                    or "token" in k.lower()
                    or "account" in k.lower()
                )
            ):
                try:
                    out[k] = _hash_val(str(v)) if v is not None else None
                except Exception:
                    out[k] = "<HASH_FAIL>"
            else:
                out[k] = sanitize(v)
        return out
    elif isinstance(obj, (list, tuple)):
        return [sanitize(x) for x in obj]
    else:
        # primitives
        return obj


def _ts_iso_ist(ts: Optional[float]) -> str:
    try:
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        if ts is None:
            return datetime.now(tz=tz_ist).isoformat()
        t = float(ts)
        if t > 1e12:
            dt = datetime.fromtimestamp(t / 1000.0, tz=timezone.utc).astimezone(tz_ist)
        else:
            dt = datetime.fromtimestamp(t, tz=timezone.utc).astimezone(tz_ist)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def partitioned_path(root: str, ts_iso: str, fname: str, asset: Optional[str] = None) -> str:
    """Build partitioned path: {root}/date=YYYY-MM-DD/asset={symbol}/{fname}"""
    # ts_iso expected like 2025-10-23T12:34:56+05:30
    try:
        date = ts_iso.split("T", 1)[0]
    except Exception:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Build path with asset partition
    if asset:
        d = os.path.join(root, f"date={date}", f"asset={asset}")
    else:
        d = os.path.join(root, f"date={date}", "asset=UNKNOWN")
    
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, fname)


class LogEmitter:
    """Simple file-based JSONL emitter.

    Writes to <base>/<topic>/date=YYYY-MM-DD/*.jsonl
    Default base unified to paper_trading_outputs/logs.
    """

    def __init__(self, root: Optional[str] = None):
        """Unify default destination to MetaStacker/paper_trading_outputs/logs.

        Priority:
          1) PAPER_TRADING_ROOT env var (absolute or relative)
          2) MetaStacker root (parent of repo) / paper_trading_outputs/logs
        """
        # Env override
        pt_root = os.environ.get('PAPER_TRADING_ROOT')
        if pt_root:
            try:
                pt_root = os.path.abspath(pt_root)
            except Exception:
                pass
            default_base = os.path.join(pt_root, 'logs')
        else:
            # Compute MetaStacker root (repo parent)
            ops_dir = os.path.dirname(__file__)                 # .../MetaStackerBandit/live_demo/ops
            live_demo_dir = os.path.dirname(ops_dir)            # .../MetaStackerBandit/live_demo
            repo_root = os.path.dirname(live_demo_dir)          # .../MetaStackerBandit
            metastacker_root = os.path.dirname(repo_root)       # .../MetaStacker
            default_base = os.path.normpath(
                os.path.join(metastacker_root, 'paper_trading_outputs', 'logs')
            )
        base = root or default_base
        self.root = os.path.abspath(base)

    def _write(
        self, topic: str, payload: Dict[str, Any], ts: Optional[float] = None
    ) -> None:
        ts_iso = _ts_iso_ist(ts)
        payload = dict(payload)
        payload.setdefault("ts_iso", ts_iso)
        payload.setdefault("ts", ts)
        payload["sanitized"] = sanitize(payload.get("sanitized", payload))
        
        # Extract symbol/asset for partitioning
        symbol = payload.get("symbol") or payload.get("asset") or "UNKNOWN"
        
        topic_dir = os.path.join(self.root, topic)
        os.makedirs(topic_dir, exist_ok=True)
        path = partitioned_path(topic_dir, ts_iso, f"{topic}.jsonl", asset=symbol)
        # Append JSONL
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # Best-effort only; don't raise to avoid crashing the bot
            return

    def emit_signals(
        self,
        *,
        ts: Optional[float],
        symbol: str,
        features: Dict[str, Any],
        model_out: Dict[str, Any],
        decision: Dict[str, Any],
        cohort: Dict[str, Any],
    ):
        """Emit signals log with flattened structure for easier model evaluation."""
        # Extract model predictions to top level
        p_up = model_out.get('p_up')
        p_down = model_out.get('p_down')
        p_neutral = model_out.get('p_neutral')
        s_model = model_out.get('s_model')
        
        # Calculate derived fields
        p_non_neutral = None
        conf_dir = None
        strength = None
        
        if p_up is not None and p_down is not None and p_neutral is not None:
            p_non_neutral = float(p_up) + float(p_down)
            conf_dir = max(float(p_up), float(p_down))
            strength = abs(float(p_up) - float(p_down))
        
        # Extract decision fields
        decision_dir = decision.get('dir')
        decision_alpha = decision.get('alpha')
        decision_details = decision.get('details', {}) if isinstance(decision, dict) else {}
        
        # Determine selected arm and action
        selected_arm = decision_details.get('chosen') or decision_details.get('model_source') or 'unknown'
        
        # Map direction to action
        raw_action = None
        final_action = None
        if decision_dir is not None:
            if decision_dir > 0:
                raw_action = 'BUY'
                final_action = 'BUY'
            elif decision_dir < 0:
                raw_action = 'SELL'
                final_action = 'SELL'
            else:
                raw_action = 'HOLD'
                final_action = 'HOLD'
        
        # Flatten structure for schema compliance and easier querying
        payload = {
            "symbol": symbol,
            
            # Model predictions (flattened - REQUIRED for evaluation)
            "p_up": p_up,
            "p_down": p_down,
            "p_neutral": p_neutral,
            "s_model": s_model,
            
            # Derived model metrics (flattened)
            "p_non_neutral": p_non_neutral,
            "conf_dir": conf_dir,
            "strength": strength,
            
            # Decision fields (flattened - REQUIRED for evaluation)
            "selected_arm": selected_arm,
            "raw_action": raw_action,
            "final_action": final_action,
            "decision_dir": decision_dir,
            "decision_alpha": decision_alpha,
            
            # Cohort signals (flattened)
            "cohort_pros": cohort.get('pros') if isinstance(cohort, dict) else None,
            "cohort_amateurs": cohort.get('amateurs') if isinstance(cohort, dict) else None,
            "cohort_mood": cohort.get('mood') if isinstance(cohort, dict) else None,
            
            # Optional metadata
            "decision_tf": "5m",  # Default timeframe, can be parameterized later
            
            # Keep original nested structures for backward compatibility
            "features": sanitize(features),
            "model": sanitize(model_out),
            "decision": sanitize(decision),
            "cohort": sanitize(cohort),
        }
        self._write("signals", payload, ts=ts)

    def emit_ensemble(
        self,
        *,
        ts: Optional[float],
        symbol: str,
        raw_preds: Dict[str, Any],
        meta: Dict[str, Any],
    ):
        payload = {
            "symbol": symbol,
            "preds": sanitize(raw_preds),
            "meta": sanitize(meta),
        }
        self._write("ensemble", {"sanitized": payload}, ts=ts)

    def emit_execution(
        self,
        *,
        ts: Optional[float],
        symbol: str,
        exec_resp: Dict[str, Any],
        risk_state: Dict[str, Any],
        is_forced: bool = False,
        is_dry_run: bool = True,
    ):
        """
        Emit execution log with flattened structure.

        Args:
            is_forced: True if this is a forced/smoke-test trade, False if organic model trade
            is_dry_run: True if paper trading, False if live trading
        """
        # Flatten execution details to top level for easier querying
        payload = {
            "symbol": symbol,
            "is_forced": is_forced,  # Critical: separates smoke tests from real trades
            "is_dry_run": is_dry_run,  # Critical: separates paper from live trading

            # Execution details (flattened)
            "side": exec_resp.get("side"),
            "qty": exec_resp.get("qty"),
            "price": exec_resp.get("fill_price") or exec_resp.get("price"),
            "notional_usd": exec_resp.get("notional_usd"),
            "order_id": exec_resp.get("order_id"),
            "result": exec_resp.get("result"),

            # Risk state (flattened)
            "target_position": risk_state.get("target_position"),
            "realized_pnl": risk_state.get("realized_pnl"),
            "unrealized_pnl": risk_state.get("unrealized_pnl"),

            # Keep original nested structures for backward compatibility
            "exec_resp": sanitize(exec_resp),
            "risk_state": sanitize(risk_state),
        }
        self._write("execution", payload, ts=ts)

    def emit_costs(self, *, ts: Optional[float], symbol: str, costs: Dict[str, Any]):
        """Emit costs log with flattened structure for easier analysis."""
        # Flatten cost fields to top level for schema compliance and easier querying
        payload = {
            "symbol": symbol,
            
            # Required fields (flattened)
            "notional_usd": costs.get("trade_notional") or costs.get("notional_usd"),
            "total_cost_usd": costs.get("cost_usd") or costs.get("total_cost_usd"),
            
            # Optional USD components (flattened)
            "fee_usd": costs.get("fee_usd"),
            "slippage_usd": costs.get("slip_usd") or costs.get("slippage_usd"),
            "impact_usd": costs.get("impact_usd"),
            
            # Optional basis points components (flattened)
            "fee_bps": costs.get("fee_bps"),
            "slippage_bps": costs.get("slip_bps") or costs.get("slippage_bps"),
            "impact_bps": costs.get("impact_bps"),
            "cost_bps": costs.get("cost_bps_total") or costs.get("cost_bps"),
            
            # Additional metadata
            "cost_model_version": costs.get("cost_model_version"),
            
            # Keep original nested structure for backward compatibility
            "costs": sanitize(costs),
        }
        self._write("costs", payload, ts=ts)

    def emit_health(self, *, ts: Optional[float], symbol: str, health: Dict[str, Any], loop_alive: bool = True):
        """Emit health heartbeat with flattened structure."""
        payload = {
            "symbol": symbol,
            "loop_alive": loop_alive,  # Required by schema
            
            # Flatten common health metrics
            "latency_ms": health.get("latency_ms"),
            "last_kline_ts": health.get("last_kline_ts"),
            "data_freshness_ok": health.get("data_freshness_ok"),
            
            # Add missing fields for complete schema compliance
            "funding_ts": health.get("funding_ts"),
            "fills_queue_depth": health.get("fills_queue_depth") or health.get("queue_depth") or 0,
            
            # Optional component status fields
            "model_loaded": health.get("model_loaded"),
            "exchange_connected": health.get("exchange_connected"),
            
            # Keep full health dict for backward compatibility
            "health": sanitize(health),
        }
        self._write("health", payload, ts=ts)

    def emit_hyperliquid_fill(self, *, ts: Optional[float], symbol: str, fill: Dict[str, Any]):
        """Emit a single Hyperliquid user fill (drained) in a compact, Sheets-compatible shape.

        Expected keys in 'fill': ts, address, coin, side, price, size
        """
        try:
            payload = {
                'symbol': symbol,
                'fill': sanitize({
                    'ts': fill.get('ts'),
                    'address': fill.get('address'),
                    'coin': fill.get('coin'),
                    'side': fill.get('side'),
                    'price': fill.get('price'),
                    'size': fill.get('size'),
                })
            }
            self._write('hyperliquid', {'sanitized': payload}, ts=ts)
        except Exception:
            # Best-effort only
            return

    def emit_order_intent(self, record: Dict[str, Any]):
        """Emit pre-trade order intent with flattened structure for easier veto analysis."""
        try:
            symbol = record.get('asset') or record.get('symbol') or ''
            
            # Extract intent fields
            side = record.get('side', 'HOLD')
            intent_action = side  # BUY/SELL/HOLD
            
            # Map side to direction
            intent_dir = 0
            if side == 'BUY':
                intent_dir = 1
            elif side == 'SELL':
                intent_dir = -1
            
            # Extract strength/alpha
            intent_strength = record.get('signal_strength') or record.get('intent_qty', 0.0)
            
            # Extract veto tracking fields
            veto_primary = record.get('veto_reason_primary')
            veto_secondary = record.get('veto_reason_secondary')
            guard_details = record.get('guard_details', {})
            
            # Extract checks/vetoes
            reason_codes = record.get('reason_codes', {})
            checks_passed = reason_codes
            vetoes_triggered = {k: not v for k, v in reason_codes.items() if not v}
            
            # Flatten structure for schema compliance
            payload = {
                "symbol": symbol,
                
                # Required intent fields (flattened)
                "intent_action": intent_action,
                "intent_dir": intent_dir,
                "intent_strength": intent_strength,
                
                # Veto tracking (flattened)
                "veto_reason_primary": veto_primary,
                "veto_reason_secondary": veto_secondary,
                "guard_details": guard_details,
                
                # Checks and vetoes (flattened)
                "checks_passed": checks_passed,
                "vetoes_triggered": vetoes_triggered,
                
                # Optional fields (flattened)
                "bar_id_decision": record.get('bar_id_decision'),
                "intent_qty": record.get('intent_qty'),
                "intent_notional": record.get('intent_notional'),
                "signal_strength": record.get('signal_strength'),
                "model_confidence": record.get('model_confidence'),
                "risk_score": record.get('risk_score'),
                "market_conditions": record.get('market_conditions'),
                "reason_codes": reason_codes,
                
                # Keep original nested structure for backward compatibility
                "order_intent": sanitize(record),
            }
            self._write('order_intent', payload, ts=record.get('ts'))
        except Exception:
            return

    def emit_pnl_equity(
        self,
        *,
        ts: Optional[float],
        symbol: str,
        equity_value: float,
        pnl_total_usd: float,
        realized_pnl_usd: Optional[float] = None,
        unrealized_pnl_usd: Optional[float] = None,
        realized_return_bps: Optional[float] = None,
        position_qty: Optional[float] = None,
        position_avg_px: Optional[float] = None,
        current_price: Optional[float] = None,
        starting_equity: Optional[float] = None,
        peak_equity: Optional[float] = None,
        drawdown_pct: Optional[float] = None,
    ):
        """Emit PnL and equity log with flattened structure and auto-calculated metrics."""
        # Calculate derived fields if not provided
        drawdown_usd = None
        return_pct = None
        return_usd = None
        
        if peak_equity is not None and equity_value is not None:
            drawdown_usd = peak_equity - equity_value
            if drawdown_pct is None and peak_equity > 0:
                drawdown_pct = 100.0 * (peak_equity - equity_value) / peak_equity
        
        if starting_equity is not None and equity_value is not None and starting_equity > 0:
            return_usd = equity_value - starting_equity
            return_pct = 100.0 * (equity_value - starting_equity) / starting_equity
        
        payload = {
            "symbol": symbol,
            
            # Required fields
            "equity_value": equity_value,
            "pnl_total_usd": pnl_total_usd,
            
            # PnL breakdown
            "realized_pnl_usd": realized_pnl_usd,
            "unrealized_pnl_usd": unrealized_pnl_usd,
            "realized_return_bps": realized_return_bps,
            
            # Position info
            "position_qty": position_qty,
            "position_avg_px": position_avg_px,
            "current_price": current_price,
            
            # Equity tracking
            "starting_equity": starting_equity,
            "peak_equity": peak_equity,
            
            # Risk metrics (auto-calculated)
            "drawdown_pct": drawdown_pct,
            "drawdown_usd": drawdown_usd,
            "return_pct": return_pct,
            "return_usd": return_usd,
        }
        self._write("pnl_equity", payload, ts=ts)

    def emit_overlay(
        self,
        *,
        ts: Optional[float],
        symbol: str,
        bar_id: int,
        confidence: float,
        alignment_rule: str,
        chosen_timeframes: list = None,
        individual_signals: Dict[str, Any] = None,
        overlay_dir: Optional[int] = None,
        overlay_alpha: Optional[float] = None,
    ):
        """Emit overlay status log with flattened structure and derived metrics."""
        chosen_timeframes = chosen_timeframes or []
        individual_signals = individual_signals or {}
        
        # Calculate derived fields
        num_timeframes = len(chosen_timeframes)
        
        # Calculate agreement percentage
        agreement_pct = None
        if individual_signals and num_timeframes > 0:
            directions = [sig.get('dir', 0) for sig in individual_signals.values()]
            if directions:
                most_common_dir = max(set(directions), key=directions.count)
                agreement_count = sum(1 for d in directions if d == most_common_dir)
                agreement_pct = 100.0 * agreement_count / len(directions)
        
        # Find strongest and weakest timeframes
        strongest_timeframe = None
        weakest_timeframe = None
        conflicting_timeframes = []
        
        if individual_signals:
            # Find strongest by alpha
            max_alpha = -1
            min_alpha = 2
            for tf, sig in individual_signals.items():
                alpha = abs(sig.get('alpha', 0.0))
                if alpha > max_alpha:
                    max_alpha = alpha
                    strongest_timeframe = tf
                if alpha < min_alpha:
                    min_alpha = alpha
                    weakest_timeframe = tf
            
            # Find conflicting (opposite direction from overlay)
            if overlay_dir is not None and overlay_dir != 0:
                for tf, sig in individual_signals.items():
                    sig_dir = sig.get('dir', 0)
                    if sig_dir != 0 and sig_dir != overlay_dir:
                        conflicting_timeframes.append(tf)
        
        payload = {
            "symbol": symbol,
            
            # Required fields
            "bar_id": bar_id,
            "confidence": confidence,
            "alignment_rule": alignment_rule,
            
            # Overlay result
            "chosen_timeframes": chosen_timeframes,
            "overlay_dir": overlay_dir,
            "overlay_alpha": overlay_alpha,
            
            # Derived metrics
            "num_timeframes": num_timeframes,
            "agreement_pct": agreement_pct,
            "strongest_timeframe": strongest_timeframe,
            "weakest_timeframe": weakest_timeframe,
            "conflicting_timeframes": conflicting_timeframes if conflicting_timeframes else None,
            
            # Individual signals (nested for detail)
            "individual_signals": individual_signals,
        }
        self._write("overlay", payload, ts=ts)

    def emit_feature_log(self, record: Dict[str, Any]):
        """Emit compact feature snapshot for a bar (debug/analysis)."""
        try:
            symbol = record.get('asset') or record.get('symbol') or ''
            payload = {'symbol': symbol, 'feature_log': sanitize(record)}
            self._write('feature_log', {'sanitized': payload}, ts=record.get('ts'))
        except Exception:
            return

    def emit_calibration(self, record: Dict[str, Any]):
        """Emit model calibration diagnostics (a, b, realized)."""
        try:
            symbol = record.get('asset') or record.get('symbol') or ''
            payload = {'symbol': symbol, 'calibration': sanitize(record)}
            self._write('calibration', {'sanitized': payload}, ts=record.get('ts'))
        except Exception:
            return

    def emit_repro(self, *, ts: Optional[float] = None, symbol: str = '', repro: Dict[str, Any]):
        """Emit reproducibility/config snapshot for this session."""
        try:
            payload = {'symbol': symbol, 'repro': sanitize(repro)}
            self._write('repro', {'sanitized': payload}, ts=ts)
        except Exception:
            return


_GLOBAL: Optional[LogEmitter] = None
_GLOBAL_ROOT: Optional[str] = None


def get_emitter(bot_version: Optional[str] = None, base_dir: Optional[str] = None) -> LogEmitter:
    """Return a process-wide emitter using the specified base directory.
    
    If base_dir is provided, it forces the emitter to use that root.
    """
    global _GLOBAL, _GLOBAL_ROOT
    
    target_root = base_dir
    
    if _GLOBAL is None or _GLOBAL_ROOT != target_root:
        _GLOBAL = LogEmitter(root=target_root)
        _GLOBAL_ROOT = target_root
        
    return _GLOBAL
