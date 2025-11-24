import json
import os
from datetime import datetime
import pytz
import pandas as pd

IST = pytz.timezone("Asia/Kolkata")


def ist_now():
    return datetime.now(IST).isoformat()


def write_jsonl(path: str, record: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


class LogEmitter:
    def __init__(self, config: dict):
        self.base_dir = config["logging"]["base_dir"]
        self.formats = config["logging"].get("formats", {})

    def validate_format(self, data: dict, format_type: str) -> dict:
        if format_type not in self.formats:
            return data

        required_fields = set(self.formats[format_type])
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValueError(
                f"Missing required fields for {format_type}: {missing_fields}"
            )

        return {k: v for k, v in data.items() if k in required_fields}

    def emit_market_data(self, data: dict):
        data["ts_ist"] = data.get("ts_ist") or ist_now()
        validated_data = self.validate_format(data, "market")
        write_jsonl(f"{self.base_dir}/market/market_data.jsonl", validated_data)

    def emit_signals(self, signals: dict):
        signals["ts_ist"] = signals.get("ts_ist") or ist_now()
        validated_signals = self.validate_format(signals, "signals")
        write_jsonl(f"{self.base_dir}/signals/signals.jsonl", validated_signals)

    def emit_ensemble(self, ensemble: dict):
        ensemble["ts_ist"] = ensemble.get("ts_ist") or ist_now()
        validated_ensemble = self.validate_format(ensemble, "ensemble")
        write_jsonl(f"{self.base_dir}/ensemble/ensemble.jsonl", validated_ensemble)

    def emit_execution(self, execution: dict):
        execution["ts_ist"] = execution.get("ts_ist") or ist_now()
        # Execution has dynamic fields, so we don't validate format
        write_jsonl(f"{self.base_dir}/execution/execution.jsonl", execution)

    def emit_health(self, health: dict):
        health["ts_ist"] = health.get("ts_ist") or ist_now()
        validated_health = self.validate_format(health, "health")
        write_jsonl(f"{self.base_dir}/health/health.jsonl", validated_health)

    def emit_alert(self, alert: dict):
        alert["ts_ist"] = alert.get("ts_ist") or ist_now()
        alert["level"] = alert.get("level", "INFO")
        write_jsonl(f"{self.base_dir}/alerts/alerts.jsonl", alert)


def get_partition_path(root: str, date: datetime):
    return f"{root}/date={date.date()}"


def sanitize_record(record: dict) -> dict:
    SENSITIVE_KEYS = {"api_key", "api_secret", "private_key"}
    return {k: "[REDACTED]" if k in SENSITIVE_KEYS else v for k, v in record.items()}
