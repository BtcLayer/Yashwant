import json
import os
import sys
from typing import Dict, List
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

# Import EnsembleWrapper for 1h model compatibility
try:
    try:
        from live_demo_1h.ensemble_wrapper import EnsembleWrapper  # type: ignore
    except ImportError:
        import sys
        import os
        # Try adding live_demo_1h to path
        live_demo_1h_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'live_demo_1h')
        if os.path.exists(live_demo_1h_path):
            sys.path.insert(0, live_demo_1h_path)
            from ensemble_wrapper import EnsembleWrapper  # type: ignore
    globals().setdefault("EnsembleWrapper", EnsembleWrapper)
    # Register in __main__ for pickle compatibility
    try:
        main_mod = sys.modules.get("__main__")
        if main_mod is not None:
            setattr(main_mod, "EnsembleWrapper", EnsembleWrapper)
    except (AttributeError, RuntimeError, TypeError):
        pass
except ImportError:
    EnsembleWrapper = None  # type: ignore


class ModelRuntime:
    def __init__(self, manifest_path: str):
        # Support both legacy and versioned manifests via loader
        try:
            try:
                from live_demo.models.manifest_loader import normalize_manifest  # type: ignore
            except ImportError:  # pragma: no cover
                from .models.manifest_loader import normalize_manifest  # type: ignore
            nm = normalize_manifest(manifest_path)
            self.feature_schema_path = nm.get('feature_schema_path')
            self.model_path = nm.get('model_path')
            self.calibrator_path = nm.get('calibrator_path')
            cal = nm.get('calibration') or {}
            self.cal_a = float(cal.get('a', 0.0))
            self.cal_b = float(cal.get('b', 1.0))
            
            # Extract new metadata fields (optional)
            self.git_commit = nm.get('git_commit')
            self.trained_at_utc = nm.get('trained_at_utc')
            self.expected_feature_dim = nm.get('feature_dim')
            
            # Log metadata if available
            if self.git_commit:
                print(f"[ModelRuntime] Model git commit: {self.git_commit}")
            if self.trained_at_utc:
                print(f"[ModelRuntime] Model trained at: {self.trained_at_utc}")
                
        except Exception:
            # Fallback to direct JSON with legacy keys
            with open(manifest_path, 'r', encoding='utf-8') as f:
                m = json.load(f)
            base_dir = os.path.dirname(os.path.abspath(manifest_path))
            def abs_path(p: str) -> str:
                return p if os.path.isabs(p) else os.path.join(base_dir, p)
            self.model_path = abs_path(m['meta_classifier'])
            self.calibrator_path = abs_path(m.get('calibrator')) if m.get('calibrator') else None
            self.feature_schema_path = abs_path(m['feature_columns'])
            self.cal_a = 0.0
            self.cal_b = 1.0
            
            # Metadata fields not available in fallback mode
            self.git_commit = None
            self.trained_at_utc = None
            self.expected_feature_dim = None
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
                
            # Validate feature dimension if expected_feature_dim is set
            if self.expected_feature_dim is not None:
                actual_dim = len(self.columns)
                if actual_dim != self.expected_feature_dim:
                    print(
                        f"[ModelRuntime] WARNING: Feature dimension mismatch! "
                        f"Expected {self.expected_feature_dim}, got {actual_dim}"
                    )
                else:
                    print(f"[ModelRuntime] Feature dimension validated: {actual_dim} features")
                    
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

    def infer(self, x: List[float]) -> Dict:
        # Build DataFrame with proper feature names if columns are available
        # October model (with calibration) expects DataFrames with feature names
        # Jan model (no calibration) expects numpy arrays
        if self.columns and len(x) == len(self.columns):
            X_df = pd.DataFrame([x], columns=self.columns)
            X = X_df  # Use DataFrame for models trained with feature names
        else:
            # Fallback to numpy array if schema missing/mismatch
            X = np.array(x, dtype=float).reshape(1, -1)
        
        if self.model is None:
            # Neutral, no model available
            proba = np.array([[0.33, 0.34, 0.33]], dtype=float)
        else:
            proba = None
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(X)
            elif hasattr(self.model, "decision_function"):
                # Fallback: map decision function to 3-class via heuristic (shouldn't happen)
                df = self.model.decision_function(X)
                # naive softmax
                ex = np.exp(df - np.max(df))
                proba = ex / np.sum(ex)
            else:
                raise RuntimeError("Model lacks predict_proba/decision_function")

            # Calibrator retrained 2026-02-26: old CalibrationWrapper (Platt) was inverting
            # probabilities; replaced with identity passthrough. Safe to re-enable.
            if self.calibrator is not None:
                calibrated_proba = None
                
                # Attempt 1: Try calling with raw probabilities (for sklearn CalibrationWrapper)
                try:
                    if hasattr(self.calibrator, "predict_proba"):
                        calibrated_proba = self.calibrator.predict_proba(proba)
                    elif hasattr(self.calibrator, "transform"):
                        calibrated_proba = self.calibrator.transform(proba)
                except Exception as e:
                    print(f"[ModelRuntime] Warning: Calibrator failed with raw probabilities: {e}")

                # Attempt 2: If first failed, try calling with original features (for CustomClassificationCalibrator)
                if calibrated_proba is None:
                    try:
                        if CustomClassificationCalibrator is not None and isinstance(self.calibrator, CustomClassificationCalibrator):
                            calibrated_proba = self.calibrator.predict_proba(X)
                        elif hasattr(self.calibrator, "predict_proba"): # Generic fallback for predict_proba with X
                            calibrated_proba = self.calibrator.predict_proba(X)
                    except Exception as e:
                        print(f"[ModelRuntime] Warning: Calibrator failed with original features: {e}")

                if calibrated_proba is not None:
                    proba = calibrated_proba
                else:
                    print("[ModelRuntime] Warning: Calibrator application failed after all attempts. Using uncalibrated probabilities.")

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
