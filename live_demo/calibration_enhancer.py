"""
Enhanced Calibration Logging for MetaStackerBandit
Adds realized returns tracking to calibration logs
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import pytz
import numpy as np

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class CalibrationLog:
    """Enhanced calibration log with realized returns"""

    ts_ist: str
    bar_id: int
    asset: str
    a: float  # Calibration parameter a
    b: float  # Calibration parameter b
    pred_raw_bps: float  # Uncalibrated prediction in bps (10000*s_model)
    pred_cal_bps: float  # Calibrated prediction in bps (10000*(a + b*s_model))
    in_band_flag: bool  # Whether prediction is in no-trade band
    band_bps: float  # No-trade band width (default 15 bps)
    realized_bps: float  # Realized returns in bps
    prediction_error: float  # |pred_cal_bps - realized_bps|
    calibration_score: float  # Calibration quality score
    band_hit_rate: float  # No-trade band hit rate
    prediction_accuracy: float  # Directional accuracy on recent window


class CalibrationEnhancer:
    """Enhanced calibration logging with realized returns tracking"""

    def __init__(self, band_bps: float = 15.0):
        self.band_bps = band_bps
        self.calibration_history: List[CalibrationLog] = []
        self.prediction_history: List[float] = []
        self.realized_history: List[float] = []
        self.band_hits: int = 0
        self.total_predictions: int = 0

    def log_calibration(
        self,
        ts: float,
        bar_id: int,
        asset: str,
        calibration_params: Dict[str, float],
        prediction: float,
        realized_return: float,
    ) -> CalibrationLog:
        """Log enhanced calibration with realized returns"""
        # Convert timestamp to IST
        dt_ist = datetime.fromtimestamp(ts / 1000.0, tz=IST)
        ts_ist = dt_ist.isoformat()

        # Extract calibration parameters
        a = float(calibration_params.get('a', 0.0))
        b = float(calibration_params.get('b', 1.0))

        # s_model is unitless; convert to bps for raw and calibrated
        pred_raw_bps = 10000.0 * float(prediction)
        pred_cal_bps = 10000.0 * (a + b * float(prediction))

        # Check if in no-trade band
        in_band_flag = abs(pred_cal_bps) <= self.band_bps

        # Calculate prediction error in bps space
        prediction_error = abs(pred_cal_bps - float(realized_return))

        # Calculate calibration score (how well calibrated the model is)
        calibration_score = self._calculate_calibration_score()

        # Update band hit rate
        if in_band_flag:
            self.band_hits += 1
        self.total_predictions += 1

        band_hit_rate = (
            self.band_hits / self.total_predictions
            if self.total_predictions > 0
            else 0.0
        )

        # Calculate prediction accuracy
        prediction_accuracy = self._calculate_prediction_accuracy()

        # Create calibration log
        calibration_log = CalibrationLog(
            ts_ist=ts_ist,
            bar_id=bar_id,
            asset=asset,
            a=a,
            b=b,
            pred_raw_bps=pred_raw_bps,
            pred_cal_bps=pred_cal_bps,
            in_band_flag=in_band_flag,
            band_bps=self.band_bps,
            realized_bps=float(realized_return),
            prediction_error=prediction_error,
            calibration_score=calibration_score,
            band_hit_rate=band_hit_rate,
            prediction_accuracy=prediction_accuracy,
        )

        # Store calibration log
        self.calibration_history.append(calibration_log)

        # Update prediction and realized history
        self.prediction_history.append(pred_cal_bps)
        self.realized_history.append(float(realized_return))

        # Keep only recent history
        if len(self.calibration_history) > 1000:
            self.calibration_history = self.calibration_history[-1000:]
        if len(self.prediction_history) > 1000:
            self.prediction_history = self.prediction_history[-1000:]
        if len(self.realized_history) > 1000:
            self.realized_history = self.realized_history[-1000:]

        return calibration_log

    def _calculate_calibration_score(self) -> float:
        """Calculate calibration quality score"""
        if len(self.prediction_history) < 10:
            return 0.0

        # Calculate correlation between predictions and realized returns
        if len(self.prediction_history) != len(self.realized_history):
            return 0.0

        predictions = np.array(self.prediction_history[-100:])  # Last 100 predictions
        realized = np.array(self.realized_history[-100:])

        if len(predictions) < 10:
            return 0.0

        # Calculate correlation
        correlation = np.corrcoef(predictions, realized)[0, 1]

        # Handle NaN correlation
        if np.isnan(correlation):
            return 0.0

        # Convert correlation to score (0-1)
        return max(0.0, min(1.0, (correlation + 1.0) / 2.0))

    def _calculate_prediction_accuracy(self) -> float:
        """Calculate prediction accuracy"""
        if len(self.prediction_history) < 10:
            return 0.0

        predictions = np.array(self.prediction_history[-100:])
        realized = np.array(self.realized_history[-100:])

        if len(predictions) < 10:
            return 0.0

        # Calculate directional accuracy
        pred_direction = np.sign(predictions)
        realized_direction = np.sign(realized)

        correct_directions = np.sum(pred_direction == realized_direction)
        total_predictions = len(predictions)

        return correct_directions / total_predictions if total_predictions > 0 else 0.0

    def get_calibration_log(
        self, ts: float, asset: str, bar_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get calibration log for emission"""
        if not self.calibration_history:
            return None

        latest_log = self.calibration_history[-1]

        return {
        'ts_ist': latest_log.ts_ist,
        'bar_id': latest_log.bar_id,
        'asset': latest_log.asset,
        'a': latest_log.a,
        'b': latest_log.b,
        'pred_raw_bps': latest_log.pred_raw_bps,
        'pred_cal_bps': latest_log.pred_cal_bps,
        'in_band_flag': latest_log.in_band_flag,
        'band_bps': latest_log.band_bps,
        'realized_bps': latest_log.realized_bps,
        'prediction_error': latest_log.prediction_error,
        'calibration_score': latest_log.calibration_score,
        'band_hit_rate': latest_log.band_hit_rate,
        'prediction_accuracy': latest_log.prediction_accuracy
        }

    def log_calibration_dict(
        self,
        ts: float,
        bar_id: int,
        asset: str,
        calibration_params: Dict[str, float],
        prediction: float,
        realized_return: float,
    ) -> Optional[Dict[str, Any]]:
        """Log calibration and return dictionary directly"""
        calibration_log = self.log_calibration(
            ts, bar_id, asset, calibration_params, prediction, realized_return
        )
        if calibration_log:
            return {
                'ts_ist': calibration_log.ts_ist,
                'bar_id': calibration_log.bar_id,
                'asset': calibration_log.asset,
                'a': calibration_log.a,
                'b': calibration_log.b,
                'pred_raw_bps': calibration_log.pred_raw_bps,
                'pred_cal_bps': calibration_log.pred_cal_bps,
                'in_band_flag': calibration_log.in_band_flag,
                'band_bps': calibration_log.band_bps,
                'realized_bps': calibration_log.realized_bps,
                'prediction_error': calibration_log.prediction_error,
                'calibration_score': calibration_log.calibration_score,
                'band_hit_rate': calibration_log.band_hit_rate,
                'prediction_accuracy': calibration_log.prediction_accuracy
            }
        return None

    def get_calibration_statistics(self) -> Dict[str, Any]:
        """Get calibration statistics"""
        if not self.calibration_history:
            return {}

        total_calibrations = len(self.calibration_history)

        # Calculate statistics
        a_values = [log.a for log in self.calibration_history]
        b_values = [log.b for log in self.calibration_history]
        prediction_errors = [log.prediction_error for log in self.calibration_history]
        calibration_scores = [log.calibration_score for log in self.calibration_history]
        band_hit_rates = [log.band_hit_rate for log in self.calibration_history]
        prediction_accuracies = [
            log.prediction_accuracy for log in self.calibration_history
        ]

        return {
            "total_calibrations": total_calibrations,
            "avg_a": np.mean(a_values),
            "avg_b": np.mean(b_values),
            "avg_prediction_error": np.mean(prediction_errors),
            "avg_calibration_score": np.mean(calibration_scores),
            "avg_band_hit_rate": np.mean(band_hit_rates),
            "avg_prediction_accuracy": np.mean(prediction_accuracies),
            "a_std": np.std(a_values),
            "b_std": np.std(b_values),
            "prediction_error_std": np.std(prediction_errors),
            "calibration_score_std": np.std(calibration_scores),
        }

    def detect_calibration_drift(self, window_size: int = 50) -> Dict[str, Any]:
        """Detect calibration drift"""
        if len(self.calibration_history) < window_size:
            return {"drift_detected": False, "drift_score": 0.0}

        # Get recent and historical calibration parameters
        recent_logs = self.calibration_history[-window_size:]
        historical_logs = self.calibration_history[-(window_size * 2) : -window_size]

        if len(historical_logs) < window_size:
            return {"drift_detected": False, "drift_score": 0.0}

        # Calculate parameter drift
        recent_a = np.mean([log.a for log in recent_logs])
        historical_a = np.mean([log.a for log in historical_logs])
        recent_b = np.mean([log.b for log in recent_logs])
        historical_b = np.mean([log.b for log in historical_logs])

        # Calculate drift scores
        a_drift = abs(recent_a - historical_a)
        b_drift = abs(recent_b - historical_b)

        # Calculate overall drift score
        drift_score = (a_drift + b_drift) / 2.0

        # Determine if drift is significant
        drift_detected = drift_score > 0.1  # Threshold for significant drift

        return {
            "drift_detected": drift_detected,
            "drift_score": drift_score,
            "a_drift": a_drift,
            "b_drift": b_drift,
            "recent_a": recent_a,
            "historical_a": historical_a,
            "recent_b": recent_b,
            "historical_b": historical_b,
        }
