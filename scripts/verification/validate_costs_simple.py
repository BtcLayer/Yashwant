"""Simple costs schema validation test"""
import json
import sys
sys.path.insert(0, 'live_demo')

# Load schema
with open('live_demo/schemas/logs/costs.schema.json', 'r') as f:
    schema = json.load(f)

print("Costs Schema Required Fields:")
for field in schema['required']:
    print(f"  - {field}")

# Load latest costs log
import os
log_files = []
for root, dirs, files in os.walk("../paper_trading_outputs/logs/costs"):
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
                print("✅ Costs logs are schema-compliant!")
else:
    print("No costs logs found")
