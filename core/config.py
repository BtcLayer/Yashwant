"""Small config helper for strategy metadata.

This is intentionally tiny and non-invasive: it reads environment variables
STRATEGY_ID and SCHEMA_VERSION when present, otherwise falls back to safe defaults.
This is useful for injecting metadata into logs without changing runtime behavior.
"""
import os


def get_strategy_id() -> str:
    return os.environ.get("STRATEGY_ID", "ensemble_1_0")


def get_schema_version() -> str:
    return os.environ.get("SCHEMA_VERSION", "v1")
"""Central config utilities for strategy defaults and runtime overrides.

This module reads config/ensemble_config.json when present and provides
helpers to fetch thresholds and strategy metadata. It is intentionally
lightweight and falls back to sensible defaults for backward compatibility.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any


_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PATH = _ROOT / "config" / "ensemble_config.json"


def _load_raw() -> Dict[str, Any]:
    # Accept JSON from env (STRATEGY_CONFIG) or file (config/ensemble_config.json)
    env = os.environ.get("STRATEGY_CONFIG")
    if env:
        try:
            return json.loads(env)
        except Exception:
            pass
    try:
        if _DEFAULT_PATH.exists():
            return json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


_RAW = _load_raw()


def get_strategy_id() -> str:
    return os.environ.get("STRATEGY_ID") or _RAW.get("strategy_id") or "ensemble_1_0"


def get_schema_version() -> str:
    return os.environ.get("SCHEMA_VERSION") or _RAW.get("schema_version") or "v1"


def get_thresholds() -> Dict[str, Any]:
    default = {
        "S_MIN": 0.12,
        "M_MIN": 0.12,
        "CONF_MIN": 0.60,
        "ALPHA_MIN": 0.10,
        "flip_mood": True,
        "flip_model": True,
        "flip_model_bma": True,
        "allow_model_only_when_mood_neutral": True,
    }
    th = _RAW.get("thresholds", {})
    merged = {**default, **(th or {})}
    # Ensure types
    for k in ["S_MIN", "M_MIN", "CONF_MIN", "ALPHA_MIN"]:
        try:
            merged[k] = float(merged.get(k, default[k]))
        except Exception:
            merged[k] = default[k]
    for k in ["flip_mood", "flip_model", "flip_model_bma", "allow_model_only_when_mood_neutral"]:
        merged[k] = bool(merged.get(k, default[k]))
    return merged
