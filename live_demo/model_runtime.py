import json
import os
import sys
from typing import Any, Dict, List, Optional
import joblib
import numpy as np
import pandas as pd

# Ensure custom classes are importable for joblib unpickling
try:
    # Absolute import works when running package-less; package import when installed
    try:
        from live_demo.custom_models import EnhancedMetaClassifier, CustomClassificationCalibrator  # type: ignore
    except ImportError:  # pragma: no cover
        from .custom_models import EnhancedMetaClassifier, CustomClassificationCalibrator  # type: ignore
    # Register in globals to help joblib locate symbols even if pickled under __main__
    globals().setdefault("EnhancedMetaClassifier", EnhancedMetaClassifier)
    globals().setdefault(
        "CustomClassificationCalibrator", CustomClassificationCalibrator
    )
    # Also register in __main__ module to match notebook pickled module path
    try:
        main_mod = sys.modules.get("__main__")
        if main_mod is not None:
            setattr(main_mod, "EnhancedMetaClassifier", EnhancedMetaClassifier)
            setattr(
                main_mod,
                "CustomClassificationCalibrator",
                CustomClassificationCalibrator,
            )
    except (AttributeError, RuntimeError, TypeError):
        pass
except ImportError:
    # Proceed; joblib may still load if artifacts use only sklearn types
    EnhancedMetaClassifier = None  # type: ignore
    CustomClassificationCalibrator = None  # type: ignore

try:
    from live_demo.features import FeaturePipeline  # type: ignore
except ImportError:  # pragma: no cover
    from .features import FeaturePipeline  # type: ignore


class ModelRuntime:
    def __init__(self, manifest_path: str):
        manifest_meta: Dict[str, Any]
        # Support both legacy and versioned manifests via loader
        try:
            try:
                from live_demo.models.manifest_loader import normalize_manifest  # type: ignore
            except ImportError:  # pragma: no cover
                from .models.manifest_loader import normalize_manifest  # type: ignore
            nm = normalize_manifest(manifest_path)
            manifest_meta = dict(nm)
            self.feature_schema_path = nm.get('feature_schema_path')
            self.model_path = nm.get('model_path')
            self.calibrator_path = nm.get('calibrator_path')
            cal = nm.get('calibration') or {}
            self.cal_a = float(cal.get('a', 0.0))
            self.cal_b = float(cal.get('b', 1.0))
        except Exception:
            # Fallback to direct JSON with legacy keys
            with open(manifest_path, 'r', encoding='utf-8') as f:
                m = json.load(f)
            manifest_meta = dict(m)
            base_dir = os.path.dirname(os.path.abspath(manifest_path))
            def abs_path(p: str) -> str:
                return p if os.path.isabs(p) else os.path.join(base_dir, p)
            self.model_path = abs_path(m['meta_classifier'])
            self.calibrator_path = abs_path(m.get('calibrator')) if m.get('calibrator') else None
            self.feature_schema_path = abs_path(m['feature_columns'])
            self.cal_a = 0.0
            self.cal_b = 1.0
        self.feature_pipeline_config: Optional[Dict[str, Any]] = manifest_meta.get("feature_pipeline")
        # Load feature column names for inference-time DataFrame construction
        try:
            with open(self.feature_schema_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict) and "feature_columns" in payload:
                self.columns: List[str] = payload["feature_columns"]
            elif isinstance(payload, dict) and "feature_cols" in payload:
                self.columns = payload["feature_cols"]
            elif isinstance(payload, list):
                self.columns = payload
            else:
                raise ValueError("Invalid feature schema payload")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Fallback to empty; inference will raise if lengths mismatch
            self.columns = []
        try:
            self.model = joblib.load(self.model_path)
        except (ValueError, TypeError, AttributeError, ImportError) as e:
            # Degrade gracefully if custom class from notebook cannot be unpickled
            self.model = None
            print(
                f"[ModelRuntime] Warning: failed to load model '{self.model_path}': {e}"
            )
        try:
            self.calibrator = (
                joblib.load(self.calibrator_path) if self.calibrator_path else None
            )
        except (ValueError, TypeError, AttributeError, ImportError) as e:
            self.calibrator = None
            print(
                f"[ModelRuntime] Warning: failed to load calibrator '{self.calibrator_path}': {e}"
            )
        # class order {down:0, neutral:1, up:2}
        self.class_order = [0, 1, 2]
        self.feature_pipeline = FeaturePipeline(self.columns, self.feature_pipeline_config)

    def infer(self, x: List[float]) -> Dict:
        features = list(x)
        if self.feature_pipeline is not None:
            features = self.feature_pipeline.transform(features)
        # Build DataFrame with proper feature names to avoid sklearn warnings
        if self.columns and len(features) == len(self.columns):
            X_df = pd.DataFrame([features], columns=self.columns)
        else:
            # Fallback to numpy array if schema missing/mismatch
            X_df = None
        X = np.array(features, dtype=float).reshape(1, -1)
        if self.model is None:
            # Neutral, no model available
            proba = np.array([[0.33, 0.34, 0.33]], dtype=float)
        else:
            proba = None
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(X_df if X_df is not None else X)
            elif hasattr(self.model, "decision_function"):
                # Fallback: map decision function to 3-class via heuristic (shouldn't happen)
                df = self.model.decision_function(X_df if X_df is not None else X)
                # naive softmax
                ex = np.exp(df - np.max(df))
                proba = ex / np.sum(ex)
            else:
                raise RuntimeError("Model lacks predict_proba/decision_function")
            if self.calibrator is not None:
                # Calibrator exposes predict_proba(X) taking feature matrix; however our
                # CustomClassificationCalibrator expects raw features to call base_estimator
                # internally. If the loaded calibrator is our custom class, call predict_proba
                # with the original feature vector; otherwise, try transform(proba) as fallback.
                try:
                    if hasattr(self.calibrator, "predict_proba"):
                        proba = self.calibrator.predict_proba(
                            X_df if X_df is not None else X
                        )
                    else:
                        proba = self.calibrator.transform(proba)  # type: ignore[attr-defined]
                except (ValueError, TypeError, AttributeError):
                    # If calibrator application fails, keep uncalibrated probabilities
                    pass
        # Ensure shape (1,3)
        proba = np.asarray(proba).reshape(1, -1)
        if proba.shape[1] != 3:
            raise RuntimeError(f"Expected 3-class probabilities, got {proba.shape}")
        p_down, p_neutral, p_up = proba[0].tolist()
        s_model = float(p_up - p_down)
        return {
        'p_down': float(p_down),
        'p_neutral': float(p_neutral),
        'p_up': float(p_up),
        's_model': s_model,
        # Expose calibration params from artifacts (read-only)
        'a': float(getattr(self, 'cal_a', 0.0)),
        'b': float(getattr(self, 'cal_b', 1.0)),
        }
