import json
import os
import numpy as np
from live_demo.model_runtime import ModelRuntime

# Load manifest
manifest = os.path.join(os.path.dirname(__file__), '..', 'models', 'LATEST.json')
manifest = os.path.abspath(manifest)
print(f"Using manifest: {manifest}")
mr = ModelRuntime(manifest)

# Build a zero vector matching the feature schema
n = len(getattr(mr, 'columns', []) or [])
print(f"Feature count: {n}")
if n == 0:
    raise SystemExit("No feature columns found; cannot run smoke test")

x = [0.0] * n
out = mr.infer(x)
print(json.dumps(out, indent=2))
