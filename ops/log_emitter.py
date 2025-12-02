"""Minimal log emitter for development."""


class LogEmitter:
    def __init__(self, bot_version=None, base_dir: str | None = None):
        import os
        import pathlib
        # Resolve to repo-local paper_trading_outputs, but honor PAPER_TRADING_ROOT
        # if it points to a subfolder within the repo's paper_trading_outputs (per-TF routing)
        here = pathlib.Path(__file__).resolve()  # <repo>/ops/log_emitter.py
        repo_root = here.parent.parent            # <repo>
        repo_paper = (repo_root / "paper_trading_outputs").resolve()
        if base_dir:
            base_path = pathlib.Path(base_dir).resolve()
            self.base_dir = str(base_path)
        else:
            env = os.environ.get("PAPER_TRADING_ROOT")
            if env:
                try:
                    env_path = pathlib.Path(env).resolve()
                    if str(env_path).startswith(str(repo_paper)):
                        pt_root = str(env_path)
                    else:
                        pt_root = str(repo_paper)
                except Exception:
                    pt_root = str(repo_paper)
            else:
                pt_root = str(repo_paper)
            base = os.path.join(pt_root, "logs")
            self.base_dir = os.path.join(base, bot_version) if bot_version else base

    def _write_jsonl(self, path, record):
        import os
        import json
        from datetime import datetime
        import pytz

        IST = pytz.timezone("Asia/Kolkata")

        # Ensure directory exists
        dir_path = os.path.dirname(path)
        if dir_path:  # Only create directory if path has a directory component
            os.makedirs(dir_path, exist_ok=True)

        # Add timestamp if not present
        if "ts_ist" not in record:
            record["ts_ist"] = datetime.now(IST).isoformat()

        # Inject minimal strategy metadata if not present (non-destructive)
        try:
            from core.config import get_strategy_id, get_schema_version

            if "strategy_id" not in record:
                record["strategy_id"] = get_strategy_id()
            if "schema_version" not in record:
                record["schema_version"] = get_schema_version()
        except Exception:
            # Keep write non-failing if core.config is not available
            pass

        # Write record
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def emit_ensemble(self, ts, symbol, raw_preds, meta=None):
        record = {"ts": ts, "symbol": symbol, "predictions": raw_preds}
        if meta:
            record["meta"] = meta
        self._write_jsonl(f"{self.base_dir}/ensemble/ensemble.jsonl", record)

    def emit_signals(self, ts, symbol, features, model_out, decision, cohort):
        record = {
            "ts": ts,
            "symbol": symbol,
            "features": features,
            "model_out": model_out,
            "decision": decision,
            "cohort": cohort,
        }
        self._write_jsonl(f"{self.base_dir}/signals/signals.jsonl", record)

    def emit_execution(self, ts, symbol, exec_resp, risk_state):
        record = {
            "ts": ts,
            "symbol": symbol,
            "execution": exec_resp,
            "risk_state": risk_state,
        }
        self._write_jsonl(f"{self.base_dir}/execution/execution.jsonl", record)

    def emit_health(self, ts, symbol, health):
        record = {"ts": ts, "symbol": symbol, "metrics": health}
        self._write_jsonl(f"{self.base_dir}/health/health.jsonl", record)

    def emit_repro(self, ts, symbol, repro):
        record = {"ts": ts, "symbol": symbol, "repro": repro}
        self._write_jsonl(f"{self.base_dir}/repro/repro.jsonl", record)

    def emit_costs(self, ts, symbol, costs):
        record = {"ts": ts, "symbol": symbol, "costs": costs}
        self._write_jsonl(f"{self.base_dir}/costs/costs.jsonl", record)

    def emit_order_intent(self, order_intent):
        """Emit order intent log"""
        self._write_jsonl(
            f"{self.base_dir}/order_intent/order_intent.jsonl", order_intent
        )

    def emit_feature_log(self, feature_log):
        """Emit feature log"""
        self._write_jsonl(f"{self.base_dir}/feature_log/feature_log.jsonl", feature_log)

    def emit_calibration(self, calibration_log):
        """Emit calibration log"""
        self._write_jsonl(
            f"{self.base_dir}/calibration/calibration.jsonl", calibration_log
        )


_emitters = {}


def _cache_key(bot_version: str, base_dir: str | None) -> str:
    # Use bot_version + normalized base_dir for uniqueness; base_dir may be None
    bd = str(base_dir) if base_dir else ""
    return f"{bot_version}::{bd}"


def get_emitter(bot_version=None, base_dir: str | None = None):
    """Get emitter for specific bot version or default.

    Caches emitters by (bot_version, base_dir) so tests and different runtime
    locations don't collide. This is additive and safe for 1.1.
    """
    if bot_version is None:
        bot_version = "default"

    key = _cache_key(bot_version, base_dir)
    if key not in _emitters:
        _emitters[key] = LogEmitter(bot_version, base_dir=base_dir)
    return _emitters[key]
