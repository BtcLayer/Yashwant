"""
PnL Attribution System for MetaStackerBandit
Tracks and attributes PnL to alpha, timing, fees, and impact components
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from collections import deque
import pytz
from dataclasses import dataclass
import json

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class PnLAttribution:
    """PnL attribution breakdown"""

    alpha: float = 0.0
    timing: float = 0.0
    fees: float = 0.0
    impact: float = 0.0
    total: float = 0.0


class PnLAttributionTracker:
    """PnL attribution tracking system"""

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.attribution_history = deque(maxlen=max_history)
        self.position_history = deque(maxlen=max_history)
        self.return_history = deque(maxlen=max_history)
        self.fee_history = deque(maxlen=max_history)
        self.impact_history = deque(maxlen=max_history)

        # Tracking variables
        self.last_position = 0.0
        self.last_price = 0.0
        self.cumulative_alpha = 0.0
        self.cumulative_timing = 0.0
        self.cumulative_fees = 0.0
        self.cumulative_impact = 0.0

    def update_position(self, position: float, price: float, timestamp: float):
        """Update position and calculate attribution"""
        if self.last_position != 0.0 and self.last_price != 0.0:
            # Calculate position change
            position_change = position - self.last_position
            price_change = price - self.last_price

            # Calculate PnL components
            alpha_pnl = self._calculate_alpha_pnl(position_change, price_change)
            timing_pnl = self._calculate_timing_pnl(position_change, price_change)

            # Store attribution
            attribution = PnLAttribution(
                alpha=alpha_pnl, timing=timing_pnl, total=alpha_pnl + timing_pnl
            )

            self.attribution_history.append(
                {
                    "timestamp": timestamp,
                    "attribution": attribution,
                    "position": position,
                    "price": price,
                    "position_change": position_change,
                    "price_change": price_change,
                }
            )

            # Update cumulative totals
            self.cumulative_alpha += alpha_pnl
            self.cumulative_timing += timing_pnl

        self.last_position = position
        self.last_price = price

    def add_fee(self, fee_usd: float, timestamp: float):
        """Add fee to attribution"""
        self.cumulative_fees += fee_usd

        self.fee_history.append(
            {
                "timestamp": timestamp,
                "fee_usd": fee_usd,
                "cumulative_fees": self.cumulative_fees,
            }
        )

    def add_impact(self, impact_usd: float, timestamp: float):
        """Add market impact to attribution"""
        self.cumulative_impact += impact_usd

        self.impact_history.append(
            {
                "timestamp": timestamp,
                "impact_usd": impact_usd,
                "cumulative_impact": self.cumulative_impact,
            }
        )

    def _calculate_alpha_pnl(
        self, position_change: float, price_change: float
    ) -> float:
        """Calculate alpha PnL (skill-based returns)"""
        # Alpha PnL is the return from the position change
        # This is a simplified calculation - in practice, this would be more sophisticated
        if position_change == 0:
            return 0.0

        # Alpha is the return from the position change
        alpha_pnl = position_change * price_change
        return alpha_pnl

    def _calculate_timing_pnl(
        self, position_change: float, price_change: float
    ) -> float:
        """Calculate timing PnL (market timing)"""
        # Timing PnL is the return from market timing
        # This is a simplified calculation
        if position_change == 0:
            return 0.0

        # Timing is the return from market timing (simplified)
        timing_pnl = position_change * price_change * 0.1  # Simplified timing factor
        return timing_pnl

    def get_current_attribution(self) -> PnLAttribution:
        """Get current PnL attribution"""
        return PnLAttribution(
            alpha=self.cumulative_alpha,
            timing=self.cumulative_timing,
            fees=self.cumulative_fees,
            impact=self.cumulative_impact,
            total=self.cumulative_alpha
            + self.cumulative_timing
            + self.cumulative_fees
            + self.cumulative_impact,
        )

    def get_attribution_log(
        self, timestamp: float, asset: str, bar_id: int
    ) -> Dict[str, Any]:
        """Get PnL attribution log for a specific timestamp"""
        current_attribution = self.get_current_attribution()

        return {
            "ts_ist": datetime.fromtimestamp(timestamp / 1000, IST).isoformat(),
            "asset": asset,
            "bar_id": bar_id,
            "pnl_attrib": {
                "alpha": current_attribution.alpha,
                "timing": current_attribution.timing,
                "fees": current_attribution.fees,
                "impact": current_attribution.impact,
                "total": current_attribution.total,
            },
        }

    def get_attribution_stats(self) -> Dict[str, Any]:
        """Get attribution statistics"""
        if not self.attribution_history:
            return {}

        # Calculate attribution breakdown
        total_alpha = sum(a["attribution"].alpha for a in self.attribution_history)
        total_timing = sum(a["attribution"].timing for a in self.attribution_history)
        total_fees = sum(f["fee_usd"] for f in self.fee_history)
        total_impact = sum(i["impact_usd"] for i in self.impact_history)
        total_pnl = total_alpha + total_timing + total_fees + total_impact

        # Calculate percentages
        if total_pnl != 0:
            alpha_pct = (total_alpha / total_pnl) * 100
            timing_pct = (total_timing / total_pnl) * 100
            fees_pct = (total_fees / total_pnl) * 100
            impact_pct = (total_impact / total_pnl) * 100
        else:
            alpha_pct = timing_pct = fees_pct = impact_pct = 0.0

        return {
            "total_alpha": total_alpha,
            "total_timing": total_timing,
            "total_fees": total_fees,
            "total_impact": total_impact,
            "total_pnl": total_pnl,
            "alpha_percentage": alpha_pct,
            "timing_percentage": timing_pct,
            "fees_percentage": fees_pct,
            "impact_percentage": impact_pct,
            "attribution_quality": self._calculate_attribution_quality(),
        }

    def _calculate_attribution_quality(self) -> float:
        """Calculate attribution quality score (0-1)"""
        if not self.attribution_history:
            return 0.0

        # Quality is based on how well we can attribute PnL
        # This is a simplified calculation
        total_attributions = len(self.attribution_history)
        non_zero_attributions = sum(
            1 for a in self.attribution_history if abs(a["attribution"].total) > 0.01
        )

        if total_attributions == 0:
            return 0.0

        quality = non_zero_attributions / total_attributions
        return quality

    def get_attribution_breakdown(self, window: int = 100) -> Dict[str, Any]:
        """Get attribution breakdown for recent window"""
        recent_attributions = list(self.attribution_history)[-window:]

        if not recent_attributions:
            return {}

        # Calculate rolling attribution
        alpha_values = [a["attribution"].alpha for a in recent_attributions]
        timing_values = [a["attribution"].timing for a in recent_attributions]

        return {
            "window_size": len(recent_attributions),
            "avg_alpha": np.mean(alpha_values),
            "avg_timing": np.mean(timing_values),
            "alpha_volatility": np.std(alpha_values),
            "timing_volatility": np.std(timing_values),
            "alpha_sharpe": (
                np.mean(alpha_values) / np.std(alpha_values)
                if np.std(alpha_values) > 0
                else 0
            ),
            "timing_sharpe": (
                np.mean(timing_values) / np.std(timing_values)
                if np.std(timing_values) > 0
                else 0
            ),
        }

    def get_performance_attribution(self) -> Dict[str, Any]:
        """Get performance attribution analysis"""
        stats = self.get_attribution_stats()
        breakdown = self.get_attribution_breakdown()

        return {
            "attribution_stats": stats,
            "recent_breakdown": breakdown,
            "performance_analysis": {
                "alpha_contribution": stats.get("alpha_percentage", 0),
                "timing_contribution": stats.get("timing_percentage", 0),
                "cost_contribution": stats.get("fees_percentage", 0)
                + stats.get("impact_percentage", 0),
                "skill_vs_luck": self._calculate_skill_vs_luck(),
                "attribution_consistency": self._calculate_attribution_consistency(),
            },
        }

    def _calculate_skill_vs_luck(self) -> float:
        """Calculate skill vs luck ratio"""
        if not self.attribution_history:
            return 0.0

        # Skill is alpha, luck is timing
        total_alpha = sum(a["attribution"].alpha for a in self.attribution_history)
        total_timing = sum(a["attribution"].timing for a in self.attribution_history)

        if total_alpha + total_timing == 0:
            return 0.0

        skill_ratio = abs(total_alpha) / (abs(total_alpha) + abs(total_timing))
        return skill_ratio

    def _calculate_attribution_consistency(self) -> float:
        """Calculate attribution consistency"""
        if len(self.attribution_history) < 10:
            return 0.0

        # Consistency is based on how stable the attribution is over time
        recent_attributions = list(self.attribution_history)[-50:]
        alpha_values = [a["attribution"].alpha for a in recent_attributions]

        if len(alpha_values) < 2:
            return 0.0

        # Calculate coefficient of variation (lower is more consistent)
        mean_alpha = np.mean(alpha_values)
        std_alpha = np.std(alpha_values)

        if mean_alpha == 0:
            return 0.0

        cv = std_alpha / abs(mean_alpha)
        consistency = max(0, 1 - cv)  # Higher consistency for lower CV

        return consistency

    def reset_attribution(self):
        """Reset attribution tracking"""
        self.attribution_history.clear()
        self.position_history.clear()
        self.return_history.clear()
        self.fee_history.clear()
        self.impact_history.clear()

        self.last_position = 0.0
        self.last_price = 0.0
        self.cumulative_alpha = 0.0
        self.cumulative_timing = 0.0
        self.cumulative_fees = 0.0
        self.cumulative_impact = 0.0
