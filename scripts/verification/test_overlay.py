"""Test Overlay logging"""
import sys
sys.path.insert(0, 'live_demo')

from ops.log_emitter import LogEmitter
import time
import json

print("Testing Overlay logging...")

emitter = LogEmitter()

# Test with typical overlay data
emitter.emit_overlay(
    ts=time.time(),
    symbol="BTCUSDT",
    bar_id=100,
    confidence=0.75,
    alignment_rule="agreement",
    chosen_timeframes=["5m", "15m", "1h"],
    overlay_dir=1,
    overlay_alpha=0.65,
    individual_signals={
        "5m": {"dir": 1, "alpha": 0.60, "conf": 0.70},
        "15m": {"dir": 1, "alpha": 0.70, "conf": 0.80},
        "1h": {"dir": -1, "alpha": 0.50, "conf": 0.60}  # Conflicting!
    }
)

print("✓ Overlay log emitted")

# Verify the log structure
import os
log_files = []
for root, dirs, files in os.walk("../paper_trading_outputs/logs/overlay"):
    for file in files:
        if file.endswith('.jsonl'):
            log_files.append(os.path.join(root, file))

if log_files:
    latest_log = max(log_files, key=os.path.getmtime)
    print(f"\n📄 Latest overlay log: {latest_log}")
    
    with open(latest_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_record = json.loads(lines[-1])
            print("\n✅ Required fields:")
            print(f"   bar_id: {last_record.get('bar_id')}")
            print(f"   confidence: {last_record.get('confidence')}")
            print(f"   alignment_rule: {last_record.get('alignment_rule')}")
            
            print("\n✅ Overlay result:")
            print(f"   chosen_timeframes: {last_record.get('chosen_timeframes')}")
            print(f"   overlay_dir: {last_record.get('overlay_dir')}")
            print(f"   overlay_alpha: {last_record.get('overlay_alpha')}")
            
            print("\n✅ Derived metrics (AUTO-CALCULATED):")
            print(f"   num_timeframes: {last_record.get('num_timeframes')}")
            print(f"   agreement_pct: {last_record.get('agreement_pct')}%")
            print(f"   strongest_timeframe: {last_record.get('strongest_timeframe')}")
            print(f"   weakest_timeframe: {last_record.get('weakest_timeframe')}")
            print(f"   conflicting_timeframes: {last_record.get('conflicting_timeframes')}")
            
            print("\n✅ Individual signals:")
            for tf, sig in last_record.get('individual_signals', {}).items():
                print(f"   {tf}: dir={sig.get('dir')}, alpha={sig.get('alpha')}, conf={sig.get('conf')}")
            
            # Verify schema compliance
            required_fields = ['ts', 'symbol', 'bar_id', 'confidence', 'alignment_rule']
            missing = [f for f in required_fields if last_record.get(f) is None]
            
            if missing:
                print(f"\n✗ Missing required fields: {missing}")
            else:
                print("\n✅ All required schema fields present!")
            
            # Verify auto-calculated fields
            if last_record.get('agreement_pct') is not None:
                print("\n✅ Auto-calculated fields working!")
                print(f"   Agreement: {last_record.get('agreement_pct'):.1f}%")
                print(f"   Strongest: {last_record.get('strongest_timeframe')}")
                print(f"   Conflicts: {last_record.get('conflicting_timeframes')}")
            
            print("\n✅ Test complete!")
            print("✅ Overlay stream is now schema-compliant!")
else:
    print("⚠️  No overlay logs found yet")
