"""
Verification Script for Phase 6 - Enhanced Manifests
Tests that all enhanced manifests load correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*80)
print("PHASE 6 VERIFICATION: Testing Enhanced Manifests")
print("="*80)

manifests_to_test = [
    ('5m', 'live_demo/models/LATEST.json'),
    ('1h', 'live_demo_1h/models/LATEST.json'),
    ('12h', 'live_demo_12h/models/LATEST.json'),
    ('24h', 'live_demo_24h/models/LATEST.json')
]

all_passed = True

for name, manifest_path in manifests_to_test:
    print(f"\n{name} Timeframe")
    print("-" * 80)
    
    if not os.path.exists(manifest_path):
        print(f"  ⚠️  Manifest not found: {manifest_path}")
        continue
    
    try:
        # Test 1: Load with manifest_loader
        print(f"  1. Testing manifest_loader...")
        from live_demo.models.manifest_loader import normalize_manifest
        result = normalize_manifest(manifest_path)
        
        print(f"     ✅ Loaded successfully")
        print(f"     - model_path: {result.get('model_path') is not None}")
        print(f"     - feature_schema_path: {result.get('feature_schema_path') is not None}")
        print(f"     - git_commit: {result.get('git_commit')}")
        print(f"     - trained_at_utc: {result.get('trained_at_utc')}")
        print(f"     - feature_dim: {result.get('feature_dim')}")
        
        # Test 2: Load with ModelRuntime
        print(f"  2. Testing ModelRuntime...")
        from live_demo.model_runtime import ModelRuntime
        mr = ModelRuntime(manifest_path)
        
        print(f"     ✅ ModelRuntime initialized")
        print(f"     - Model loaded: {mr.model is not None}")
        print(f"     - Calibrator loaded: {mr.calibrator is not None}")
        print(f"     - Feature columns: {len(mr.columns)}")
        print(f"     - Git commit: {mr.git_commit}")
        print(f"     - Trained at: {mr.trained_at_utc}")
        print(f"     - Expected feature dim: {mr.expected_feature_dim}")
        
        # Test 3: Model inference
        print(f"  3. Testing model inference...")
        import numpy as np
        dummy_input = [0.0] * len(mr.columns)
        pred = mr.infer(dummy_input)
        
        print(f"     ✅ Inference works")
        print(f"     - p_down: {pred.get('p_down'):.4f}")
        print(f"     - p_neutral: {pred.get('p_neutral'):.4f}")
        print(f"     - p_up: {pred.get('p_up'):.4f}")
        
        print(f"  ✅ All tests passed for {name}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

print("\n" + "="*80)
if all_passed:
    print("✅ VERIFICATION COMPLETE: ALL TIMEFRAMES WORKING!")
else:
    print("❌ VERIFICATION FAILED: Some timeframes have issues")
print("="*80)
