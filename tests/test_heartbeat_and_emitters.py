import json
import os
from pathlib import Path


def test_emitter_injects_strategy_metadata(tmp_path: Path, monkeypatch):
    # Use a temporary logs root so tests are hermetic
    logs_root = tmp_path / "logs"
    os.makedirs(logs_root, exist_ok=True)

    # Import runtime emitter
    from ops.log_emitter import get_emitter

    # Ensure env vars are set for test
    monkeypatch.setenv("STRATEGY_ID", "ensemble_test")
    monkeypatch.setenv("SCHEMA_VERSION", "v1-test")

    emitter = get_emitter(bot_version="testbot", base_dir=str(logs_root / "testbot"))

    # Emit a simple signal
    emitter.emit_signals(1, "BTCUSDT", {"close": 100}, {"pred": 1.0}, {"dir":1}, {"pros":0})

    p = logs_root / "testbot" / "signals" / "signals.jsonl"
    assert p.exists(), f"signals file missing at {p}"

    # Read the last line and check metadata
    with p.open('r', encoding='utf-8') as fh:
        lines = [l.strip() for l in fh if l.strip()]
    assert lines, "no lines written to signals file"

    rec = json.loads(lines[-1])
    assert rec.get("strategy_id") == "ensemble_test"
    assert rec.get("schema_version") == "v1-test"
import json
import os
from pathlib import Path

import pytest


def test_write_heartbeat_and_emit_signal(tmp_path: Path):
    # set up temporary logs root
    logs_root = tmp_path / "logs"
    os.makedirs(logs_root, exist_ok=True)

    # Write heartbeat
    from ops.heartbeat import write_heartbeat

    hb_path = write_heartbeat(str(logs_root), bot_version="testbot", last_bar_id=1)
    assert Path(hb_path).exists()
    data = json.loads(Path(hb_path).read_text(encoding="utf-8"))
    assert "strategy_id" in data
    assert "schema_version" in data

    # Use repo-level emitter to write a signals record into tmp logs
    from ops.log_emitter import get_emitter

    # Use per-bot base_dir so files are written under logs/testbot/**
    em = get_emitter(bot_version="testbot", base_dir=str(logs_root / 'testbot'))
    # Emit a simple signal
    em.emit_signals(1234567890, "BTCUSDT", {"close": 100}, {"s_model": 0.1}, {"dir": 1, "alpha": 0.5}, {"pros": 0})

    # Check file exists and contains strategy metadata
    p = Path(str(logs_root)) / "testbot" / "signals" / "signals.jsonl"
    assert p.exists(), f"signals file missing at {p}"
    # read last line
    with p.open('r', encoding='utf-8') as fh:
        lines = [l.strip() for l in fh if l.strip()]
    assert lines, "no lines written to signals file"
    rec = json.loads(lines[-1])
    # the emitter should have added strategy_id and schema_version
    assert "strategy_id" in rec and "schema_version" in rec
