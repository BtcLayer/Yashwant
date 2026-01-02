"""
Quick summary of 5m model analysis
"""
import json
from datetime import datetime

# Load metadata
with open('live_demo/models/LATEST.json', 'r') as f:
    latest = json.load(f)

with open(f"live_demo/models/{latest['training_meta']}", 'r') as f:
    meta = json.load(f)

# Calculate age
train_date = datetime.strptime(meta['timestamp_utc'], '%Y%m%d_%H%M%S')
age_days = (datetime.now() - train_date).days

print("=" * 80)
print("5M MODEL QUICK SUMMARY")
print("=" * 80)
print()
print(f"📅 Trained: {train_date.strftime('%Y-%m-%d %H:%M')}")
print(f"⏰ Age: {age_days} days old")
print(f"📊 Training Score: {meta.get('meta_score_in_sample', 0):.4f} ({meta.get('meta_score_in_sample', 0)*100:.2f}%)")
print(f"🎯 Features: {meta['n_features']}")
print()

# Decision
print("🎯 DECISION:")
print("-" * 80)

if age_days > 90:
    print("❌ RETRAIN RECOMMENDED")
    print(f"   Reason: Model is {age_days} days old (>90 days)")
elif age_days > 60:
    print("⚠️ RETRAIN OPTIONAL")
    print(f"   Reason: Model is {age_days} days old (getting old)")
else:
    print("✅ NO RETRAINING NEEDED")
    print(f"   Reason: Model is only {age_days} days old (fresh enough)")

print()

if meta.get('meta_score_in_sample', 0) < 0.45:
    print("❌ RETRAIN RECOMMENDED")
    print(f"   Reason: Low training score ({meta.get('meta_score_in_sample', 0):.2%})")
elif meta.get('meta_score_in_sample', 0) >= 0.60:
    print("✅ PERFORMANCE IS GOOD")
    print(f"   Training score: {meta.get('meta_score_in_sample', 0):.2%}")

print()
print("=" * 80)
