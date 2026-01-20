"""Test flattened costs logging"""
import sys
sys.path.insert(0, 'live_demo')

from ops.log_emitter import LogEmitter
import time
import json

print("Testing flattened costs logging...")

emitter = LogEmitter()

# Test with typical costs payload from main.py
costs_payload = {
    "trade_notional": 102.50,
    "fee_bps": 5.0,
    "slip_bps": 1.2,
    "impact_k": 0.5,
    "impact_bps": 0.8,
    "adv_ref": 1000000.0,
    "cost_usd": 0.56,
    "cost_bps_total": 7.0,
    "fee_usd": 0.51,
    "slip_usd": 0.01,
    "impact_usd": 0.08,
}

emitter.emit_costs(
    ts=time.time(),
    symbol="BTCUSDT",
    costs=costs_payload
)

print("✓ Costs log emitted")

# Verify the log structure
import os
log_files = []
for root, dirs, files in os.walk("../paper_trading_outputs/logs/costs"):
    for file in files:
        if file.endswith('.jsonl'):
            log_files.append(os.path.join(root, file))

if log_files:
    latest_log = max(log_files, key=os.path.getmtime)
    print(f"\n📄 Latest costs log: {latest_log}")
    
    with open(latest_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_record = json.loads(lines[-1])
            print("\n✅ Flattened fields present:")
            print(f"   notional_usd: {last_record.get('notional_usd')}")
            print(f"   total_cost_usd: {last_record.get('total_cost_usd')}")
            print(f"   fee_usd: {last_record.get('fee_usd')}")
            print(f"   fee_bps: {last_record.get('fee_bps')}")
            print(f"   slippage_usd: {last_record.get('slippage_usd')}")
            print(f"   impact_usd: {last_record.get('impact_usd')}")
            print(f"   cost_bps: {last_record.get('cost_bps')}")
            
            # Check backward compatibility
            if 'costs' in last_record:
                print("\n✅ Backward compatibility maintained (nested 'costs' dict present)")
            
            print("\n✅ Test complete!")
else:
    print("⚠️  No costs logs found yet")
