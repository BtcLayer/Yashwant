"""Test flattened order intent logging"""
import sys
sys.path.insert(0, 'live_demo')

from ops.log_emitter import LogEmitter
import time
import json

print("Testing flattened order intent logging...")

emitter = LogEmitter()

# Test with typical order intent payload
order_intent = {
    'ts': time.time() * 1000,
    'asset': 'BTCUSDT',
    'side': 'BUY',
    'bar_id_decision': 100,
    'intent_qty': 0.001,
    'intent_notional': 102.5,
    'signal_strength': 0.65,
    'model_confidence': 0.70,
    'risk_score': 0.15,
    'reason_codes': {
        'threshold': True,
        'band': True,
        'spread_guard': False,  # Failed
        'volatility': True,
        'liquidity': True,
        'risk': True
    },
    'veto_reason_primary': 'spread_guard',
    'veto_reason_secondary': None,
    'guard_details': {
        'spread_guard': {
            'spread_bps': 15.5,
            'threshold_bps': 10.0,
            'excess_bps': 5.5
        }
    },
    'market_conditions': {
        'spread_bps': 15.5,
        'volatility': 0.025,
        'volume': 1000.0,
        'funding_rate': 0.0001
    }
}

emitter.emit_order_intent(order_intent)

print("✓ Order intent log emitted")

# Verify the log structure
import os
log_files = []
for root, dirs, files in os.walk("../paper_trading_outputs/logs/order_intent"):
    for file in files:
        if file.endswith('.jsonl'):
            log_files.append(os.path.join(root, file))

if log_files:
    latest_log = max(log_files, key=os.path.getmtime)
    print(f"\n📄 Latest order_intent log: {latest_log}")
    
    with open(latest_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_record = json.loads(lines[-1])
            print("\n✅ Flattened intent fields:")
            print(f"   intent_action: {last_record.get('intent_action')}")
            print(f"   intent_dir: {last_record.get('intent_dir')}")
            print(f"   intent_strength: {last_record.get('intent_strength')}")
            
            print("\n✅ Veto tracking fields:")
            print(f"   veto_reason_primary: {last_record.get('veto_reason_primary')}")
            print(f"   veto_reason_secondary: {last_record.get('veto_reason_secondary')}")
            print(f"   guard_details: {last_record.get('guard_details')}")
            
            print("\n✅ Checks/vetoes:")
            print(f"   checks_passed: {last_record.get('checks_passed')}")
            print(f"   vetoes_triggered: {last_record.get('vetoes_triggered')}")
            
            # Check backward compatibility
            if 'order_intent' in last_record:
                print("\n✅ Backward compatibility maintained (nested dict present)")
            
            print("\n✅ Test complete!")
else:
    print("⚠️  No order_intent logs found yet")
