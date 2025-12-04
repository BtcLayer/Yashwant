import json

import numpy as np
import pytest

from live_demo.features import FeaturePipeline
from live_demo.model_runtime import ModelRuntime
from live_demo.models import manifest_loader


class DummyModel:
    def __init__(self):
        self.last_matrix = None

    def predict_proba(self, X):
        self.last_matrix = X
        return np.array([[0.1, 0.2, 0.7]])


def test_feature_pipeline_standardize_and_clip():
    cfg = {
        "type": "standardize",
        "stats": {
            "mean": {"f1": 1.0, "f2": 0.0},
            "std": {"f1": 2.0, "f2": 4.0},
        },
        "clip": [-1.0, 1.0],
    }
    pipeline = FeaturePipeline(["f1", "f2", "f3"], cfg)
    transformed = pipeline.transform([3.0, -2.0, 10.0])
    assert transformed == pytest.approx([1.0, -0.5, 1.0])


def test_model_runtime_applies_feature_pipeline(tmp_path, monkeypatch):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({"feature_cols": ["f1", "f2"]}), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    pipeline_cfg = {
        "type": "standardize",
        "stats": {
            "mean": {"f1": 1.0, "f2": 0.0},
            "std": {"f1": 2.0, "f2": 4.0},
        },
    }

    def fake_normalize(_: str):
        return {
            "feature_schema_path": str(schema_path),
            "model_path": str(tmp_path / "model.pkl"),
            "calibrator_path": None,
            "calibration": {"a": 0.0, "b": 1.0},
            "feature_pipeline": pipeline_cfg,
        }

    dummy_model = DummyModel()
    monkeypatch.setattr(manifest_loader, "normalize_manifest", fake_normalize)
    monkeypatch.setattr("live_demo.model_runtime.joblib.load", lambda path: dummy_model)

    runtime = ModelRuntime(str(manifest_path))
    runtime.infer([1.0, 4.0])

    assert hasattr(dummy_model, "last_matrix")
    assert list(dummy_model.last_matrix.iloc[0]) == pytest.approx([0.0, 1.0])
