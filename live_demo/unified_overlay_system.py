"""
Unified Overlay System for Multi-Timeframe Trading

This module integrates all overlay components into a single system
that can replace the separate bot architecture.
"""

from typing import Dict, List, Optional, Any
import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
import pytz

from live_demo.overlay_manager import OverlayManager, OverlayConfig, BarData
from live_demo.overlay_features import OverlayFeatureComputer
from live_demo.overlay_signal_generator import OverlaySignalGenerator
from live_demo.enhanced_signal_combiner import EnhancedSignalCombiner
from live_demo.model_runtime import ModelRuntime
from live_demo.features import LiveFeatureComputer

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class OverlaySystemConfig:
    """Configuration for the unified overlay system"""

    enable_overlays: bool = True
    base_timeframe: str = "5m"
    overlay_timeframes: List[str] = None
    rollup_windows: Dict[str, int] = None
    alignment_rules: Dict[str, Any] = None
    timeframe_weights: Dict[str, float] = None
    model_manifest_path: str = "live_demo/models/LATEST.json"
    # Optional per-timeframe signal thresholds configuration
    signal_thresholds: Dict[str, Any] = None
    # Ensemble 1.1: Shadow mode for safe observation
    shadow_mode: bool = False
    veto_confidence_threshold: float = 0.15  # Min confidence to allow trade
    veto_on_timeframe_conflict: bool = True  # Veto when 5m vs 15m conflict

    def __post_init__(self):
        if self.overlay_timeframes is None:
            self.overlay_timeframes = ["15m", "1h"]
        if self.rollup_windows is None:
            self.rollup_windows = {"15m": 3, "1h": 12}
        if self.alignment_rules is None:
            # Alignment rules include exact behavior knobs consumed by combiner and main.py
            self.alignment_rules = {
                "require_5m_15m_agreement": True,
                "allow_1h_override": True,
                "neutral_1h_override": True,
                # Prompt-aligned exact policy:
                # - Full size when 5m & 15m agree
                # - Size × 0.5 if 1h disagrees
                # - If 5m opposes 15m, skip unless |calibrated_pred_bps| > conflict_band_mult × band_bps
                "halve_on_1h_opposition": True,
                "conflict_band_mult": 2.0
            }
        if self.timeframe_weights is None:
            self.timeframe_weights = {"5m": 0.5, "15m": 0.3, "1h": 0.2}


@dataclass
class OverlayDecision:
    """Final decision from the overlay system"""

    direction: int  # -1, 0, 1
    alpha: float  # Signal strength [0, 1]
    confidence: float  # Combined confidence [0, 1]
    chosen_timeframes: List[str]
    alignment_rule: str
    individual_signals: Dict[str, Any]
    reasoning: str
    timestamp: str
    bar_id: int
    # Ensemble 1.1: Shadow mode fields
    overlay_would_veto: bool = False
    overlay_veto_reason: Optional[str] = None


class UnifiedOverlaySystem:
    """Unified system for multi-timeframe trading with overlays"""

    def __init__(self, config: OverlaySystemConfig):
        self.config = config

        # Initialize components
        self.overlay_config = OverlayConfig(
            base_timeframe=config.base_timeframe,
            overlay_timeframes=config.overlay_timeframes,
            rollup_windows=config.rollup_windows,
            alignment_rules=config.alignment_rules,
        )

        self.overlay_manager = OverlayManager(self.overlay_config)

        # Initialize feature computer (will be set up with base computer)
        self.feature_computer = None

        # Initialize model runtime
        try:
            self.model_runtime = ModelRuntime(config.model_manifest_path)
        except Exception as e:
            print(f"[UnifiedOverlaySystem] Error loading model: {e}")
            self.model_runtime = None

        # Initialize signal generator and combiner
        self.signal_generator = None
        self.signal_combiner = None

        # Decision history
        self.decision_history: List[OverlayDecision] = []
        self.max_history = 1000

        # System status
        self.is_initialized = False
        self.last_update_time = None
        
        # Ensemble 1.1: Shadow mode tracking
        self.veto_count = 0
        self.total_decisions = 0

    def initialize(self, base_feature_computer: LiveFeatureComputer):
        """Initialize the overlay system with base feature computer"""
        try:
            self.feature_computer = OverlayFeatureComputer(
                base_feature_computer, self.overlay_manager
            )

            if self.model_runtime:
                self.signal_generator = OverlaySignalGenerator(
                    self.model_runtime, self.feature_computer
                )
                # Apply per-timeframe thresholds if provided in config
                try:
                    if self.config.signal_thresholds:
                        self.signal_generator.update_thresholds(self.config.signal_thresholds)
                except Exception:
                    pass
                
                self.signal_combiner = EnhancedSignalCombiner({
                    'timeframe_weights': self.config.timeframe_weights,
                    'alignment_rules': self.config.alignment_rules
                })
            
            
            self.is_initialized = True
            print("[UnifiedOverlaySystem] System initialized successfully")

        except Exception as e:
            print(f"[UnifiedOverlaySystem] Initialization failed: {e}")
            self.is_initialized = False

    def add_market_data(self, bar_data: Dict[str, Any]) -> Dict[str, Optional[BarData]]:
        """Add new market data and generate overlay bars"""
        try:
            # Helper to coerce None/invalid to a numeric default
            def _nz(v: Any, default: float = 0.0) -> float:
                try:
                    return default if v is None else float(v)
                except (TypeError, ValueError):
                    return default

            # Convert dict to BarData
            bar = BarData(
                timestamp=datetime.fromisoformat(bar_data['timestamp'].replace('Z', '+00:00')),
                bar_id=int(bar_data['bar_id']),
                open=_nz(bar_data.get('open')),
                high=_nz(bar_data.get('high')),
                low=_nz(bar_data.get('low')),
                close=_nz(bar_data.get('close')),
                volume=_nz(bar_data.get('volume')),
                funding=_nz(bar_data.get('funding', 0.0)),
                spread_bps=_nz(bar_data.get('spread_bps', 0.0)),
                rv_1h=_nz(bar_data.get('rv_1h', 0.0))
            )

            # Add to overlay manager
            overlay_bars = self.overlay_manager.add_bar(bar)

            self.last_update_time = datetime.now(IST)
            return overlay_bars

        except Exception as e:
            print(f"[UnifiedOverlaySystem] Error adding market data: {e}")
            return {}

    def generate_decision(
        self, cohort_signals: Dict[str, float], base_bar_id: int
    ) -> OverlayDecision:
        """Generate a trading decision using overlay signals.
        
        Ensemble 1.1: Includes shadow mode veto checking.
        """

        if (
            not self.is_initialized
            or not self.signal_generator
            or not self.signal_combiner
        ):
            return self._create_neutral_decision(base_bar_id, "System not initialized")

        try:
            # Generate signals for all timeframes
            signal_result = self.signal_generator.generate_signals(
                cohort_signals, base_bar_id
            )

            # Combine signals using alignment rules
            combined_signal = self.signal_combiner.combine_signals(signal_result)

            # Convert to decision format
            decision = OverlayDecision(
                direction=combined_signal.direction,
                alpha=combined_signal.alpha,
                confidence=combined_signal.confidence,
                chosen_timeframes=combined_signal.chosen_timeframes,
                alignment_rule=combined_signal.alignment_rule,
                individual_signals={
                    tf: {
                        "direction": sig.direction,
                        "alpha": sig.alpha,
                        "confidence": sig.confidence,
                    }
                    for tf, sig in combined_signal.individual_signals.items()
                },
                reasoning=combined_signal.reasoning,
                timestamp=datetime.now(IST).isoformat(),
                bar_id=base_bar_id,
            )
            
            # Ensemble 1.1: Check veto conditions
            self.total_decisions += 1
            would_veto, veto_reason = self._check_veto_conditions(decision, combined_signal)
            
            decision.overlay_would_veto = would_veto
            decision.overlay_veto_reason = veto_reason
            
            if would_veto:
                self.veto_count += 1
                
                if self.config.shadow_mode:
                    # Shadow mode: Log but don't enforce
                    print(
                        f"[OVERLAY_SHADOW] Would veto trade: {veto_reason} "
                        f"(dir={decision.direction}, alpha={decision.alpha:.4f}, "
                        f"conf={decision.confidence:.4f}, veto_rate={self.veto_count}/{self.total_decisions})"
                    )
                else:
                    # Production mode: Enforce veto
                    print(
                        f"[OVERLAY_VETO] Trade vetoed: {veto_reason} "
                        f"(dir={decision.direction}, alpha={decision.alpha:.4f}, conf={decision.confidence:.4f})"
                    )
                    # Override decision to neutral
                    decision.direction = 0
                    decision.alpha = 0.0
                    decision.reasoning = f"VETOED: {veto_reason}"

            # Store in history
            self.decision_history.append(decision)
            if len(self.decision_history) > self.max_history:
                self.decision_history.pop(0)

            return decision

        except Exception as e:
            print(f"[UnifiedOverlaySystem] Error generating decision: {e}")
            return self._create_neutral_decision(base_bar_id, f"Error: {str(e)}")

    def _check_veto_conditions(self, decision: OverlayDecision, combined_signal: Any) -> tuple[bool, Optional[str]]:
        """Check if trade should be vetoed.
        
        Ensemble 1.1: Veto conditions:
        1. Low confidence (< threshold)
        2. Timeframe conflict (5m vs 15m disagreement)
        3. Missing critical timeframes
        
        Returns:
            (should_veto, reason)
        """
        # Skip veto check for neutral decisions
        if decision.direction == 0:
            return False, None
        
        # Condition 1: Low confidence
        if decision.confidence < self.config.veto_confidence_threshold:
            return True, f"low_overlay_confidence_{decision.confidence:.3f}"
        
        # Condition 2: Timeframe conflict (5m vs 15m)
        if self.config.veto_on_timeframe_conflict:
            signals_5m = decision.individual_signals.get("5m", {})
            signals_15m = decision.individual_signals.get("15m", {})
            
            if signals_5m and signals_15m:
                dir_5m = signals_5m.get("direction", 0)
                dir_15m = signals_15m.get("direction", 0)
                
                # Veto if 5m and 15m point in opposite directions
                if dir_5m != 0 and dir_15m != 0 and dir_5m != dir_15m:
                    return True, f"timeframe_conflict_5m({dir_5m})_vs_15m({dir_15m})"
        
        # Condition 3: Missing critical timeframes
        if not decision.chosen_timeframes or len(decision.chosen_timeframes) == 0:
            return True, "no_timeframes_chosen"
        
        # All checks passed
        return False, None
    
    def _create_neutral_decision(self, bar_id: int, reason: str) -> OverlayDecision:
        """Create a neutral decision when system fails"""
        return OverlayDecision(
            direction=0,
            alpha=0.0,
            confidence=0.0,
            chosen_timeframes=[],
            alignment_rule="neutral",
            individual_signals={},
            reasoning=reason,
            timestamp=datetime.now(IST).isoformat(),
            bar_id=bar_id,
            overlay_would_veto=False,
            overlay_veto_reason=None,
        )

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "is_initialized": self.is_initialized,
            "last_update_time": (
                self.last_update_time.isoformat() if self.last_update_time else None
            ),
            "model_loaded": self.model_runtime is not None,
            "timeframe_status": {},
            "decision_count": len(self.decision_history),
            "config": {
                "base_timeframe": self.config.base_timeframe,
                "overlay_timeframes": self.config.overlay_timeframes,
                "rollup_windows": self.config.rollup_windows,
                "timeframe_weights": self.config.timeframe_weights,
            },
        }

        # Check timeframe readiness
        for timeframe in ["5m"] + self.config.overlay_timeframes:
            status["timeframe_status"][timeframe] = {
                "bar_count": self.overlay_manager.get_bar_count(timeframe),
                "is_ready": self.overlay_manager.is_timeframe_ready(timeframe),
                "last_bar_id": self.overlay_manager.last_bar_ids.get(timeframe, 0),
            }

        return status

    def get_performance_stats(self, lookback: int = 100) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.decision_history:
            return {}

        recent_decisions = self.decision_history[-lookback:]

        directions = [d.direction for d in recent_decisions]
        alphas = [d.alpha for d in recent_decisions]
        confidences = [d.confidence for d in recent_decisions]

        # Rule usage statistics
        rule_counts = {}
        for decision in recent_decisions:
            rule = decision.alignment_rule
            rule_counts[rule] = rule_counts.get(rule, 0) + 1

        return {
            "total_decisions": len(recent_decisions),
            "avg_direction": sum(directions) / len(directions) if directions else 0.0,
            "avg_alpha": sum(alphas) / len(alphas) if alphas else 0.0,
            "avg_confidence": (
                sum(confidences) / len(confidences) if confidences else 0.0
            ),
            "non_zero_decisions": sum(1 for d in directions if d != 0),
            "hit_rate": (
                sum(1 for d in directions if d != 0) / len(directions)
                if directions
                else 0.0
            ),
            "rule_usage": rule_counts,
        }

    def get_timeframe_signals(self, lookback: int = 50) -> Dict[str, Dict[str, float]]:
        """Get signal statistics for each timeframe"""
        if not self.signal_generator:
            return {}

        return self.signal_generator.get_all_timeframe_summary(lookback)

    def update_config(self, new_config: Dict[str, Any]):
        """Update system configuration"""
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Reinitialize components if needed
        if "timeframe_weights" in new_config and self.signal_combiner:
            self.signal_combiner.timeframe_weights = new_config["timeframe_weights"]

    def export_state(self) -> Dict[str, Any]:
        """Export current system state for persistence"""
        return {
            "config": {
                "base_timeframe": self.config.base_timeframe,
                "overlay_timeframes": self.config.overlay_timeframes,
                "rollup_windows": self.config.rollup_windows,
                "timeframe_weights": self.config.timeframe_weights,
                "model_manifest_path": self.config.model_manifest_path,
            },
            "last_bar_ids": self.overlay_manager.last_bar_ids,
            "last_update_time": (
                self.last_update_time.isoformat() if self.last_update_time else None
            ),
            "decision_count": len(self.decision_history),
        }

    def import_state(self, state: Dict[str, Any]):
        """Import system state from persistence"""
        try:
            # Restore bar IDs
            if "last_bar_ids" in state:
                self.overlay_manager.last_bar_ids.update(state["last_bar_ids"])

            # Restore last update time
            if "last_update_time" in state and state["last_update_time"]:
                self.last_update_time = datetime.fromisoformat(
                    state["last_update_time"]
                )

            print("[UnifiedOverlaySystem] State imported successfully")

        except Exception as e:
            print(f"[UnifiedOverlaySystem] Error importing state: {e}")
