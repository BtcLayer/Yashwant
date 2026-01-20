"""Quick test for enhanced emitter"""
import sys
sys.path.insert(0, 'live_demo')

from ops.log_emitter import LogEmitter
import time

print("Testing enhanced emitter...")

emitter = LogEmitter()

# Test execution with new fields
exec_resp = {"side": "BUY", "qty": 0.001, "fill_price": 102500.0, "notional_usd": 102.5}
risk_state = {"target_position": 0.001, "realized_pnl": 0.0}

emitter.emit_execution(
    ts=time.time(),
    symbol="BTCUSDT",
    exec_resp=exec_resp,
    risk_state=risk_state,
    is_forced=False,
    is_dry_run=True
)
print("✓ Execution log emitted")

# Test health with new field
health_data = {"latency_ms": 45.2, "cpu": 15.5}
emitter.emit_health(
    ts=time.time(),
    symbol="BTCUSDT",
    health=health_data,
    loop_alive=True
)
print("✓ Health log emitted")

print("\n✅ Test complete!")
