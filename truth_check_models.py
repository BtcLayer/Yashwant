"""
TRUTH CHECK: Which timeframes truly have their own models vs shared
"""
import json
import os

print("=" * 80)
print("TRUTH VERIFICATION: MODEL INDEPENDENCE")
print("=" * 80)
print()

timeframes = {
    '5m': 'live_demo/models/LATEST.json',
    '1h': 'live_demo_1h/models/LATEST.json',
    '12h': 'live_demo_12h/models/LATEST.json',
    '24h': 'live_demo_24h/models/LATEST.json'
}

models = {}
dates = {}

for tf, path in timeframes.items():
    if os.path.exists(path):
        with open(path, 'r') as f:
            latest = json.load(f)
        
        model_file = latest['meta_classifier']
        models[tf] = model_file
        
        # Extract date
        date_str = model_file.split('_')[2]
        dates[tf] = date_str
        
        print(f"{tf.upper()}:")
        print(f"  Model: {model_file}")
        print(f"  Date: {date_str}")
        print()

print("=" * 80)
print("INDEPENDENCE CHECK")
print("=" * 80)
print()

# Check if any share the same model file
print("Checking for shared models:")
print()

# Group by model file
from collections import defaultdict
model_groups = defaultdict(list)
for tf, model in models.items():
    model_groups[model].append(tf)

shared_found = False
for model, tfs in model_groups.items():
    if len(tfs) > 1:
        print(f"⚠️ SHARED MODEL: {', '.join(tfs)} use the same model")
        print(f"   File: {model}")
        shared_found = True

if not shared_found:
    print("✅ No shared models found - all timeframes have unique model files")

print()

# Check if 24h is using old 5m model
print("Checking if 24h is using old 5m model:")
print()

old_5m_date = "20251018"  # From session report
current_24h_date = dates.get('24h', '')

if old_5m_date in current_24h_date:
    print(f"🔴 WARNING: 24h is using OLD 5m model from Oct 18, 2025")
    print(f"   This is the SAME model that 5m used before today's retraining")
    print(f"   24h does NOT have its own independent model")
else:
    print(f"✅ 24h has a different model (not the old 5m)")

print()

# Check if 1h was retrained
print("Checking 1h model status:")
print()

h1_date = dates.get('1h', '')
if '20251230' in h1_date or '20251231' in h1_date or '20260101' in h1_date or '20260102' in h1_date:
    print(f"✅ 1h was retrained recently (Dec 30 - Jan 2)")
    print(f"   1h NOW has its own independent model")
else:
    print(f"⚠️ 1h model date: {h1_date}")
    print(f"   Need to verify if this is independent")

print()

# Final verdict
print("=" * 80)
print("FINAL TRUTH")
print("=" * 80)
print()

print("Based on file analysis:")
print()

# 5m
print("5M:")
if dates.get('5m', '') == '20260102':
    print("  ✅ Has own model (retrained TODAY)")
else:
    print(f"  Status: {dates.get('5m', 'Unknown')}")

# 1h
print()
print("1H:")
if dates.get('1h', '') in ['20251230', '20251231', '20260101', '20260102']:
    print("  ✅ Has own model (retrained recently)")
elif dates.get('1h', '') == dates.get('5m', ''):
    print("  ❌ Using 5m model (SHARED)")
else:
    print(f"  ⚠️ Has model from {dates.get('1h', 'Unknown')} (need to verify)")

# 12h
print()
print("12H:")
if dates.get('12h', '') == '20251021':
    print("  ✅ Has own model (Oct 21, 2025)")
    print("  ⚠️ But WEAK (only 218 samples)")
else:
    print(f"  Status: {dates.get('12h', 'Unknown')}")

# 24h
print()
print("24H:")
if dates.get('24h', '') == '20251018':
    print("  ❌ Using OLD 5m model (Oct 18, 2025)")
    print("  🔴 This is the SAME model 5m used before today")
    print("  🔴 Does NOT have its own independent model")
elif dates.get('24h', '') == dates.get('5m', ''):
    print("  ❌ Using current 5m model (SHARED)")
else:
    print(f"  ⚠️ Has model from {dates.get('24h', 'Unknown')} (need to verify)")

print()
print("=" * 80)
print("CORRECTED SUMMARY")
print("=" * 80)
print()

independent = []
shared = []
weak = []

# Determine actual status
if dates.get('5m') == '20260102':
    independent.append('5m')

if dates.get('1h') in ['20251230', '20251231', '20260101', '20260102']:
    independent.append('1h')
elif dates.get('1h') == dates.get('5m'):
    shared.append('1h (using 5m)')

if dates.get('12h') == '20251021':
    independent.append('12h')
    weak.append('12h (only 218 samples)')

if dates.get('24h') == '20251018':
    shared.append('24h (using old 5m)')
elif dates.get('24h') == dates.get('5m'):
    shared.append('24h (using current 5m)')

print(f"Timeframes with OWN models: {len(independent)}/4")
for tf in independent:
    print(f"  ✅ {tf}")

print()

if shared:
    print(f"Timeframes SHARING models: {len(shared)}")
    for tf in shared:
        print(f"  ❌ {tf}")
else:
    print("No shared models ✅")

print()

if weak:
    print(f"Models that are WEAK:")
    for tf in weak:
        print(f"  ⚠️ {tf}")

print()
print("=" * 80)
