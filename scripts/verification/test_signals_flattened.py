"""Test flattened signals logging"""
import sys
sys.path.insert(0, 'live_demo')

from ops.log_emitter import LogEmitter
import time
import json

print("Testing flattened signals logging...")

emitter = LogEmitter()

# Test with typical signals payload from main.py
model_out = {
    'p_up': 0.55,
    'p_down': 0.15,
    'p_neutral': 0.30,
    's_model': 0.40,
    's_model_meta': 0.40,
    'a': 0.0,
    'b': 1.0
}

decision = {
    'dir': 1,
    'alpha': 0.65,
    'details': {
        'chosen': 'model_meta',
        's_model': 0.40,
        'conf': 0.65
    }
}

cohort = {
    'pros': 0.12,
    'amateurs': -0.08,
    'mood': 0.05
}

features = {
    'close': 102500.0,
    'volume': 1000.0
}

emitter.emit_signals(
    ts=time.time(),
    symbol="BTCUSDT",
    features=features,
    model_out=model_out,
    decision=decision,
    cohort=cohort
)

print("✓ Signals log emitted")

# Verify the log structure
import os
log_files = []
for root, dirs, files in os.walk("../paper_trading_outputs/logs/signals"):
    for file in files:
        if file.endswith('.jsonl'):
            log_files.append(os.path.join(root, file))

if log_files:
    latest_log = max(log_files, key=os.path.getmtime)
    print(f"\n📄 Latest signals log: {latest_log}")
    
    with open(latest_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_record = json.loads(lines[-1])
            print("\n✅ Flattened model prediction fields:")
            print(f"   p_up: {last_record.get('p_up')}")
            print(f"   p_down: {last_record.get('p_down')}")
            print(f"   p_neutral: {last_record.get('p_neutral')}")
            print(f"   s_model: {last_record.get('s_model')}")
            
            print("\n✅ Derived fields:")
            print(f"   p_non_neutral: {last_record.get('p_non_neutral')}")
            print(f"   conf_dir: {last_record.get('conf_dir')}")
            print(f"   strength: {last_record.get('strength')}")
            
            print("\n✅ Decision fields:")
            print(f"   selected_arm: {last_record.get('selected_arm')}")
            print(f"   raw_action: {last_record.get('raw_action')}")
            print(f"   final_action: {last_record.get('final_action')}")
            print(f"   decision_dir: {last_record.get('decision_dir')}")
            print(f"   decision_alpha: {last_record.get('decision_alpha')}")
            
            print("\n✅ Cohort fields:")
            print(f"   cohort_pros: {last_record.get('cohort_pros')}")
            print(f"   cohort_amateurs: {last_record.get('cohort_amateurs')}")
            print(f"   cohort_mood: {last_record.get('cohort_mood')}")
            
            # Check backward compatibility
            if 'model' in last_record and 'decision' in last_record:
                print("\n✅ Backward compatibility maintained (nested dicts present)")
            
            print("\n✅ Test complete!")
else:
    print("⚠️  No signals logs found yet")
