import joblib
import json
import os
import sys

# Add project to path and import custom classes
sys.path.insert(0, r'c:\Users\yashw\MetaStackerBandit')
from live_demo.custom_models import EnhancedMetaClassifier, CustomClassificationCalibrator

# Paths
models_dir = r"c:\Users\yashw\MetaStackerBandit\live_demo\models"

# Old model (October 2025)
old_model_path = os.path.join(models_dir, "meta_classifier_20251018_101628_d7a9e9fb3a42.joblib")
old_features_path = os.path.join(models_dir, "feature_columns_20251018_101628_d7a9e9fb3a42.json")
old_meta_path = os.path.join(models_dir, "training_meta_20251018_101628_d7a9e9fb3a42.json")

# New model (January 2026)
new_model_path = os.path.join(models_dir, "meta_classifier_20260102_111331_d7a9e9fb3a42.joblib")
new_features_path = os.path.join(models_dir, "feature_columns_20260102_111331_d7a9e9fb3a42.json")
new_meta_path = os.path.join(models_dir, "training_meta_20260102_111331_d7a9e9fb3a42.json")

print("=" * 80)
print("COMPARING OLD MODEL vs NEW MODEL")
print("=" * 80)

# Load old model
print("\n### OLD MODEL (October 2025) ###")
old_model = joblib.load(old_model_path)
with open(old_features_path, 'r') as f:
    old_features = json.load(f)['feature_cols']
if os.path.exists(old_meta_path):
    with open(old_meta_path, 'r') as f:
        old_meta = json.load(f)
else:
    old_meta = None

print("Model type: {0}".format(type(old_model).__name__))

# Get n_features from model
old_n_features = None
if hasattr(old_model, 'n_features_in_'):
    old_n_features = old_model.n_features_in_
elif hasattr(old_model, 'base_models') and old_model.base_models:
    # EnhancedMetaClassifier - check first base model
    first_base = list(old_model.base_models.values())[0]
    if hasattr(first_base, 'n_features_in_'):
        old_n_features = first_base.n_features_in_

if old_n_features:
    print("Model expects: {0} features".format(old_n_features))
else:
    print("Model expects: UNKNOWN (no n_features_in_ found)")
    
print("Feature JSON has: {0} features".format(len(old_features)))
if old_meta:
    print("Training meta n_features: {0}".format(old_meta.get('n_features', 'N/A')))

print("\nOld model features ({0}):".format(len(old_features)))
for i, feat in enumerate(old_features, 1):
    print("  {0:2d}. {1}".format(i, feat))

# Load new model
print("\n### NEW MODEL (January 2026) ###")
new_model = joblib.load(new_model_path)
with open(new_features_path, 'r') as f:
    new_features = json.load(f)['feature_cols']
if os.path.exists(new_meta_path):
    with open(new_meta_path, 'r') as f:
        new_meta = json.load(f)
else:
    new_meta = None

print("Model type: {0}".format(type(new_model).__name__))

# Get n_features from model
new_n_features = None
if hasattr(new_model, 'n_features_in_'):
    new_n_features = new_model.n_features_in_
elif hasattr(new_model, 'base_models') and new_model.base_models:
    # EnhancedMetaClassifier - check first base model
    first_base = list(new_model.base_models.values())[0]
    if hasattr(first_base, 'n_features_in_'):
        new_n_features = first_base.n_features_in_

if new_n_features:
    print("Model expects: {0} features".format(new_n_features))
else:
    print("Model expects: UNKNOWN (no n_features_in_ found)")
    
print("Feature JSON has: {0} features".format(len(new_features)))
if new_meta:
    print("Training meta n_features: {0}".format(new_meta.get('n_features', 'N/A')))

print("\nNew model features ({0}):".format(len(new_features)))
for i, feat in enumerate(new_features, 1):
    print("  {0:2d}. {1}".format(i, feat))

# Compare
print("\n" + "=" * 80)
print("COMPARISON SUMMARY")
print("=" * 80)

print("\nOld: Model expects {0}, JSON has {1} features".format(old_n_features, len(old_features)))
print("New: Model expects {0}, JSON has {1} features".format(new_n_features, len(new_features)))

if old_n_features and old_n_features == len(old_features):
    print("[OK] Old model: MATCH between model and JSON")
elif old_n_features:
    print("[MISMATCH] Old model: Difference = {0}".format(old_n_features - len(old_features)))
else:
    print("[?] Old model: Cannot determine (no n_features_in_)")

if new_n_features and new_n_features == len(new_features):
    print("[OK] New model: MATCH between model and JSON")
elif new_n_features:
    print("[MISMATCH] New model: Difference = {0}".format(new_n_features - len(new_features)))
else:
    print("[?] New model: Cannot determine (no n_features_in_)")

# Find differences in features
old_set = set(old_features)
new_set = set(new_features)

added = new_set - old_set
removed = old_set - new_set

if added:
    print("\n[ADDED] Features in new model: {0}".format(added))
if removed:
    print("\n[REMOVED] Features from old model: {0}".format(removed))
if not added and not removed:
    print("\n[SAME] Feature lists are identical")

# Check if model has feature_names_in_
print("\n" + "=" * 80)
print("CHECKING MODEL FEATURE NAMES")
print("=" * 80)

if hasattr(old_model, 'feature_names_in_'):
    print("\nOld model has feature_names_in_ ({0} features):".format(len(old_model.feature_names_in_)))
    for i, name in enumerate(old_model.feature_names_in_, 1):
        print("  {0:2d}. {1}".format(i, name))
else:
    print("\nOld model: No feature_names_in_ (trained without column names)")

if hasattr(new_model, 'feature_names_in_'):
    print("\nNew model has feature_names_in_ ({0} features):".format(len(new_model.feature_names_in_)))
    for i, name in enumerate(new_model.feature_names_in_, 1):
        print("  {0:2d}. {1}".format(i, name))
else:
    print("\nNew model: No feature_names_in_ (trained without column names)")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
