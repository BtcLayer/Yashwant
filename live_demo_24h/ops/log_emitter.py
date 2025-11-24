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


def partitioned_path(root: str, ts_iso: str, fname: str) -> str:
    # ts_iso expected like 2025-10-23T12:34:56+05:30
    try:
        date = ts_iso.split("T", 1)[0]
    except Exception:
        date = datetime.now().strftime("%Y-%m-%d")
    d = os.path.join(root, f"date={date}")
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
        topic_dir = os.path.join(self.root, topic)
        os.makedirs(topic_dir, exist_ok=True)
        path = partitioned_path(topic_dir, ts_iso, f"{topic}.jsonl")
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
        payload = {
            "symbol": symbol,
            "features": sanitize(features),
            "model": sanitize(model_out),
            "decision": sanitize(decision),
            "cohort": sanitize(cohort),
        }
        self._write("signals", {"sanitized": payload}, ts=ts)

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
    ):
        payload = {
            "symbol": symbol,
            "exec": sanitize(exec_resp),
            "risk": sanitize(risk_state),
        }
        self._write("executions", {"sanitized": payload}, ts=ts)

    def emit_costs(self, *, ts: Optional[float], symbol: str, costs: Dict[str, Any]):
        payload = {"symbol": symbol, "costs": sanitize(costs)}
        self._write("costs", {"sanitized": payload}, ts=ts)

    def emit_health(self, *, ts: Optional[float], symbol: str, health: Dict[str, Any]):
        payload = {"symbol": symbol, "health": sanitize(health)}
        self._write("health", {"sanitized": payload}, ts=ts)

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
        """Emit pre-trade order intent (used for audit/attribution)."""
        try:
            symbol = record.get('asset') or record.get('symbol') or ''
            payload = {'symbol': symbol, 'order_intent': sanitize(record)}
            self._write('order_intent', {'sanitized': payload}, ts=record.get('ts'))
        except Exception:
            return

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


def get_emitter(root: Optional[str] = None) -> LogEmitter:
    """Return a process-wide emitter using the unified logs base.

    The optional 'root' argument is ignored to enforce a single sink at
    paper_trading_outputs/logs. If an emitter was previously created with a
    different root (from older runs), it will be replaced on next call.
    """
    global _GLOBAL
    # Compute the unified default base path (same as LogEmitter default)
    # Recompute default_base using the constructor logic (MetaStacker root or PAPER_TRADING_ROOT)
    try:
        tmp = LogEmitter(root=None)
        default_base = getattr(tmp, 'root', None) or ''
    except Exception:
        default_base = ''
    if _GLOBAL is None:
        _GLOBAL = LogEmitter(root=None)
    else:
        try:
            current_root = getattr(_GLOBAL, 'root', None)
            if not current_root or os.path.normpath(current_root) != default_base:
                _GLOBAL = LogEmitter(root=None)
        except Exception:
            _GLOBAL = LogEmitter(root=None)
    return _GLOBAL
