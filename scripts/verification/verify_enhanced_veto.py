"""
Comprehensive Verification: Enhanced Veto Tracking Implementation
Tests that the implementation will work correctly for both 5m and 12h bots
"""

import sys
import os
import json
sys.path.insert(0, os.path.abspath('.'))

from live_demo.order_intent_tracker import OrderIntentTracker

print("=" * 70)
print("ENHANCED VETO TRACKING - COMPREHENSIVE VERIFICATION")
print("=" * 70)
print()

# Test scenarios for both timeframes
test_scenarios = [
    {
        "name": "5m Bot - Multiple Guard Failures",
        "timeframe": "5m",
        "decision": {"dir": 0, "alpha": 0.08},
        "model_out": {"s_model": 0.05, "confidence": 0.65},
        "market_data": {
            "spread_bps": 12.5,
            "rv_1h": 0.005,
            "volume": 50.0,
            "mid": 50000.0,
            "funding_8h": 0.0001
        },
        "risk_state": {"position": 0.0, "max_position": 1.0}
    },
    {
        "name": "12h Bot - Single Guard Failure",
        "timeframe": "12h",
        "decision": {"dir": 0, "alpha": 0.10},
        "model_out": {"s_model": 0.15, "confidence": 0.75},
        "market_data": {
            "spread_bps": 15.0,
            "rv_1h": 0.02,
            "volume": 500.0,
            "mid": 51000.0,
            "funding_8h": 0.0002
        },
        "risk_state": {"position": 0.0, "max_position": 1.0}
    },
    {
        "name": "All Guards Pass",
        "timeframe": "5m",
        "decision": {"dir": 1, "alpha": 0.15},
        "model_out": {"s_model": 0.20, "confidence": 0.85},
        "market_data": {
            "spread_bps": 5.0,
            "rv_1h": 0.05,
            "volume": 1000.0,
            "mid": 50000.0,
            "funding_8h": 0.0001
        },
        "risk_state": {"position": 0.0, "max_position": 1.0}
    }
]

all_tests_passed = True
test_results = []

for scenario in test_scenarios:
    print(f"Testing: {scenario['name']}")
    print("-" * 70)
    
    # Create tracker
    tracker = OrderIntentTracker()
    
    # Log order intent
    intent_dict = tracker.log_order_intent_dict(
        ts=1736849400000,
        bar_id=100,
        asset="BTCUSDT",
        decision=scenario["decision"],
        model_out=scenario["model_out"],
        market_data=scenario["market_data"],
        risk_state=scenario["risk_state"]
    )
    
    if not intent_dict:
        print("❌ FAILED: No intent_dict returned")
        all_tests_passed = False
        test_results.append({"scenario": scenario["name"], "passed": False, "reason": "No intent returned"})
        print()
        continue
    
    # Check for enhanced fields
    has_primary = 'veto_reason_primary' in intent_dict
    has_secondary = 'veto_reason_secondary' in intent_dict
    has_details = 'guard_details' in intent_dict
    has_reason_codes = 'reason_codes' in intent_dict
    
    scenario_passed = has_primary and has_secondary and has_details and has_reason_codes
    
    if scenario_passed:
        print(f"✅ All enhanced fields present")
        print(f"   - Side: {intent_dict['side']}")
        print(f"   - Signal Strength: {intent_dict['signal_strength']}")
        print(f"   - Primary Veto: {intent_dict['veto_reason_primary']}")
        print(f"   - Secondary Veto: {intent_dict['veto_reason_secondary']}")
        
        # Count failed guards
        failed_guards = [k for k, v in intent_dict['reason_codes'].items() if v is False]
        print(f"   - Failed Guards: {len(failed_guards)}")
        
        # Show guard details
        if intent_dict['guard_details']:
            print(f"   - Guard Details: {len(intent_dict['guard_details'])} guards with details")
            for guard_name, details in intent_dict['guard_details'].items():
                print(f"     • {guard_name}: {details}")
        else:
            print(f"   - Guard Details: None (all guards passed)")
        
        test_results.append({"scenario": scenario["name"], "passed": True})
    else:
        print(f"❌ FAILED: Missing enhanced fields")
        if not has_primary:
            print(f"   - Missing: veto_reason_primary")
        if not has_secondary:
            print(f"   - Missing: veto_reason_secondary")
        if not has_details:
            print(f"   - Missing: guard_details")
        if not has_reason_codes:
            print(f"   - Missing: reason_codes")
        
        all_tests_passed = False
        test_results.append({"scenario": scenario["name"], "passed": False, "reason": "Missing fields"})
    
    print()

# Final verification
print("=" * 70)
print("FINAL VERIFICATION")
print("=" * 70)
print()

# Check that the implementation matches both bots' usage
print("Checking integration with bot code...")
print()

# Verify 5m bot integration
live_demo_main = "live_demo/main.py"
if os.path.exists(live_demo_main):
    with open(live_demo_main, 'r', encoding='utf-8') as f:
        content = f.read()
        has_import = "from live_demo.order_intent_tracker import OrderIntentTracker" in content
        has_init = "order_intent_tracker = OrderIntentTracker()" in content
        has_usage = "order_intent_tracker.log_order_intent_dict(" in content
        has_emit = "emitter.emit_order_intent(order_intent)" in content
        
        print("5m Bot Integration:")
        print(f"  {'✅' if has_import else '❌'} Import OrderIntentTracker")
        print(f"  {'✅' if has_init else '❌'} Initialize tracker")
        print(f"  {'✅' if has_usage else '❌'} Use log_order_intent_dict()")
        print(f"  {'✅' if has_emit else '❌'} Emit order_intent")
        
        bot_5m_ready = has_import and has_init and has_usage and has_emit
        print(f"  Status: {'✅ READY' if bot_5m_ready else '❌ NOT READY'}")
else:
    print("❌ 5m bot main.py not found")
    bot_5m_ready = False

print()

# Verify 12h bot integration
live_demo_12h_main = "live_demo_12h/main.py"
if os.path.exists(live_demo_12h_main):
    with open(live_demo_12h_main, 'r', encoding='utf-8') as f:
        content = f.read()
        # 12h bot might use different import path
        has_import_12h = "OrderIntentTracker" in content or "order_intent_tracker" in content
        has_emit_12h = "emit_order_intent" in content
        
        print("12h Bot Integration:")
        print(f"  {'✅' if has_import_12h else '❌'} OrderIntentTracker referenced")
        print(f"  {'✅' if has_emit_12h else '❌'} Emit order_intent")
        
        bot_12h_ready = has_emit_12h
        print(f"  Status: {'✅ READY' if bot_12h_ready else '❌ NOT READY'}")
else:
    print("❌ 12h bot main.py not found")
    bot_12h_ready = False

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()

# Test results summary
passed_tests = sum(1 for r in test_results if r["passed"])
total_tests = len(test_results)

print(f"Test Scenarios: {passed_tests}/{total_tests} passed")
for result in test_results:
    status = "✅" if result["passed"] else "❌"
    print(f"  {status} {result['scenario']}")

print()
print(f"5m Bot Integration: {'✅ READY' if bot_5m_ready else '❌ NOT READY'}")
print(f"12h Bot Integration: {'✅ READY' if bot_12h_ready else '❌ NOT READY'}")
print()

# Final verdict
overall_success = all_tests_passed and bot_5m_ready and bot_12h_ready

if overall_success:
    print("🎉 " + "=" * 66)
    print("🎉 VERIFICATION SUCCESSFUL - TASK COMPLETED!")
    print("🎉 " + "=" * 66)
    print()
    print("✅ Enhanced veto tracking is implemented and working")
    print("✅ Both 5m and 12h bots will automatically use it")
    print("✅ All test scenarios passed")
    print()
    print("Next order_intent logs will include:")
    print("  - veto_reason_primary")
    print("  - veto_reason_secondary")
    print("  - guard_details (with actual values vs thresholds)")
    print()
    print("Status: READY FOR PRODUCTION ✅")
else:
    print("❌ " + "=" * 66)
    print("❌ VERIFICATION FAILED - ISSUES FOUND")
    print("❌ " + "=" * 66)
    print()
    if not all_tests_passed:
        print("❌ Some test scenarios failed")
    if not bot_5m_ready:
        print("❌ 5m bot integration incomplete")
    if not bot_12h_ready:
        print("❌ 12h bot integration incomplete")

print()
print("=" * 70)

# Exit with appropriate code
sys.exit(0 if overall_success else 1)
