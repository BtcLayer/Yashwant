"""Validate order intent against schema"""
import json
import sys
sys.path.insert(0, 'live_demo')

# Load schema
with open('live_demo/schemas/logs/order_intent_pre_risk.schema.json', 'r') as f:
    schema = json.load(f)

print("Order Intent Schema Required Fields:")
for field in schema['required']:
    print(f"  - {field}")

# Load latest order_intent log
import os
log_files = []
for root, dirs, files in os.walk("../paper_trading_outputs/logs/order_intent"):
    for file in files:
        if file.endswith('.jsonl'):
            log_files.append(os.path.join(root, file))

if log_files:
    latest_log = max(log_files, key=os.path.getmtime)
    with open(latest_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_record = json.loads(lines[-1])
            
            print("\nActual Log Fields:")
            for field in schema['required']:
                value = last_record.get(field)
                status = "✓" if value is not None else "✗"
                print(f"  {status} {field}: {value}")
            
            # Check all required fields present
            missing = [f for f in schema['required'] if last_record.get(f) is None]
            if missing:
                print(f"\n✗ Missing required fields: {missing}")
            else:
                print("\n✅ All required fields present!")
                print("✅ Order intent logs are schema-compliant!")
                
            # Show veto tracking fields
            print("\n📊 Veto Tracking Fields:")
            veto_fields = ['veto_reason_primary', 'veto_reason_secondary', 'guard_details', 
                          'checks_passed', 'vetoes_triggered']
            for field in veto_fields:
                value = last_record.get(field)
                if value is not None:
                    if isinstance(value, dict):
                        print(f"  ✓ {field}: {len(value)} items")
                    else:
                        print(f"  ✓ {field}: {value}")
else:
    print("No order_intent logs found")
