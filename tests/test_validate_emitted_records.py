import json
from pathlib import Path

import pytest

from scripts.validate_emitted_records import validate_logs


def _write_signals(tmp_path: Path, record: dict) -> Path:
    path = tmp_path / "tf" / "logs" / "tf" / "signals" / "signals.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return path


def _base_record() -> dict:
    return {
        "ts": 1234567890,
        "symbol": "BTCUSDT",
        "features": {"close": 100.0},
        "model_out": {"s_model": 0.1},
        "decision": {"dir": 1, "alpha": 0.5},
        "cohort": {"pros": 0.2},
        "strategy_id": "test_id",
        "schema_version": "v1",
    }


def test_validate_logs_pass(tmp_path: Path):
    _write_signals(tmp_path, _base_record())
    issues = validate_logs(tmp_path, strict=False)
    assert issues == 0


def test_validate_logs_strict_failure(tmp_path: Path):
    record = _base_record()
    record.pop("strategy_id")
    _write_signals(tmp_path, record)
    with pytest.raises(SystemExit):
        validate_logs(tmp_path, strict=True)
    # Non-strict returns issue count but does not raise
    issues = validate_logs(tmp_path, strict=False)
    assert issues == 1
