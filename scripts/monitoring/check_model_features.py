import joblib
import sys
import json

# Load the model
model_path = r"c:\Users\yashw\MetaStackerBandit\live_demo\models\meta_classifier_20260102_111331_d7a9e9fb3a42.joblib"
model = joblib.load(model_path)

# Load the feature columns
feature_cols_path = r"c:\Users\yashw\MetaStackerBandit\live_demo\models\feature_columns_20260102_111331_d7a9e9fb3a42.json"
with open(feature_cols_path, 'r') as f:
    feature_data = json.load(f)
    feature_cols = feature_data['feature_cols']

print(f"Model type: {type(model)}")
print(f"\nModel expects {model.n_features_in_} features")
print(f"Feature columns JSON has {len(feature_cols)} features")
print(f"\nFeature columns from JSON:")
for i, col in enumerate(feature_cols):
    print(f"  {i+1}. {col}")

# Check if model has feature_names_in_
if hasattr(model, 'feature_names_in_'):
    print(f"\nModel's feature_names_in_:")
    for i, name in enumerate(model.feature_names_in_):
        print(f"  {i+1}. {name}")
else:
    print("\nModel doesn't have feature_names_in_ attribute (trained without feature names)")

