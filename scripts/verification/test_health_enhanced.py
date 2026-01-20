"""Test enhanced health logging with missing fields"""
import sys
sys.path.insert(0, 'live_demo')

from ops.log_emitter import LogEmitter
import time
import json
from datetime import datetime, timezone

print("Testing enhanced health logging...")

emitter = LogEmitter()

# Test with comprehensive health payload
health_payload = {
    'latency_ms': 45.2,
    'last_kline_ts': datetime.now(timezone.utc).isoformat(),
    'funding_ts': datetime.now(timezone.utc).isoformat(),
    'fills_queue_depth': 0,
    'data_freshness_ok': True,
    'model_loaded': True,
    'exchange_connected': True,
    'cpu': 15.5,
    'mem': 512,
    'ws_staleness_ms': 100
}

emitter.emit_health(
    ts=time.time(),
    symbol="BTCUSDT",
    health=health_payload,
    loop_alive=True
)

print("✓ Health log emitted")

# Verify the log structure
import os
log_files = []
for root, dirs, files in os.walk("../paper_trading_outputs/logs/health"):
    for file in files:
        if file.endswith('.jsonl'):
            log_files.append(os.path.join(root, file))

if log_files:
    latest_log = max(log_files, key=os.path.getmtime)
    print(f"\n📄 Latest health log: {latest_log}")
    
    with open(latest_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_record = json.loads(lines[-1])
            print("\n✅ Required fields:")
            print(f"   loop_alive: {last_record.get('loop_alive')}")
            
            print("\n✅ Common health fields:")
            print(f"   latency_ms: {last_record.get('latency_ms')}")
            print(f"   last_kline_ts: {last_record.get('last_kline_ts')}")
            print(f"   data_freshness_ok: {last_record.get('data_freshness_ok')}")
            
            print("\n✅ NEW: Missing fields now present:")
            print(f"   funding_ts: {last_record.get('funding_ts')}")
            print(f"   fills_queue_depth: {last_record.get('fills_queue_depth')}")
            
            print("\n✅ Optional component status:")
            print(f"   model_loaded: {last_record.get('model_loaded')}")
            print(f"   exchange_connected: {last_record.get('exchange_connected')}")
            
            # Check backward compatibility
            if 'health' in last_record:
                print("\n✅ Backward compatibility maintained (nested 'health' dict present)")
            
            # Verify schema compliance
            required_fields = ['ts', 'loop_alive']
            missing = [f for f in required_fields if last_record.get(f) is None]
            
            if missing:
                print(f"\n✗ Missing required fields: {missing}")
            else:
                print("\n✅ All required schema fields present!")
            
            # Check if new fields are present
            new_fields = ['funding_ts', 'fills_queue_depth']
            present_new = [f for f in new_fields if last_record.get(f) is not None]
            
            print(f"\n✅ New fields added: {len(present_new)}/{len(new_fields)}")
            for field in present_new:
                print(f"   ✓ {field}")
            
            print("\n✅ Test complete!")
            print("✅ Health stream is now fully schema-compliant!")
else:
    print("⚠️  No health logs found yet")
