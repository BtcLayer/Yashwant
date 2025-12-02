"""Simple heartbeat writer used by monitoring and smoke tests.

This writes a small JSON file into paper_trading_outputs/logs/<bot>/heartbeat/heartbeat.json
It intentionally does not change runtime behavior and is safe for 1.1.
"""
import json
import os
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


def write_heartbeat(root: str, bot_version: str = "default", last_bar_id=None, last_trade_ts=None) -> str:
    path = os.path.join(root, bot_version, "heartbeat", "heartbeat.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        from core.config import get_strategy_id, get_schema_version
        strategy_id = get_strategy_id()
        schema_version = get_schema_version()
    except Exception:
        strategy_id = "ensemble_1_0"
        schema_version = "v1"

    payload = {
        "ts_ist": datetime.now(IST).isoformat(),
        "strategy_id": strategy_id,
        "schema_version": schema_version,
        "last_bar_id": last_bar_id,
        "last_trade_ts": last_trade_ts,
    }

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)

    return path
"""Write lightweight heartbeat JSON for each bot to paper_trading_outputs/logs/<bot>/heartbeat/heartbeat.json

This is used by monitor_bots.py to detect liveness and stuck processes.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import pytz
from core.config import get_strategy_id, get_schema_version


IST = pytz.timezone("Asia/Kolkata")


def write_heartbeat(base_dir: str, bot_version: str | None = None, last_bar_id: int | None = None, last_trade_ts: float | None = None, last_error: str | None = None):
    base = Path(base_dir)
    if bot_version:
        root = base / bot_version
    else:
        root = base
    out_dir = root / "heartbeat"
    out_dir.mkdir(parents=True, exist_ok=True)
    hb = {
        "ts_ist": datetime.now(IST).isoformat(),
        "strategy_id": get_strategy_id(),
        "schema_version": get_schema_version(),
        "last_bar_id": last_bar_id,
        "last_trade_ts": last_trade_ts,
        "last_error": last_error,
    }
    path = out_dir / "heartbeat.json"
    # atomically overwrite
    tmp = out_dir / "heartbeat.json.tmp"
    tmp.write_text(json.dumps(hb), encoding="utf-8")
    tmp.replace(path)
    return str(path)
