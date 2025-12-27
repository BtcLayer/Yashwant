"""
Enhanced Signal Combiner for Multi-Timeframe Trading System

This module implements sophisticated signal combination logic with
alignment rules and timeframe coordination.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from enum import Enum

from live_demo.overlay_signal_generator import OverlaySignal, OverlaySignalResult


class AlignmentRule(Enum):
    """Types of alignment rules"""

    AGREEMENT = "agreement"  # All timeframes must agree
    NEUTRAL_OVERRIDE = "neutral_override"  # Neutral timeframe overrides others
    THRESHOLD = "threshold"  # Signal must exceed threshold
    WEIGHTED_AVERAGE = "weighted_average"  # Weighted combination
    MAJORITY_VOTE = "majority_vote"  # Majority of timeframes decide


@dataclass
class AlignmentConfig:
    """Configuration for signal alignment rules"""

    rule_type: AlignmentRule
    required_timeframes: List[str]
    threshold: float = 0.0
    weights: Dict[str, float] = None
    enabled: bool = True

    def __post_init__(self):
        if self.weights is None:
            self.weights = {"5m": 0.5, "15m": 0.3, "1h": 0.2}


@dataclass
class CombinedSignal:
    """Final combined signal from multiple timeframes"""

    direction: int  # -1, 0, 1
    alpha: float  # Signal strength [0, 1]
    confidence: float  # Combined confidence [0, 1]
    chosen_timeframes: List[str]  # Which timeframes contributed
    alignment_rule: str  # Which rule was applied
    individual_signals: Dict[str, OverlaySignal]  # Individual timeframe signals
    reasoning: str  # Human-readable explanation


class EnhancedSignalCombiner:
    """Enhanced signal combination with multiple alignment rules"""

    def __init__(self, config: Dict[str, any]):
        self.config = config

        # Default timeframe weights
        self.timeframe_weights = config.get('timeframe_weights', {
            "5m": 0.5,
            "15m": 0.3,
            "1h": 0.2
        })
        # Alignment runtime options
        arules = config.get('alignment_rules', {}) or {}
        # Whether to halve size if 1h opposes final direction
        self.halve_on_1h_opposition: bool = bool(arules.get('halve_on_1h_opposition', True))
        # Conflict skip threshold (alpha units) when 5m vs 15m disagree; if None, default ~0.3
        self.conflict_min_alpha: float = float(arules.get('conflict_min_alpha', 0.3))
        # Alignment rules configuration
        self.alignment_rules = self._setup_default_rules()

        # Signal history for analysis
        self.combination_history: List[CombinedSignal] = []
        self.max_history = 1000

    def _setup_default_rules(self) -> List[AlignmentConfig]:
        """Setup default alignment rules"""
        return [
            AlignmentConfig(
                rule_type=AlignmentRule.AGREEMENT,
                required_timeframes=["5m", "15m"],
                enabled=True,
            ),
            AlignmentConfig(
                rule_type=AlignmentRule.NEUTRAL_OVERRIDE,
                required_timeframes=["1h"],
                threshold=0.1,  # If 1h signal is weak, allow others to override
                enabled=True,
            ),
            AlignmentConfig(
                rule_type=AlignmentRule.WEIGHTED_AVERAGE,
                required_timeframes=["5m", "15m", "1h"],
                weights=self.timeframe_weights,
                enabled=True,
            ),
        ]

    def combine_signals(self, signal_result: OverlaySignalResult) -> CombinedSignal:
        """Combine signals from all timeframes using alignment rules"""

        signals = signal_result.signals
        # Prompt-aligned pre-check: if 5m and 15m conflict and signals are weak, skip (neutral)
        try:
            s5 = signals.get('5m')
            s15 = signals.get('15m')
            if s5 and s15:
                if (s5.direction != 0 and s15.direction != 0 and s5.direction != s15.direction):
                    max_alpha = max(abs(getattr(s5, 'alpha', 0.0)), abs(getattr(s15, 'alpha', 0.0)))
                    if max_alpha < self.conflict_min_alpha:
                        return CombinedSignal(
                            direction=0,
                            alpha=0.0,
                            confidence=float(np.mean([getattr(s5, 'confidence', 0.0), getattr(s15, 'confidence', 0.0)])),
                            chosen_timeframes=['5m','15m'],
                            alignment_rule='conflict_skip',
                            individual_signals=signals,
                            reasoning='5m vs 15m conflict with weak signals'
                        )
        except Exception:
            pass
        
        # Try each alignment rule in order of preference
        for rule_config in self.alignment_rules:
            if not rule_config.enabled:
                continue

            # Check if we have the required timeframes
            if not self._has_required_timeframes(
                signals, rule_config.required_timeframes
            ):
                continue

            # Apply the alignment rule
            combined_signal = self._apply_alignment_rule(signals, rule_config)

            if combined_signal:
                # Store in history
                self.combination_history.append(combined_signal)
                if len(self.combination_history) > self.max_history:
                    self.combination_history.pop(0)
                
                # Post-adjustment: halve size if 1h opposes
                try:
                    s1h = signals.get('1h')
                    if self.halve_on_1h_opposition and s1h and combined_signal.direction != 0:
                        if s1h.direction != 0 and s1h.direction != combined_signal.direction:
                            combined_signal = CombinedSignal(
                                direction=combined_signal.direction,
                                alpha=0.5 * float(getattr(combined_signal, 'alpha', 0.0)),
                                confidence=float(getattr(combined_signal, 'confidence', 0.0)),
                                chosen_timeframes=list(getattr(combined_signal, 'chosen_timeframes', [])),
                                alignment_rule=f"{combined_signal.alignment_rule}+halve_on_1h_opposition",
                                individual_signals=signals,
                                reasoning=f"1h opposes; halved size"
                            )
                except Exception:
                    pass
                return combined_signal

        # Fallback: return neutral signal if no rules match
        return self._create_fallback_signal(signals)

    def _has_required_timeframes(
        self, signals: Dict[str, OverlaySignal], required: List[str]
    ) -> bool:
        """Check if we have signals for all required timeframes"""
        return all(tf in signals for tf in required)

    def _apply_alignment_rule(
        self, signals: Dict[str, OverlaySignal], rule_config: AlignmentConfig
    ) -> Optional[CombinedSignal]:
        """Apply a specific alignment rule"""

        if rule_config.rule_type == AlignmentRule.AGREEMENT:
            return self._apply_agreement_rule(signals, rule_config)
        elif rule_config.rule_type == AlignmentRule.NEUTRAL_OVERRIDE:
            return self._apply_neutral_override_rule(signals, rule_config)
        elif rule_config.rule_type == AlignmentRule.WEIGHTED_AVERAGE:
            return self._apply_weighted_average_rule(signals, rule_config)
        elif rule_config.rule_type == AlignmentRule.MAJORITY_VOTE:
            return self._apply_majority_vote_rule(signals, rule_config)
        elif rule_config.rule_type == AlignmentRule.THRESHOLD:
            return self._apply_threshold_rule(signals, rule_config)

        return None

    def _apply_agreement_rule(
        self, signals: Dict[str, OverlaySignal], rule_config: AlignmentConfig
    ) -> Optional[CombinedSignal]:
        """Apply agreement rule: all timeframes must agree on direction"""

        required_signals = [signals[tf] for tf in rule_config.required_timeframes]

        # Check if all signals agree on direction
        directions = [s.direction for s in required_signals]
        non_zero_directions = [d for d in directions if d != 0]

        if not non_zero_directions:
            # All neutral - return neutral signal
            return CombinedSignal(
                direction=0,
                alpha=0.0,
                confidence=np.mean([s.confidence for s in required_signals]),
                chosen_timeframes=rule_config.required_timeframes,
                alignment_rule="agreement",
                individual_signals=signals,
                reasoning="All timeframes neutral",
            )

        # Check if all non-zero signals agree
        if len(set(non_zero_directions)) == 1:
            # All agree - use weighted average
            direction = non_zero_directions[0]
            alphas = [s.alpha for s in required_signals if s.direction == direction]
            confidences = [
                s.confidence for s in required_signals if s.direction == direction
            ]

            return CombinedSignal(
                direction=direction,
                alpha=np.mean(alphas),
                confidence=np.mean(confidences),
                chosen_timeframes=rule_config.required_timeframes,
                alignment_rule="agreement",
                individual_signals=signals,
                reasoning=f"All timeframes agree on direction {direction}",
            )

        return None  # No agreement found

    def _apply_neutral_override_rule(
        self, signals: Dict[str, OverlaySignal], rule_config: AlignmentConfig
    ) -> Optional[CombinedSignal]:
        """Apply neutral override rule: neutral timeframe can override others"""

        override_timeframe = rule_config.required_timeframes[0]
        override_signal = signals[override_timeframe]

        # If override timeframe is neutral or weak, use other timeframes
        if abs(override_signal.alpha) < rule_config.threshold:
            other_signals = {
                tf: signals[tf] for tf in signals.keys() if tf != override_timeframe
            }

            if other_signals:
                # Use weighted average of other timeframes
                return self._apply_weighted_average_rule(other_signals, rule_config)

        # Use the override timeframe signal
        return CombinedSignal(
            direction=override_signal.direction,
            alpha=override_signal.alpha,
            confidence=override_signal.confidence,
            chosen_timeframes=[override_timeframe],
            alignment_rule="neutral_override",
            individual_signals=signals,
            reasoning=f"{override_timeframe} signal overrides others",
        )

    def _apply_weighted_average_rule(
        self, signals: Dict[str, OverlaySignal], rule_config: AlignmentConfig
    ) -> Optional[CombinedSignal]:
        """Apply weighted average rule"""

        weights = rule_config.weights or self.timeframe_weights

        # Calculate weighted averages
        weighted_direction = 0.0
        weighted_alpha = 0.0
        weighted_confidence = 0.0
        total_weight = 0.0

        for timeframe, signal in signals.items():
            if timeframe in weights:
                weight = weights[timeframe]
                weighted_direction += signal.direction * weight
                weighted_alpha += signal.alpha * weight
                weighted_confidence += signal.confidence * weight
                total_weight += weight

        if total_weight == 0:
            return None

        # Normalize
        weighted_direction /= total_weight
        weighted_alpha /= total_weight
        weighted_confidence /= total_weight

        # Convert to final signal
        final_direction = 0
        if weighted_direction > 0.1:
            final_direction = 1
        elif weighted_direction < -0.1:
            final_direction = -1

        return CombinedSignal(
            direction=final_direction,
            alpha=min(1.0, weighted_alpha),
            confidence=min(1.0, weighted_confidence),
            chosen_timeframes=list(signals.keys()),
            alignment_rule="weighted_average",
            individual_signals=signals,
            reasoning=f"Weighted average of {len(signals)} timeframes",
        )

    def _apply_majority_vote_rule(
        self, signals: Dict[str, OverlaySignal], rule_config: AlignmentConfig
    ) -> Optional[CombinedSignal]:
        """Apply majority vote rule"""

        directions = [s.direction for s in signals.values()]

        # Count votes
        vote_counts = {-1: 0, 0: 0, 1: 0}
        for direction in directions:
            vote_counts[direction] += 1

        # Find majority
        majority_direction = max(vote_counts.keys(), key=lambda k: vote_counts[k])

        if vote_counts[majority_direction] == 0:
            return None

        # Calculate average alpha and confidence for majority direction
        majority_signals = [
            s for s in signals.values() if s.direction == majority_direction
        ]

        return CombinedSignal(
            direction=majority_direction,
            alpha=np.mean([s.alpha for s in majority_signals]),
            confidence=np.mean([s.confidence for s in majority_signals]),
            chosen_timeframes=list(signals.keys()),
            alignment_rule="majority_vote",
            individual_signals=signals,
            reasoning=f"Majority vote: {majority_direction} ({vote_counts[majority_direction]} votes)",
        )

    def _apply_threshold_rule(
        self, signals: Dict[str, OverlaySignal], rule_config: AlignmentConfig
    ) -> Optional[CombinedSignal]:
        """Apply threshold rule: signal must exceed threshold"""

        for timeframe, signal in signals.items():
            if signal.alpha >= rule_config.threshold:
                return CombinedSignal(
                    direction=signal.direction,
                    alpha=signal.alpha,
                    confidence=signal.confidence,
                    chosen_timeframes=[timeframe],
                    alignment_rule="threshold",
                    individual_signals=signals,
                    reasoning=f"{timeframe} exceeds threshold {rule_config.threshold}",
                )

        return None

    def _create_fallback_signal(
        self, signals: Dict[str, OverlaySignal]
    ) -> CombinedSignal:
        """Create a fallback neutral signal"""
        return CombinedSignal(
            direction=0,
            alpha=0.0,
            confidence=0.0,
            chosen_timeframes=[],
            alignment_rule="fallback",
            individual_signals=signals,
            reasoning="No alignment rules matched - using neutral signal",
        )

    def get_combination_stats(self, lookback: int = 100) -> Dict[str, float]:
        """Get statistics about signal combinations"""
        if not self.combination_history:
            return {}

        recent_signals = self.combination_history[-lookback:]

        directions = [s.direction for s in recent_signals]
        alphas = [s.alpha for s in recent_signals]
        confidences = [s.confidence for s in recent_signals]

        return {
            "total_combinations": len(recent_signals),
            "avg_direction": np.mean(directions),
            "avg_alpha": np.mean(alphas),
            "avg_confidence": np.mean(confidences),
            "non_zero_signals": sum(1 for d in directions if d != 0),
            "hit_rate": (
                sum(1 for d in directions if d != 0) / len(directions)
                if directions
                else 0.0
            ),
            "rule_usage": self._get_rule_usage_stats(recent_signals),
        }

    def _get_rule_usage_stats(self, signals: List[CombinedSignal]) -> Dict[str, int]:
        """Get statistics about which rules are used most"""
        rule_counts = {}
        for signal in signals:
            rule = signal.alignment_rule
            rule_counts[rule] = rule_counts.get(rule, 0) + 1
        return rule_counts
