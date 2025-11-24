"""
Overlay Feature Computer for Multi-Timeframe Trading System

This module extends the existing feature computation to work with
multiple timeframes using rollup overlays.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import deque
import math
from dataclasses import dataclass

from live_demo.overlay_manager import OverlayManager, BarData
from live_demo.features import LiveFeatureComputer


@dataclass
class OverlayFeatures:
    """Features computed for a specific timeframe"""

    timeframe: str
    features: List[float]
    feature_names: List[str]
    timestamp: str
    bar_id: int


class OverlayFeatureComputer:
    """Extended feature computer for overlay timeframes"""

    def __init__(
        self,
        base_feature_computer: LiveFeatureComputer,
        overlay_manager: OverlayManager,
    ):
        self.base_computer = base_feature_computer
        self.overlay_manager = overlay_manager

        # Feature column names (from the model schema)
        self.feature_columns = [
            "mom_1",
            "mom_3",
            "mr_ema20_z",
            "rv_1h",
            "regime_high_vol",
            "gk_volatility",
            "jump_magnitude",
            "volume_intensity",
            "price_efficiency",
            "price_volume_corr",
            "vwap_momentum",
            "depth_proxy",
            "funding_rate",
            "funding_momentum_1h",
            "flow_diff",
            "S_top",
            "S_bot",
        ]

        # Overlay-specific feature histories
        self.overlay_histories: Dict[str, Dict[str, deque]] = {}
        for timeframe in ["5m", "15m", "1h"]:
            self.overlay_histories[timeframe] = {
                "closes": deque(maxlen=100),
                "highs": deque(maxlen=100),
                "lows": deque(maxlen=100),
                "volumes": deque(maxlen=100),
                "funding": deque(maxlen=100),
            }

    def compute_overlay_features(
        self, timeframe: str, bars: List[BarData], cohort_signals: Dict[str, float]
    ) -> OverlayFeatures:
        """Compute features for a specific timeframe"""

        if not bars:
            # Return neutral features if no bars available
            neutral_features = [0.0] * len(self.feature_columns)
            return OverlayFeatures(
                timeframe=timeframe,
                features=neutral_features,
                feature_names=self.feature_columns,
                timestamp=bars[-1].timestamp.isoformat() if bars else "",
                bar_id=bars[-1].bar_id if bars else 0,
            )

        # Update overlay histories
        self._update_overlay_history(timeframe, bars)

        # Convert bars to the format expected by base feature computer
        bar_data = self._convert_bars_to_dict(bars)

        # Compute base features using the existing feature computer
        base_features = self.base_computer.update_and_build(
            bar_data, cohort_signals, bars[-1].funding
        )

        # Ensure we have the right number of features
        if len(base_features) != len(self.feature_columns):
            # Pad or truncate to match expected feature count
            if len(base_features) < len(self.feature_columns):
                base_features.extend(
                    [0.0] * (len(self.feature_columns) - len(base_features))
                )
            else:
                base_features = base_features[: len(self.feature_columns)]

        return OverlayFeatures(
            timeframe=timeframe,
            features=base_features,
            feature_names=self.feature_columns,
            timestamp=bars[-1].timestamp.isoformat(),
            bar_id=bars[-1].bar_id,
        )

    def _update_overlay_history(self, timeframe: str, bars: List[BarData]):
        """Update the feature history for a specific timeframe"""
        history = self.overlay_histories[timeframe]

        for bar in bars:
            history["closes"].append(bar.close)
            history["highs"].append(bar.high)
            history["lows"].append(bar.low)
            history["volumes"].append(bar.volume)
            history["funding"].append(bar.funding)

    def _convert_bars_to_dict(self, bars: List[BarData]) -> Dict:
        """Convert BarData objects to dictionary format expected by base feature computer"""
        if not bars:
            return {}

        latest_bar = bars[-1]

        return {
            "close": latest_bar.close,
            "high": latest_bar.high,
            "low": latest_bar.low,
            "volume": latest_bar.volume,
            "funding": latest_bar.funding,
            "spread_bps": latest_bar.spread_bps,
            "rv_1h": latest_bar.rv_1h,
        }

    def compute_all_timeframe_features(
        self, cohort_signals: Dict[str, float]
    ) -> Dict[str, OverlayFeatures]:
        """Compute features for all available timeframes"""
        features_by_timeframe = {}

        # Compute features for base timeframe (5m)
        # Be permissive at startup: consider 5m ready as soon as at least 1 bar exists
        if self.overlay_manager.is_timeframe_ready("5m", min_bars=1):
            bars_5m = self.overlay_manager.get_latest_bars("5m")
            features_by_timeframe["5m"] = self.compute_overlay_features(
                "5m", bars_5m, cohort_signals
            )

        # Compute features for overlay timeframes
        for timeframe in self.overlay_manager.config.overlay_timeframes:
            # For rolled-up timeframes, begin emitting as soon as the first rollup bar exists
            if self.overlay_manager.is_timeframe_ready(timeframe, min_bars=1):
                bars = self.overlay_manager.get_latest_bars(timeframe)
                features_by_timeframe[timeframe] = self.compute_overlay_features(
                    timeframe, bars, cohort_signals
                )

        return features_by_timeframe

    def get_feature_schema(self) -> Dict[str, str]:
        """Get the feature schema for model inference"""
        return {
            "feature_cols": self.feature_columns,
            "schema_hash": "overlay_unified",
            "timeframes": ["5m", "15m", "1h"],
            "total_features": len(self.feature_columns),
        }

    def validate_features(self, features: List[float]) -> bool:
        """Validate that features are in the expected format"""
        if len(features) != len(self.feature_columns):
            return False

        # Check for NaN or infinite values
        for feature in features:
            if (
                not isinstance(feature, (int, float))
                or math.isnan(feature)
                or math.isinf(feature)
            ):
                return False

        return True
