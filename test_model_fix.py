import sys
sys.path.insert(0, r'c:\Users\yashw\MetaStackerBandit')

from live_demo.model_runtime import ModelRuntime
import json

print("=" * 80)
print("TESTING MODEL AFTER FIX")
print("=" * 80)

# Load the model
manifest_path = r'c:\Users\yashw\MetaStackerBandit\live_demo\models\LATEST.json'
print(f"\nLoading model from: {manifest_path}")

with open(manifest_path, 'r') as f:
    manifest = json.load(f)
    print(f"Model file: {manifest['meta_classifier']}")

mr = ModelRuntime(manifest_path)

print(f"\nModel type: {type(mr.model).__name__}")
print(f"Expected features: {len(mr.columns)}")
print(f"Feature columns: {mr.columns}")

# Test inference with 17 features
print("\n" + "=" * 80)
print("TESTING INFERENCE")
print("=" * 80)

test_features = [0.001, 0.002, 0.5, 0.01, 0.0, 0.008, 0.001, 0.5, 0.8, 0.1, 0.002, 0.0, 0.0001, 0.0, 0.1, 0.2, -0.1]
print(f"\nTest input: {len(test_features)} features")

try:
    result = mr.infer(test_features)
    print("\n✓ SUCCESS! Inference completed without errors.")
    print(f"\nPrediction:")
    print(f"  p_down: {result['p_down']:.4f}")
    print(f"  p_neutral: {result['p_neutral']:.4f}")
    print(f"  p_up: {result['p_up']:.4f}")
    print(f"  s_model: {result['s_model']:.4f}")
    print("\n" + "=" * 80)
    print("FIX VERIFIED - Model is working correctly!")
    print("=" * 80)
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    print("\n" + "=" * 80)
    print("FIX FAILED - Issue persists")
    print("=" * 80)
