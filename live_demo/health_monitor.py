"""
Health Monitoring System for MetaStackerBandit
Tracks performance metrics, risk indicators, and system health
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import pytz
from dataclasses import dataclass
import json

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class HealthMetrics:
    """Health metrics container"""

    sharpe_roll_1d: Optional[float] = None
    sharpe_roll_1w: Optional[float] = None
    sortino_1w: Optional[float] = None
    max_dd_to_date: Optional[float] = None
    time_in_mkt: Optional[float] = None
    hit_rate_w: Optional[float] = None
    turnover_bps_day: Optional[float] = None
    capacity_participation: Optional[float] = None
    ic_drift: Optional[float] = None
    calibration_drift: Optional[float] = None
    leakage_flag: bool = False
    same_bar_roundtrip_flag: bool = False
    in_band_share: Optional[float] = None


class HealthMonitor:
    """Production health monitoring system"""

    def __init__(self, window_1d: int = 288, window_1w: int = 2016):  # 5min bars
        self.window_1d = window_1d
        self.window_1w = window_1w

        # Performance tracking
        self.returns_history = deque(maxlen=window_1w * 2)
        self.positions_history = deque(maxlen=window_1w * 2)
        self.pnl_history = deque(maxlen=window_1w * 2)
        self.turnover_history = deque(maxlen=window_1w)

        # Risk tracking
        self.peak_equity = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0

        # Model performance tracking
        self.predictions_history = deque(maxlen=window_1w)
        self.actual_returns_history = deque(maxlen=window_1w)
        self.ic_history = deque(maxlen=200)  # 200-bar IC window

        # Execution tracking
        self.execution_times = deque(maxlen=1000)
        self.rejection_count = 0
        self.total_orders = 0

        # Data quality tracking
        self.leakage_events = 0
        self.roundtrip_events = 0
        self.last_trade_time = None
        # Calibration in-band tracking
        self._inband_flags = deque(maxlen=window_1d)
        self._inband_total = 0
        self._inband_hits = 0

    def update_returns(self, returns: float, timestamp: float):
        """Update returns history"""
        self.returns_history.append({"timestamp": timestamp, "returns": returns})

        # Update drawdown tracking
        if len(self.returns_history) > 0:
            cumulative_return = sum(r["returns"] for r in self.returns_history)
            if cumulative_return > self.peak_equity:
                self.peak_equity = cumulative_return
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = cumulative_return - self.peak_equity
                self.max_drawdown = min(self.max_drawdown, self.current_drawdown)

    def update_position(self, position: float, timestamp: float):
        """Update position history"""
        self.positions_history.append({"timestamp": timestamp, "position": position})

    def update_pnl(self, pnl: float, timestamp: float):
        """Update PnL history"""
        self.pnl_history.append({"timestamp": timestamp, "pnl": pnl})

    def update_turnover(self, turnover_bps: float, timestamp: float):
        """Update turnover history"""
        self.turnover_history.append(
            {"timestamp": timestamp, "turnover_bps": turnover_bps}
        )

    def update_predictions(
        self, prediction: float, actual_return: float, timestamp: float
    ):
        """Update prediction and actual return history"""
        self.predictions_history.append(
            {"timestamp": timestamp, "prediction": prediction}
        )
        self.actual_returns_history.append(
            {"timestamp": timestamp, "actual_return": actual_return}
        )

        # Calculate IC
        if len(self.predictions_history) >= 2:
            preds = [p["prediction"] for p in list(self.predictions_history)[-20:]]
            actuals = [
                a["actual_return"] for a in list(self.actual_returns_history)[-20:]
            ]
            if len(preds) == len(actuals) and len(preds) > 1:
                ic = (
                    np.corrcoef(preds, actuals)[0, 1]
                    if not np.isnan(np.corrcoef(preds, actuals)[0, 1])
                    else 0.0
                )
                self.ic_history.append(ic)

    def update_inband(self, pred_cal_bps: float, band_bps: float):
        """Update in-band status for the current bar.

        In-band if |pred_cal_bps| <= band_bps.
        Tracked over a rolling ~1-day window.
        """
        try:
            is_inband = 1 if abs(float(pred_cal_bps)) <= float(band_bps) else 0
        except Exception:
            is_inband = 0
        self._inband_flags.append(is_inband)
        # Maintain simple counters for fast share computation
        self._inband_total = min(len(self._inband_flags), self._inband_flags.maxlen)
        self._inband_hits = sum(self._inband_flags)

    def get_inband_share(self) -> Optional[float]:
        if self._inband_total <= 0:
            return None
        return float(self._inband_hits) / float(self._inband_total)

    def update_execution(self, execution_time_ms: float, rejected: bool = False):
        """Update execution metrics"""
        self.execution_times.append(execution_time_ms)
        self.total_orders += 1
        if rejected:
            self.rejection_count += 1

    def check_leakage(
        self, prediction: float, actual_return: float, timestamp: float
    ) -> bool:
        """Check for data leakage"""
        # Simple leakage detection: if prediction is too close to actual return
        if abs(prediction - actual_return) < 0.001:  # Threshold for leakage
            self.leakage_events += 1
            return True
        return False

    def check_roundtrip(self, side: str, timestamp: float) -> bool:
        """Check for same-bar roundtrip"""
        if self.last_trade_time is not None:
            time_diff = timestamp - self.last_trade_time
            if time_diff < 300000:  # 5 minutes in milliseconds
                self.roundtrip_events += 1
                return True

        self.last_trade_time = timestamp
        return False

    def calculate_sharpe_ratio(self, window: int) -> Optional[float]:
        """Calculate rolling Sharpe ratio"""
        if len(self.returns_history) < window:
            return None

        recent_returns = [r["returns"] for r in list(self.returns_history)[-window:]]
        if len(recent_returns) < 2:
            return None

        mean_return = np.mean(recent_returns)
        std_return = np.std(recent_returns)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe (assuming 5-minute bars)
        sharpe = (mean_return / std_return) * np.sqrt(288 * 365)  # 288 bars per day
        return sharpe

    def calculate_sortino_ratio(self, window: int) -> Optional[float]:
        """Calculate rolling Sortino ratio"""
        if len(self.returns_history) < window:
            return None

        recent_returns = [r["returns"] for r in list(self.returns_history)[-window:]]
        if len(recent_returns) < 2:
            return None

        mean_return = np.mean(recent_returns)
        negative_returns = [r for r in recent_returns if r < 0]

        if len(negative_returns) < 2:
            return None

        downside_std = np.std(negative_returns)
        if downside_std == 0:
            return 0.0

        # Annualized Sortino
        sortino = (mean_return / downside_std) * np.sqrt(288 * 365)
        return sortino

    def calculate_hit_rate(self, window: int) -> Optional[float]:
        """Calculate hit rate (percentage of profitable predictions)"""
        if (
            len(self.predictions_history) < window
            or len(self.actual_returns_history) < window
        ):
            return None

        recent_preds = [
            p["prediction"] for p in list(self.predictions_history)[-window:]
        ]
        recent_actuals = [
            a["actual_return"] for a in list(self.actual_returns_history)[-window:]
        ]

        if len(recent_preds) != len(recent_actuals):
            return None

        hits = 0
        for pred, actual in zip(recent_preds, recent_actuals):
            if (pred > 0 and actual > 0) or (pred < 0 and actual < 0):
                hits += 1

        return hits / len(recent_preds) if len(recent_preds) > 0 else None

    def calculate_time_in_market(self) -> Optional[float]:
        """Calculate time in market percentage"""
        if len(self.positions_history) < 2:
            return None

        total_time = 0
        in_market_time = 0

        for i in range(1, len(self.positions_history)):
            prev_pos = self.positions_history[i - 1]["position"]
            curr_pos = self.positions_history[i]["position"]
            prev_time = self.positions_history[i - 1]["timestamp"]
            curr_time = self.positions_history[i]["timestamp"]

            time_diff = curr_time - prev_time
            total_time += time_diff

            if abs(prev_pos) > 0.01:  # Position threshold
                in_market_time += time_diff

        return in_market_time / total_time if total_time > 0 else None

    def calculate_turnover(self) -> Optional[float]:
        """Calculate daily turnover in basis points"""
        if len(self.turnover_history) < 1:
            return None

        recent_turnover = [
            t["turnover_bps"] for t in list(self.turnover_history)[-288:]
        ]  # Last day
        return np.mean(recent_turnover) if recent_turnover else None

    def calculate_capacity_participation(self, adv_usd: float) -> Optional[float]:
        """Calculate capacity participation percentage"""
        if len(self.positions_history) < 1 or adv_usd <= 0:
            return None

        recent_positions = [
            p["position"] for p in list(self.positions_history)[-288:]
        ]  # Last day
        avg_position = np.mean([abs(p) for p in recent_positions])

        # Convert position to USD (assuming $10k base notional)
        position_usd = avg_position * 10000
        participation = position_usd / adv_usd

        return participation

    def calculate_ic_drift(self) -> Optional[float]:
        """Calculate IC drift (recent IC vs historical IC)"""
        if len(self.ic_history) < 20:
            return None

        recent_ic = np.mean(list(self.ic_history)[-10:])  # Last 10 IC values
        historical_ic = np.mean(list(self.ic_history)[-20:-10])  # Previous 10 IC values

        return recent_ic - historical_ic

    def calculate_calibration_drift(self) -> Optional[float]:
        """Calculate calibration drift"""
        # This would require calibration data - simplified for now
        return 0.0

    def get_health_metrics(self) -> HealthMetrics:
        """Get current health metrics"""
        return HealthMetrics(
            sharpe_roll_1d=self.calculate_sharpe_ratio(self.window_1d),
            sharpe_roll_1w=self.calculate_sharpe_ratio(self.window_1w),
            sortino_1w=self.calculate_sortino_ratio(self.window_1w),
            max_dd_to_date=self.max_drawdown,
            time_in_mkt=self.calculate_time_in_market(),
            hit_rate_w=self.calculate_hit_rate(self.window_1w),
            turnover_bps_day=self.calculate_turnover(),
            capacity_participation=self.calculate_capacity_participation(
                25000000
            ),  # Default ADV
            ic_drift=self.calculate_ic_drift(),
            calibration_drift=self.calculate_calibration_drift(),
            leakage_flag=self.leakage_events > 0,
            same_bar_roundtrip_flag=self.roundtrip_events > 0,
            in_band_share=self.get_inband_share(),
        )

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self.execution_times:
            return {}

        return {
            "avg_execution_time_ms": np.mean(self.execution_times),
            "max_execution_time_ms": np.max(self.execution_times),
            "rejection_rate": self.rejection_count / max(self.total_orders, 1),
            "total_orders": self.total_orders,
            "rejection_count": self.rejection_count,
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        metrics = self.get_health_metrics()
        execution_stats = self.get_execution_stats()

        return {
            "health_metrics": {
                "sharpe_1d": metrics.sharpe_roll_1d,
                "sharpe_1w": metrics.sharpe_roll_1w,
                "sortino_1w": metrics.sortino_1w,
                "max_drawdown": metrics.max_dd_to_date,
                "time_in_market": metrics.time_in_mkt,
                "hit_rate": metrics.hit_rate_w,
                "turnover_bps": metrics.turnover_bps_day,
                "capacity_participation": metrics.capacity_participation,
                "ic_drift": metrics.ic_drift,
                "calibration_drift": metrics.calibration_drift,
                "leakage_detected": metrics.leakage_flag,
                "roundtrip_detected": metrics.same_bar_roundtrip_flag,
            },
            "execution_stats": execution_stats,
            "data_quality": {
                "leakage_events": self.leakage_events,
                "roundtrip_events": self.roundtrip_events,
                "total_predictions": len(self.predictions_history),
                "total_returns": len(self.returns_history),
            },
        }
