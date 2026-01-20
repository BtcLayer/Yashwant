"""
Test enhanced veto tracking in OrderIntentTracker
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from live_demo.order_intent_tracker import OrderIntentTracker

# Create tracker
tracker = OrderIntentTracker()

# Test data
ts = 1736849400000
bar_id = 100
asset = "BTCUSDT"

decision = {
    "dir": 0,  # HOLD
    "alpha": 0.08  # Below threshold of 0.12
}

model_out = {
    "s_model": 0.05,  # Below band threshold of 0.12
    "confidence": 0.65
}

market_data = {
    "spread_bps": 12.5,  # Above threshold of 10.0
    "rv_1h": 0.005,  # Below min threshold of 0.01
    "volume": 50.0,  # Below min threshold of 100.0
    "mid": 50000.0,
    "funding_8h": 0.0001
}

risk_state = {
    "position": 0.0,
    "max_position": 1.0,
    "risk_score": 0.0
}

# Log order intent
intent_dict = tracker.log_order_intent_dict(
    ts=ts,
    bar_id=bar_id,
    asset=asset,
    decision=decision,
    model_out=model_out,
    market_data=market_data,
    risk_state=risk_state
)

print("=" * 60)
print("ENHANCED VETO TRACKING TEST")
print("=" * 60)
print()

if intent_dict:
    print("✅ Order Intent Created")
    print()
    
    print("Basic Fields:")
    print(f"  - Side: {intent_dict['side']}")
    print(f"  - Signal Strength: {intent_dict['signal_strength']}")
    print()
    
    print("Reason Codes (True = passed, False = failed):")
    for guard, passed in intent_dict['reason_codes'].items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  - {guard}: {status}")
    print()
    
    print("Enhanced Veto Fields:")
    print(f"  - Primary Veto: {intent_dict.get('veto_reason_primary', 'NOT FOUND')}")
    print(f"  - Secondary Veto: {intent_dict.get('veto_reason_secondary', 'NOT FOUND')}")
    print()
    
    print("Guard Details (only for failed guards):")
    guard_details = intent_dict.get('guard_details', {})
    if guard_details:
        for guard_name, details in guard_details.items():
            print(f"  {guard_name}:")
            for key, value in details.items():
                print(f"    - {key}: {value}")
    else:
        print("  (No guard details - all guards passed)")
    print()
    
    # Verify enhanced fields exist
    print("=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    has_primary = 'veto_reason_primary' in intent_dict
    has_secondary = 'veto_reason_secondary' in intent_dict
    has_details = 'guard_details' in intent_dict
    
    print(f"✅ veto_reason_primary: {'PRESENT' if has_primary else 'MISSING'}")
    print(f"✅ veto_reason_secondary: {'PRESENT' if has_secondary else 'MISSING'}")
    print(f"✅ guard_details: {'PRESENT' if has_details else 'MISSING'}")
    print()
    
    if has_primary and has_secondary and has_details:
        print("🎉 ALL ENHANCED FIELDS PRESENT!")
        print()
        print("This means:")
        print("  - Can identify which guard failed first")
        print("  - Can see actual values vs thresholds")
        print("  - Can diagnose rejection patterns")
    else:
        print("❌ SOME FIELDS MISSING")
else:
    print("❌ Failed to create order intent")
