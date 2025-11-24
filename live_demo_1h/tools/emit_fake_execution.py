"""
Emit a single execution_log record via the LogRouter LLM path.

Usage (PowerShell):
  python -u -m live_demo.tools.emit_fake_execution

Optional env vars:
  EXEC_ASSET   (default: BTCUSDT)
  EXEC_SIDE    (default: BUY)
  EXEC_PRICE   (default: 12345.67)
  EXEC_QTY     (default: 0.001)
"""
from __future__ import annotations

import os
from typing import Any, Dict

from live_demo.ops.log_router import LogRouter


def main() -> None:
    asset = os.environ.get("EXEC_ASSET", "BTCUSDT")
    side = os.environ.get("EXEC_SIDE", "BUY")
    price = float(os.environ.get("EXEC_PRICE", "12345.67"))
    qty = float(os.environ.get("EXEC_QTY", "0.001"))

    exec_resp: Dict[str, Any] = {
        "side": side,
        "order_type": "MARKET",
        "price": price,
        "qty": qty,
        "slip_bps": None,
        "route": "BINANCE",
        "rejections": 0,
        "ioc_ms": None,
    }

    # Use default sinks from config if present; otherwise defaults in LogRouter apply.
    router = LogRouter({
        "sinks": {"emitter": True, "llm_jsonl": True},
        "topics": {"executions": "emitter+llm"},
    })
    # ts: None to let router stamp IST time; bar_id: 0 for test
    router.emit_execution(ts=None, asset=asset, exec_resp=exec_resp, risk_state={"position": 0.0}, bar_id=0)
    print({"status": "ok", "asset": asset})


if __name__ == "__main__":
    main()
