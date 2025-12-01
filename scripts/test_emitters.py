#!/usr/bin/env python3
"""
Small test script to call ops.log_emitter and write a few demo events for 5m and default emitters.
It will write to paper_trading_outputs/<bot>/logs/...
"""
import sys, pathlib
# ensure repo root is on PYTHONPATH so 'ops' package is importable
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ops.log_emitter import get_emitter
import time

now = int(time.time() * 1000)

em = get_emitter('5m')
# Emit signals
em.emit_signals(now, 'BTCUSDT', {'close': 100.0}, {'pred_bps': 50.0}, {'dir': 1, 'alpha': 100.0}, 'A')
# Emit execution
em.emit_execution(now, 'BTCUSDT', {'side': 'BUY', 'qty':1.23, 'fill_price': 100.1, 'notional_usd': 123.5}, {'realized_pnl': -1.0})
# Emit a health metrics
em.emit_health(now, 'BTCUSDT', {'cpu': 1.0, 'mem': 50})
# Emit costs
em.emit_costs(now, 'BTCUSDT', {'trade_notional': 123.5, 'impact_bps': 5.0})
# Emit ensemble
em.emit_ensemble(now, 'BTCUSDT', {'raw': [1,2,3]})
# Calibration
em.emit_calibration({'fold':0, 'a': 0.1, 'b':0.001})

print('Emitted sample records to 5m emitter')

# Also emit a couple to default emitter
em2 = get_emitter('default')
em2.emit_signals(now, 'BTCUSDT', {'close': 100.0}, {'pred_bps': 25.0}, {'dir': 1, 'alpha': 100.0}, 'A')
print('Emitted to default emitter')

# And emit directly to the per-version logs directory so the backend's per-version readers pick it up
em_ver = get_emitter('5m', base_dir=str(ROOT / 'paper_trading_outputs' / '5m' / 'logs'))
em_ver.emit_signals(now, 'BTCUSDT', {'close': 999.0}, {'pred_bps': 123.0}, {'dir': 1, 'alpha': 5.0}, 'A')
print('Emitted to per-version 5m logs directory')
