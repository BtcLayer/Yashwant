#!/usr/bin/env python3
"""Test that calibrator actually changes model predictions."""

import sys
from pathlib import Path
import numpy as np

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from live_demo.calibration_utils import CalibrationWrapper
import joblib

print("="*70)
print("CALIBRATOR EFFECT TEST")
print("="*70)

# Load calibrator
calibrator_path = REPO_ROOT / 'live_demo/models/calibrator_5m_platt.pkl'
print(f"\nLoading calibrator from: {calibrator_path}")
calibrator = joblib.load(calibrator_path)
print(f"✅ Loaded: {type(calibrator).__name__}")
print(f"   Classes: {calibrator.classes_}")
print(f"   Transformers: {len(calibrator.calibrated_classifiers_)}")

# Test cases: overconfident predictions that should be calibrated
test_cases = [
    {
        'name': 'Strong UP prediction (overconfident)',
        'raw_probs': np.array([[0.05, 0.15, 0.80]])  # 80% up
    },
    {
        'name': 'Strong DOWN prediction (overconfident)',
        'raw_probs': np.array([[0.75, 0.15, 0.10]])  # 75% down
    },
    {
        'name': 'Moderate UP prediction',
        'raw_probs': np.array([[0.15, 0.25, 0.60]])  # 60% up
    },
    {
        'name': 'Balanced/Neutral prediction',
        'raw_probs': np.array([[0.10, 0.80, 0.10]])  # 80% neutral
    },
    {
        'name': 'Weak directional signal',
        'raw_probs': np.array([[0.35, 0.30, 0.35]])  # Ambiguous
    }
]

print(f"\n{'-'*70}")
print("Testing calibration effect on various predictions:")
print(f"{'-'*70}\n")

for i, test in enumerate(test_cases, 1):
    raw = test['raw_probs']
    calibrated = calibrator.predict_proba(raw)
    
    print(f"{i}. {test['name']}")
    print(f"   Raw:        down={raw[0][0]:.3f}, neutral={raw[0][1]:.3f}, up={raw[0][2]:.3f}")
    print(f"   Calibrated: down={calibrated[0][0]:.3f}, neutral={calibrated[0][1]:.3f}, up={calibrated[0][2]:.3f}")
    
    # Compute adjustment magnitude
    max_raw = np.max(raw)
    max_cal = np.max(calibrated)
    adjustment = abs(max_raw - max_cal)
    adjustment_pct = (adjustment / max_raw) * 100 if max_raw > 0 else 0
    
    print(f"   Adjustment: {adjustment:.3f} ({adjustment_pct:.1f}% change in max probability)")
    
    # Check if calibration reduced overconfidence
    if max_raw > 0.6 and max_cal < max_raw:
        print(f"   ✅ Calibration reduced overconfidence")
    elif adjustment < 0.01:
        print(f"   ⚠️  Minimal calibration effect (<1% change)")
    
    print()

print(f"{'-'*70}")
print("\n💡 Expected behavior:")
print("   - Overconfident predictions (>70%) should be reduced")
print("   - Well-calibrated predictions (~50-60%) should change minimally")
print("   - Neutral predictions should remain largely unchanged")
print()
print("✅ If adjustments are >5%, calibrator is working correctly")
print("❌ If adjustments are <1%, calibrator may be ineffective")
print("="*70)
