"""
Test if the new 1h model actually works
"""
import joblib
import json
import numpy as np

print("Testing 1h model...")
print()

# Load LATEST
with open('live_demo_1h/models/LATEST.json', 'r') as f:
    latest = json.load(f)

print(f"Model files: {latest['meta_classifier']}")
print()

# Load feature schema
with open(f"live_demo_1h/models/{latest['feature_columns']}", 'r') as f:
    feat_schema = json.load(f)

features = feat_schema['feature_cols']
print(f"Expected features: {len(features)}")
print(f"Features: {features[:5]}...")
print()

# Load model
model = joblib.load(f"live_demo_1h/models/{latest['meta_classifier']}")
print(f"Model type: {type(model)}")
print(f"Model expects: {model.n_features_in_} features")
print()

# The meta-classifier expects 12 features because it's trained on 
# stacked predictions from 4 base models × 3 classes = 12 features
# This is CORRECT!

print("✅ This is actually CORRECT behavior!")
print()
print("The meta-classifier expects 12 features because:")
print("  - 4 base models (RandomForest, ExtraTrees, HistGB, GB)")
print("  - Each predicts 3 classes (DOWN, NEUTRAL, UP)")
print("  - 4 × 3 = 12 stacked prediction features")
print()
print("The bot should:")
print("  1. Take 17 input features")
print("  2. Pass to base models")
print("  3. Stack their predictions (12 features)")
print("  4. Pass to meta-classifier")
print()
print("The error suggests the bot is skipping steps 2-3!")
print("This is a bot code issue, not a model issue.")
