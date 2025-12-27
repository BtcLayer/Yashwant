"""
Overlay Signal Generator for Multi-Timeframe Trading System

This module generates trading signals for all timeframes using
the same trained model with overlay features.
"""

from typing import Dict, List, Tuple
import numpy as np
from dataclasses import dataclass
from datetime import datetime

from live_demo.overlay_features import OverlayFeatures
from live_demo.model_runtime import ModelRuntime


@dataclass
class OverlaySignal:
    """Signal from a specific timeframe"""

    timeframe: str
    direction: int  # -1, 0, 1
    alpha: float  # Signal strength [0, 1]
    confidence: float  # Model confidence [0, 1]
    raw_prediction: Dict[str, float]
    features: List[float]
    timestamp: str
    bar_id: int


@dataclass
class OverlaySignalResult:
    """Complete signal result for all timeframes"""

    signals: Dict[str, OverlaySignal]
    timestamp: str
    base_bar_id: int
    model_version: str


class OverlaySignalGenerator:
    """Generates signals for all overlay timeframes using a single model"""

    def __init__(self, model_runtime: ModelRuntime, overlay_feature_computer):
        self.model_runtime = model_runtime
        self.feature_computer = overlay_feature_computer
        
        # Default signal thresholds (can be configured)
        self.thresholds_default: Dict[str, float] = {
            "min_confidence": 0.60,
            "min_alpha": 0.10,
            "neutral_band": 0.05,  # Signals within ±5% are considered neutral
        }
        # Optional per-timeframe threshold overrides, e.g., {"1h": {...}, "12h": {...}}
        self.thresholds_by_timeframe: Dict[str, Dict[str, float]] = {}
        
        # Track signal history for analysis
        self.signal_history: List[OverlaySignalResult] = []
        self.max_history = 1000

    def generate_signals(
        self, cohort_signals: Dict[str, float], base_bar_id: int
    ) -> OverlaySignalResult:
        """Generate signals for all available timeframes"""

        # Compute features for all timeframes
        features_by_timeframe = self.feature_computer.compute_all_timeframe_features(
            cohort_signals
        )

        # Generate signals for each timeframe
        signals = {}
        timestamp = datetime.now().isoformat()

        for timeframe, overlay_features in features_by_timeframe.items():
            signal = self._generate_single_signal(
                timeframe, overlay_features, cohort_signals
            )
            signals[timeframe] = signal

        # Create result object
        result = OverlaySignalResult(
            signals=signals,
            timestamp=timestamp,
            base_bar_id=base_bar_id,
            model_version="overlay_unified",
        )

        # Store in history
        self.signal_history.append(result)
        if len(self.signal_history) > self.max_history:
            self.signal_history.pop(0)

        return result

    def _generate_single_signal(
        self,
        timeframe: str,
        overlay_features: OverlayFeatures,
        cohort_signals: Dict[str, float],
    ) -> OverlaySignal:
        """Generate a signal for a single timeframe"""

        # Validate features
        if not self.feature_computer.validate_features(overlay_features.features):
            return self._create_neutral_signal(timeframe, overlay_features)

        # Get model prediction
        try:
            prediction = self.model_runtime.infer(overlay_features.features)
        except Exception as e:
            print(
                f"[OverlaySignalGenerator] Error in model inference for {timeframe}: {e}"
            )
            return self._create_neutral_signal(timeframe, overlay_features)

        # Extract signal components
        p_up = prediction['p_up']
        p_down = prediction['p_down']
        p_neutral = prediction['p_neutral']
        s_model = prediction['s_model']
        
        # Calculate signal direction and strength using per-timeframe thresholds if provided
        thr = self._get_thresholds_for_timeframe(timeframe)
        direction, alpha, confidence = self._calculate_signal_components_with_thresholds(
            p_up, p_down, p_neutral, s_model, thr
        )

        return OverlaySignal(
            timeframe=timeframe,
            direction=direction,
            alpha=alpha,
            confidence=confidence,
            raw_prediction=prediction,
            features=overlay_features.features,
            timestamp=overlay_features.timestamp,
            bar_id=overlay_features.bar_id,
        )

    def _calculate_signal_components_with_thresholds(self, p_up: float, p_down: float,
                                   p_neutral: float, s_model: float, thr: Dict[str, float]) -> Tuple[int, float, float]:
        """Calculate signal direction, alpha, and confidence with explicit thresholds"""
        # Calculate confidence as max probability
        confidence = max(p_up, p_down, p_neutral)
        # Determine direction based on model signal
        neutral_band = float(thr.get("neutral_band", self.thresholds_default["neutral_band"]))
        min_conf = float(thr.get("min_confidence", self.thresholds_default["min_confidence"]))
        min_alpha = float(thr.get("min_alpha", self.thresholds_default["min_alpha"]))

        if abs(s_model) < neutral_band:
            direction = 0
            alpha = 0.0
        elif s_model > 0:
            direction = 1
            alpha = min(1.0, abs(s_model))
        else:
            direction = -1
            alpha = min(1.0, abs(s_model))

        # Apply minimum thresholds
        if confidence < min_conf:
            direction = 0
            alpha = 0.0

        if alpha < min_alpha:
            direction = 0
            alpha = 0.0

        return direction, alpha, confidence
    
    def _calculate_signal_components(self, p_up: float, p_down: float,
                                   p_neutral: float, s_model: float) -> Tuple[int, float, float]:
        """Calculate signal direction, alpha, and confidence (legacy method)"""
        return self._calculate_signal_components_with_thresholds(
            p_up, p_down, p_neutral, s_model, self.thresholds_default
        )

    def _create_neutral_signal(
        self, timeframe: str, overlay_features: OverlayFeatures
    ) -> OverlaySignal:
        """Create a neutral signal when model inference fails"""
        return OverlaySignal(
            timeframe=timeframe,
            direction=0,
            alpha=0.0,
            confidence=0.0,
            raw_prediction={
                "p_up": 0.33,
                "p_down": 0.33,
                "p_neutral": 0.34,
                "s_model": 0.0,
            },
            features=overlay_features.features,
            timestamp=overlay_features.timestamp,
            bar_id=overlay_features.bar_id,
        )

    def get_signal_summary(
        self, timeframe: str, lookback: int = 100
    ) -> Dict[str, float]:
        """Get summary statistics for a specific timeframe"""
        if not self.signal_history:
            return {}

        # Get recent signals for the timeframe
        recent_signals = []
        for result in self.signal_history[-lookback:]:
            if timeframe in result.signals:
                recent_signals.append(result.signals[timeframe])

        if not recent_signals:
            return {}

        # Calculate statistics
        directions = [s.direction for s in recent_signals]
        alphas = [s.alpha for s in recent_signals]
        confidences = [s.confidence for s in recent_signals]

        return {
            "avg_direction": np.mean(directions),
            "avg_alpha": np.mean(alphas),
            "avg_confidence": np.mean(confidences),
            "signal_count": len(recent_signals),
            "non_zero_signals": sum(1 for d in directions if d != 0),
            "hit_rate": (
                sum(1 for d in directions if d != 0) / len(directions)
                if directions
                else 0.0
            ),
        }

    def get_all_timeframe_summary(
        self, lookback: int = 100
    ) -> Dict[str, Dict[str, float]]:
        """Get summary statistics for all timeframes"""
        summary = {}

        for timeframe in ["5m", "15m", "1h"]:
            summary[timeframe] = self.get_signal_summary(timeframe, lookback)

        return summary
    def _get_thresholds_for_timeframe(self, timeframe: str) -> Dict[str, float]:
        """Resolve thresholds for a specific timeframe by merging default and override"""
        base = dict(self.thresholds_default)
        override = self.thresholds_by_timeframe.get(str(timeframe), {}) or {}
        try:
            base.update({k: float(v) for k, v in override.items() if k in base})
        except Exception:
            base.update({k: v for k, v in override.items() if k in base})
        return base

    def update_thresholds(self, new_thresholds: Dict[str, float | Dict[str, float]]):
        """Update signal thresholds. Accepts either flat dict or per-timeframe mapping.

        Examples:
          {"min_confidence": 0.62, "min_alpha": 0.12, "neutral_band": 0.055}
          {"default": {...}, "5m": {...}, "1h": {...}, "12h": {...}}
        """
        if not isinstance(new_thresholds, dict):
            return
        # Per-timeframe structure
        tf_keys = {"1m","3m","5m","15m","30m","1h","2h","4h","12h","1d"}
        has_tf_keys = any((k in tf_keys) for k in new_thresholds.keys()) or ("default" in new_thresholds)
        if has_tf_keys:
            # Update default first if provided
            if isinstance(new_thresholds.get("default"), dict):
                try:
                    self.thresholds_default.update({
                        k: float(v) for k, v in new_thresholds["default"].items() if k in self.thresholds_default
                    })
                except Exception:
                    self.thresholds_default.update({
                        k: new_thresholds["default"][k] for k in self.thresholds_default.keys() if k in new_thresholds["default"]
                    })
            # Build per-timeframe map
            per_tf: Dict[str, Dict[str, float]] = {}
            for k, v in new_thresholds.items():
                if k == "default":
                    continue
                if k in tf_keys and isinstance(v, dict):
                    per_tf[k] = {
                        kk: float(vv) if isinstance(vv, (int, float)) else vv
                        for kk, vv in v.items() if kk in self.thresholds_default
                    }
            self.thresholds_by_timeframe = per_tf
        else:
            # Flat dict: update default thresholds only
            try:
                self.thresholds_default.update({
                    k: float(v) for k, v in new_thresholds.items() if k in self.thresholds_default
                })
            except Exception:
                self.thresholds_default.update({k: new_thresholds[k] for k in self.thresholds_default.keys() if k in new_thresholds})
    def get_model_info(self) -> Dict[str, str]:
        """Get information about the loaded model"""
        return {
            "model_path": getattr(self.model_runtime, "model_path", "unknown"),
            "feature_schema_path": getattr(
                self.model_runtime, "feature_schema_path", "unknown"
            ),
            "calibrator_path": getattr(self.model_runtime, "calibrator_path", "none"),
        }
