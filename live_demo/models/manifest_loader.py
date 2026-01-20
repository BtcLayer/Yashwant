"""Manifest loader for model artifacts (backward-compatible).

Supports two layouts:
1) Legacy: live_demo/models/LATEST.json contains direct filenames for
   meta_classifier, calibrator (optional), and feature_columns.
2) Versioned: live_demo/models/LATEST.json points to a versioned manifest
   (e.g., {"manifest": "v20251028_123045/manifest.json"}).

The loader normalizes into a simple dict with absolute paths and optional
calibration/ensemble fields so live runtime stays deterministic and fast.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple


def _abspath(base_dir: str, p: Optional[str]) -> Optional[str]:
    if not p:
        return None
    return p if os.path.isabs(p) else os.path.join(base_dir, p)


def _load_json(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def resolve_latest_path(latest_path: str) -> Tuple[str, Dict[str, Any]]:
    """Resolve LATEST.json into (manifest_path, manifest_obj or legacy_obj).

    If LATEST.json contains a 'manifest' key or a string path, return that
    target manifest path and its loaded JSON.
    If LATEST.json is a legacy minimal mapping, treat it as the manifest itself.
    """
    base_dir = os.path.dirname(os.path.abspath(latest_path))
    latest = _load_json(latest_path)
    # New style: object with 'manifest' or string containing a path
    if isinstance(latest, dict) and 'manifest' in latest:
        target = latest['manifest']
        manifest_path = _abspath(base_dir, target)
        return manifest_path, _load_json(manifest_path)
    if isinstance(latest, str):
        manifest_path = _abspath(base_dir, latest)
        return manifest_path, _load_json(manifest_path)
    # Legacy style: not a pointer, but the mapping itself
    return latest_path, latest


def normalize_manifest(latest_path: str) -> Dict[str, Any]:
    """Normalize manifest into a live-friendly structure.

    Returns a dict with keys:
      - feature_schema_path
      - model_path
      - calibrator_path (optional)
      - calibration (optional: {a,b,band_bps})
      - ensemble (optional)
      - training_meta_path (optional)
      - raw (the original manifest JSON)
      - git_commit (optional, new)
      - trained_at_utc (optional, new)
      - feature_dim (optional, new)
    """
    latest_path = os.path.abspath(latest_path)
    base_dir = os.path.dirname(latest_path)
    manifest_path, obj = resolve_latest_path(latest_path)
    m_base = os.path.dirname(os.path.abspath(manifest_path))

    # Case A: versioned manifest following schema
    if isinstance(obj, dict) and 'artifacts' in obj:
        artifacts = obj.get('artifacts', {}) or {}
        feature_schema = _abspath(m_base, artifacts.get('feature_schema'))
        meta_model = artifacts.get('meta_model', {}) or {}
        calibrator = artifacts.get('calibrator', {}) or {}
        training_meta = artifacts.get('training_meta')
        out = {
            'feature_schema_path': feature_schema,
            'model_path': _abspath(m_base, meta_model.get('path')),
            'calibrator_path': _abspath(m_base, calibrator.get('path')),
            'training_meta_path': _abspath(m_base, training_meta) if training_meta else None,
            'calibration': obj.get('calibration') or {},
            'ensemble': obj.get('ensemble') or {},
            'raw': obj,
            'manifest_path': manifest_path,
        }
        return out

    # Case B: legacy LATEST.json listing filenames directly
    if isinstance(obj, dict):
        model_path = _abspath(base_dir, obj.get('meta_classifier'))
        calibrator_path = _abspath(base_dir, obj.get('calibrator')) if obj.get('calibrator') else None
        feature_schema_path = _abspath(base_dir, obj.get('feature_columns'))
        training_meta_path = _abspath(base_dir, obj.get('training_meta')) if obj.get('training_meta') else None
        
        # Extract new metadata fields (optional, for enhanced manifests)
        git_commit = obj.get('git_commit')
        trained_at_utc = obj.get('trained_at_utc')
        feature_dim = obj.get('feature_dim')
        
        out = {
            'feature_schema_path': feature_schema_path,
            'model_path': model_path,
            'calibrator_path': calibrator_path,
            'training_meta_path': training_meta_path,
            'calibration': {'a': 0.0, 'b': 1.0},  # defaults unless provided in new manifest
            'ensemble': {},
            'raw': obj,
            'manifest_path': manifest_path,
            # New metadata fields (optional)
            'git_commit': git_commit,
            'trained_at_utc': trained_at_utc,
            'feature_dim': feature_dim,
        }
        return out

    raise ValueError(f"Unrecognized manifest format at {manifest_path}")
