"""
Feature Logging for MetaStackerBandit
Dedicated logging for microstructure and overlay features
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import pytz
import numpy as np

IST = pytz.timezone("Asia/Kolkata")


@dataclass
class FeatureLog:
    """Feature log data structure"""

    ts_ist: str
    bar_id: int
    asset: str
    mom_3: float  # 3-bar momentum
    mr_ema20: float  # Mean reversion EMA20
    obi_10: float  # Order book imbalance 10 levels
    spread_bps: float  # Bid-ask spread
    rv_1h: float  # 1-hour realized volatility
    regime_bucket: str  # Market regime classification
    funding_delta: float  # Funding rate change
    adv20: float  # 20-day average daily volume
    volume_ratio: float  # Current volume vs average
    price_change_bps: float  # Price change in basis points
    volatility_regime: str  # Volatility regime
    liquidity_score: float  # Liquidity score


class FeatureLogger:
    """Dedicated feature logging system"""

    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.funding_history: List[float] = []
        self.feature_history: List[FeatureLog] = []

    def log_features(
        self,
        ts: float,
        bar_id: int,
        asset: str,
        market_data: Dict[str, Any],
        features: List[float],
        feature_names: List[str],
    ) -> FeatureLog:
        """Log microstructure and overlay features

        Robust to missing fields in market_data by falling back to available values.
        - mid: fallback to close when not provided
        - spread_bps: fallback to bid/ask if present, else estimate from high/low
        - rv_1h: fallback to value from features when present in feature_names
        - funding: fallback to 'funding' if 'funding_8h' is absent
        """

        # Convert timestamp to IST
        dt_ist = datetime.fromtimestamp(ts / 1000.0, tz=IST)
        ts_ist = dt_ist.isoformat()

        # Extract basic market data
        # Mid/Close
        close_px = market_data.get("close", 0.0)
        mid_price = market_data.get("mid", close_px if close_px is not None else 0.0)
        volume = market_data.get("volume", 0.0)
        # Spread bps: prefer provided; else try bid/ask; else estimate from high/low range
        spread_bps = market_data.get("spread_bps")
        if spread_bps is None:
            bid = market_data.get("bid") or market_data.get("bid1")
            ask = market_data.get("ask") or market_data.get("ask1")
            try:
                if bid and ask and bid > 0 and ask > 0:
                    mid = (float(bid) + float(ask)) / 2.0
                    spread_bps = 10000.0 * ((float(ask) - float(bid)) / mid)
                else:
                    raise ValueError("no bid/ask")
            except Exception:
                try:
                    h = float(market_data.get("high", 0.0) or 0.0)
                    l = float(market_data.get("low", 0.0) or 0.0)
                    m = float(mid_price or 0.0)
                    spread_bps = 10000.0 * ((h - l) / m) if m > 0 else 0.0
                except Exception:
                    spread_bps = 0.0
        # Realized volatility (1h) fallback: from features vector if available
        rv_1h = market_data.get("rv_1h")
        if rv_1h is None and feature_names:
            try:
                if "rv_1h" in feature_names:
                    idx = feature_names.index("rv_1h")
                    rv_1h = float(features[idx])
            except Exception:
                rv_1h = 0.0
        if rv_1h is None:
            rv_1h = 0.0
        # Funding rate fallback
        funding_rate = market_data.get("funding_8h")
        if funding_rate is None:
            funding_rate = market_data.get("funding", 0.0)
        # Order book imbalance (not available in this pipeline)
        obi_10 = market_data.get("obi_10", 0.0)

        # Update history
        self.price_history.append(mid_price)
        self.volume_history.append(volume)
        self.funding_history.append(funding_rate)

        # Keep only recent history
        if len(self.price_history) > self.window_size:
            self.price_history = self.price_history[-self.window_size :]
        if len(self.volume_history) > self.window_size:
            self.volume_history = self.volume_history[-self.window_size :]
        if len(self.funding_history) > self.window_size:
            self.funding_history = self.funding_history[-self.window_size :]

        # Calculate features
        mom_3 = self._calculate_momentum(3)
        mr_ema20 = self._calculate_mean_reversion_ema20()
        regime_bucket = self._classify_regime(rv_1h, volume)
        funding_delta = self._calculate_funding_delta()
        adv20 = self._calculate_adv20()
        volume_ratio = self._calculate_volume_ratio(volume)
        price_change_bps = self._calculate_price_change_bps()
        volatility_regime = self._classify_volatility_regime(rv_1h)
        liquidity_score = self._calculate_liquidity_score(volume, spread_bps)

        # Create feature log
        feature_log = FeatureLog(
            ts_ist=ts_ist,
            bar_id=bar_id,
            asset=asset,
            mom_3=mom_3,
            mr_ema20=mr_ema20,
            obi_10=obi_10,
            spread_bps=spread_bps,
            rv_1h=rv_1h,
            regime_bucket=regime_bucket,
            funding_delta=funding_delta,
            adv20=adv20,
            volume_ratio=volume_ratio,
            price_change_bps=price_change_bps,
            volatility_regime=volatility_regime,
            liquidity_score=liquidity_score,
        )

        # Store feature log
        self.feature_history.append(feature_log)

        # Keep only recent history
        if len(self.feature_history) > 1000:
            self.feature_history = self.feature_history[-1000:]

        return feature_log

    def _calculate_momentum(self, periods: int) -> float:
        """Calculate momentum over specified periods"""
        if len(self.price_history) < periods + 1:
            return 0.0

        current_price = self.price_history[-1]
        past_price = self.price_history[-(periods + 1)]

        if past_price == 0:
            return 0.0

        return (current_price - past_price) / past_price

    def _calculate_mean_reversion_ema20(self) -> float:
        """Calculate mean reversion using EMA20"""
        if len(self.price_history) < 20:
            return 0.0

        prices = np.array(self.price_history[-20:])
        ema20 = self._calculate_ema(prices, 20)
        current_price = prices[-1]

        if ema20 == 0:
            return 0.0

        return (current_price - ema20) / ema20

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate exponential moving average"""
        if len(prices) == 0:
            return 0.0

        alpha = 2.0 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema

        return ema

    def _classify_regime(self, volatility: float, volume: float) -> str:
        """Classify market regime"""
        if volatility > 0.05 and volume > 1000:
            return "high_vol_high_vol"
        elif volatility > 0.05 and volume <= 1000:
            return "high_vol_low_vol"
        elif volatility <= 0.05 and volume > 1000:
            return "low_vol_high_vol"
        else:
            return "low_vol_low_vol"

    def _calculate_funding_delta(self) -> float:
        """Calculate funding rate change"""
        if len(self.funding_history) < 2:
            return 0.0

        current_funding = self.funding_history[-1]
        previous_funding = self.funding_history[-2]

        return current_funding - previous_funding

    def _calculate_adv20(self) -> float:
        """Calculate 20-day average daily volume"""
        if len(self.volume_history) < 20:
            return 0.0

        return np.mean(self.volume_history[-20:])

    def _calculate_volume_ratio(self, current_volume: float) -> float:
        """Calculate current volume vs average"""
        if len(self.volume_history) < 5:
            return 1.0

        avg_volume = np.mean(self.volume_history[-5:])
        if avg_volume == 0:
            return 1.0

        return current_volume / avg_volume

    def _calculate_price_change_bps(self) -> float:
        """Calculate price change in basis points"""
        if len(self.price_history) < 2:
            return 0.0

        current_price = self.price_history[-1]
        previous_price = self.price_history[-2]

        if previous_price == 0:
            return 0.0

        return ((current_price - previous_price) / previous_price) * 10000

    def _classify_volatility_regime(self, volatility: float) -> str:
        """Classify volatility regime"""
        if volatility > 0.10:
            return "very_high"
        elif volatility > 0.05:
            return "high"
        elif volatility > 0.02:
            return "medium"
        else:
            return "low"

    def _calculate_liquidity_score(self, volume: float, spread_bps: float) -> float:
        """Calculate liquidity score"""
        # Higher volume and lower spread = better liquidity
        volume_score = min(volume / 1000.0, 1.0)  # Normalize volume
        spread_score = max(0.0, 1.0 - (spread_bps / 50.0))  # Lower spread is better

        return (volume_score + spread_score) / 2.0

    def get_feature_log(
        self, ts: float, asset: str, bar_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get feature log for emission"""
        if not self.feature_history:
            return None

        latest_log = self.feature_history[-1]

        return {
            "ts_ist": latest_log.ts_ist,
            "bar_id": latest_log.bar_id,
            "asset": latest_log.asset,
            "mom_3": latest_log.mom_3,
            "mr_ema20": latest_log.mr_ema20,
            "obi_10": latest_log.obi_10,
            "spread_bps": latest_log.spread_bps,
            "rv_1h": latest_log.rv_1h,
            "regime_bucket": latest_log.regime_bucket,
            "funding_delta": latest_log.funding_delta,
            "adv20": latest_log.adv20,
            "volume_ratio": latest_log.volume_ratio,
            "price_change_bps": latest_log.price_change_bps,
            "volatility_regime": latest_log.volatility_regime,
            "liquidity_score": latest_log.liquidity_score,
        }

    def log_features_dict(
        self,
        ts: float,
        bar_id: int,
        asset: str,
        market_data: Dict[str, Any],
        features: List[float],
        feature_names: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Log features and return dictionary directly"""
        feature_log = self.log_features(
            ts, bar_id, asset, market_data, features, feature_names
        )
        if feature_log:
            return {
                "ts_ist": feature_log.ts_ist,
                "bar_id": feature_log.bar_id,
                "asset": feature_log.asset,
                "mom_3": feature_log.mom_3,
                "mr_ema20": feature_log.mr_ema20,
                "obi_10": feature_log.obi_10,
                "spread_bps": feature_log.spread_bps,
                "rv_1h": feature_log.rv_1h,
                "regime_bucket": feature_log.regime_bucket,
                "funding_delta": feature_log.funding_delta,
                "adv20": feature_log.adv20,
                "volume_ratio": feature_log.volume_ratio,
                "price_change_bps": feature_log.price_change_bps,
                "volatility_regime": feature_log.volatility_regime,
                "liquidity_score": feature_log.liquidity_score,
            }
        return None

    def get_feature_statistics(self) -> Dict[str, Any]:
        """Get feature statistics"""
        if not self.feature_history:
            return {}

        total_features = len(self.feature_history)

        # Calculate statistics for each feature
        mom_3_values = [log.mom_3 for log in self.feature_history]
        mr_ema20_values = [log.mr_ema20 for log in self.feature_history]
        spread_bps_values = [log.spread_bps for log in self.feature_history]
        rv_1h_values = [log.rv_1h for log in self.feature_history]

        return {
            "total_features": total_features,
            "avg_momentum_3": np.mean(mom_3_values),
            "avg_mean_reversion": np.mean(mr_ema20_values),
            "avg_spread_bps": np.mean(spread_bps_values),
            "avg_volatility": np.mean(rv_1h_values),
            "momentum_std": np.std(mom_3_values),
            "mean_reversion_std": np.std(mr_ema20_values),
            "spread_std": np.std(spread_bps_values),
            "volatility_std": np.std(rv_1h_values),
        }
