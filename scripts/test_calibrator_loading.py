#!/usr/bin/env python3
"""Test that calibrator loads correctly in ModelRuntime."""

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from live_demo.model_runtime import ModelRuntime

print("Testing calibrator loading...")
rt = ModelRuntime('live_demo/models/LATEST.json')

print(f"✅ ModelRuntime initialized successfully")
print(f"   Calibrator loaded: {rt.calibrator is not None}")
print(f"   Calibrator type: {type(rt.calibrator).__name__ if rt.calibrator else 'None'}")
print(f"   Calibrator path: {rt.calibrator_path}")
