"""Write lightweight heartbeat JSON for each bot to paper_trading_outputs/logs/<bot>/heartbeat/heartbeat.json

This is used by monitor_bots.py to detect liveness and stuck processes.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import pytz

try:
    from core.config import get_strategy_id, get_schema_version
except ImportError:
    # Fallback if core.config is not available
    def get_strategy_id():
        return "ensemble_1_0"
    def get_schema_version():
        return "v1"

IST = pytz.timezone("Asia/Kolkata")


def write_heartbeat(base_dir: str, bot_version: str | None = None, last_bar_id: int | None = None, last_trade_ts: float | None = None, last_error: str | None = None):
    """Write heartbeat JSON to file.
    
    Args:
        base_dir: Base directory for logs
        bot_version: Bot version (e.g., "5m", "1h", etc.)
        last_bar_id: Last bar ID processed
        last_trade_ts: Last trade timestamp
        last_error: Last error message
        
    Returns:
        str: Path to heartbeat file
    """
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