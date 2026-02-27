#Every time a new 5-minute candle closes, this sequence occurs:

#1. Ingestion: New OHLCV data is added to the historical deques

#2. State Update: The EMA20 (Exponential Moving Average) is updated using a recursive formula
# # ($Value_t = \alpha \cdot Price_t + (1-\alpha) \cdot Value_{t-1}$).

#3.Complex Calculation: It calculates advanced metrics like price_efficiency (how much the price moved relative to its total range).

#4. Cohort Integration: It calculates the flow_diff between "Pros" (top traders) and "Amateurs" (bottom traders).

#5 Final Alignment: It filters all these calculated values through the FeatureBuilder to ensure the list of numbers matches the model's expected input perfectly.


import json
import math
import statistics
from collections import deque
from typing import Deque, Dict, List


class FeatureBuilder:
    def __init__(self, feature_schema_path: str):
        with open(feature_schema_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and "feature_columns" in payload:
            self.columns: List[str] = payload["feature_columns"]
        elif isinstance(payload, dict) and "feature_cols" in payload:
            self.columns = payload["feature_cols"]
        elif isinstance(payload, list):
            self.columns = payload
        else:
            raise ValueError("Invalid feature schema payload")

    def build(self, bar_row: Dict, cohort: Dict, funding: float) -> List[float]:
        """
        Build features in the exact order of self.columns from primitives.
        bar_row: {'open','high','low','close','volume','rv_1h','gk_vol',...}
        cohort: {'pros','amateurs','mood'}
        funding: float
        Return: list of floats matching length and order of schema
        """
        primitives = {**bar_row, **cohort, "funding": funding}
        out: List[float] = []
        for col in self.columns:
            val = primitives.get(col)
            if val is None:
                # Strict parity: default to 0.0, caller should alert if frequent
                val = 0.0
            if isinstance(val, (int, float)):
                out.append(float(val))
            else:
                # Coerce booleans or categories if any; default 0.0
                if isinstance(val, bool):
                    out.append(1.0 if val else 0.0)
                else:
                    try:
                        out.append(float(val))
                    except (TypeError, ValueError):
                        out.append(0.0)
        return out


class LiveFeatureComputer:
    def __init__(
        self,
        columns: List[str],
        rv_window: int = 12,
        vol_window: int = 50,
        corr_window: int = 36,
        timeframe: str = "5m",
    ):
        self.columns = columns
        self.rv_window = rv_window
        self.vol_window = vol_window
        self.corr_window = corr_window
        self.timeframe = timeframe
        self._closes: Deque[float] = deque(maxlen=max(3, vol_window))
        self._highs: Deque[float] = deque(maxlen=max(3, vol_window))
        self._lows: Deque[float] = deque(maxlen=max(3, vol_window))
        self._vols: Deque[float] = deque(maxlen=max(3, vol_window))
        self._funding: Deque[float] = deque(maxlen=rv_window)
        self._ema20: float = 0.0
        self._ema_alpha = 2.0 / (20 + 1)
        self._last_valid_corr: float = 0.0

        # ── FIX: mr_ema20_z normalization ──────────────────────────────────
        # BUG (old): (close - EMA20) / rv_1h
        #   rv_1h is a dimensionless return (~0.0003 in quiet markets)
        #   close - EMA20 is a dollar difference (~$60)
        #   Result: 60 / 0.0003 = 200,000  →  model sees garbage, outputs p=0.5
        #
        # FIX (new): (close - EMA20) / rolling_std(close - EMA20)
        #   Both numerator and denominator are in dollar-scale.
        #   This is a true price z-score, expected range: [-5, +5]
        # ───────────────────────────────────────────────────────────────────
        self._price_dev_hist: Deque[float] = deque(maxlen=max(3, vol_window))
        self._bar_count: int = 0        # incremented every update_and_build call
        self._min_warm_bars: int = 50   # bars needed before is_warmed() = True

    def is_warmed(self) -> bool:
        """True once >= 50 bars have been fed. Gate live trading on this flag.
        Prevents garbage mr_ema20_z from reaching the model during cold start."""
        return self._bar_count >= self._min_warm_bars

    def _ret(self, a: float, b: float) -> float:
        if a is None or b is None or a == 0:
            return 0.0
        return (b / a) - 1.0

    def _gk_vol(self, o: float, h: float, l: float, c: float) -> float:
        # Single bar GK estimator (approx)
        if o <= 0 or h <= 0 or l <= 0 or c <= 0:
            return 0.0
        return math.sqrt(
            0.5 * (math.log(h / l) ** 2)
            - (2 * math.log(2) - 1) * (math.log(c / o) ** 2)
        )

    def update_and_build(
        self, bar_row: Dict, cohort: Dict, funding: float
    ) -> List[float]:
        o = float(bar_row.get("open", 0.0))
        h = float(bar_row.get("high", 0.0))
        l = float(bar_row.get("low", 0.0))
        c = float(bar_row.get("close", 0.0))
        v = float(bar_row.get("volume", 0.0))

        # Increment bar counter
        self._bar_count += 1

        # Update state
        prev_close = self._closes[-1] if self._closes else None
        self._closes.append(c)
        self._highs.append(h)
        self._lows.append(l)
        self._vols.append(v)
        self._funding.append(float(funding))

        # EMA20
        self._ema20 = (
            (1 - self._ema_alpha) * self._ema20 + self._ema_alpha * c
            if self._ema20 != 0
            else c
        )

        # Basic returns
        r1 = self._ret(prev_close, c) if prev_close is not None else 0.0
        r3 = 0.0
        if len(self._closes) >= 3:
            r3 = self._ret(self._closes[-3], c)

        # rv_1h: sqrt(sum r^2 over last rv_window)
        rets = []
        for i in range(1, min(len(self._closes), self.rv_window)):
            rets.append(self._ret(self._closes[-1 - i], self._closes[-i]))
        rv_1h = math.sqrt(sum(r * r for r in rets)) if rets else 0.0

        # regime_high_vol
        rv_hist = []
        for k in range(2, min(len(self._closes), self.rv_window + 2)):
            seg = []
            for i in range(1, min(k, self.rv_window)):
                seg.append(self._ret(self._closes[-k - 1 + i], self._closes[-k + i]))
            rv_hist.append(math.sqrt(sum(x * x for x in seg)) if seg else 0.0)
        med = sorted(rv_hist)[len(rv_hist) // 2] if rv_hist else 0.0
        regime_high_vol = 1.0 if (rv_1h > 2.0 * med and rv_1h > 0) else 0.0

        gk = self._gk_vol(o, h, l, c)
        jump_mag = abs(r1)

        vol_mean = (sum(self._vols) / len(self._vols)) if self._vols else 1.0
        volume_intensity = (v / (vol_mean + 1e-9)) - 1.0

        price_range = (h - l) / (c + 1e-9) if c else 0.0
        price_efficiency = abs(r1) / (price_range + 1e-9)

        # price_volume_corr over last corr_window
        import numpy as np

        if len(self._closes) >= 3:
            rr = []
            for i in range(1, min(len(self._closes), self.corr_window)):
                rr.append(self._ret(self._closes[-1 - i], self._closes[-i]))
            vv = list(self._vols)[-len(rr):]
            if len(rr) >= 3 and len(vv) == len(rr):
                corr_val = np.corrcoef(np.array(rr), np.array(vv))[0, 1]
                if not np.isnan(corr_val):
                    price_volume_corr = float(corr_val)
                    self._last_valid_corr = price_volume_corr
                else:
                    price_volume_corr = self._last_valid_corr
            else:
                price_volume_corr = self._last_valid_corr
        else:
            price_volume_corr = 0.0

        vwap_momentum = r3  # proxy
        depth_proxy = 0.0   # no order book in live demo

        # funding
        funding_rate = float(funding)
        if len(self._funding) >= self.rv_window:
            f_ema = float(np.mean(self._funding))
        else:
            f_ema = funding_rate
        funding_momentum_1h = funding_rate - f_ema

        # cohort mappings
        s_top = float(cohort.get("pros", 0.0))
        s_bot = float(cohort.get("amateurs", 0.0))
        flow_diff = s_top - s_bot

        # ── FIX: mr_ema20_z using price-scale z-score ────────────────────
        price_dev = c - self._ema20
        self._price_dev_hist.append(price_dev)
        if len(self._price_dev_hist) >= 3:
            dev_std = statistics.stdev(self._price_dev_hist)
            mr_ema20_z = price_dev / (dev_std + 1e-9)
        else:
            mr_ema20_z = 0.0  # neutral during first 2 bars
        # ─────────────────────────────────────────────────────────────────

        feature_map = {
            "mom_1": r1,
            "mom_3": r3,
            "mr_ema20_z": mr_ema20_z,
            "rv_1h": rv_1h,
            "regime_high_vol": regime_high_vol,
            "gk_volatility": gk,
            "jump_magnitude": jump_mag,
            "volume_intensity": volume_intensity,
            "price_efficiency": price_efficiency,
            "price_volume_corr": price_volume_corr,
            "vwap_momentum": vwap_momentum,
            "depth_proxy": depth_proxy,
            "funding_rate": funding_rate,
            "funding_momentum_1h": funding_momentum_1h,
            "flow_diff": flow_diff,
            "S_top": s_top,
            "S_bot": s_bot,
        }

        # Prepare output in schema order, defaulting to 0.0 for missing
        out: List[float] = []
        for col in self.columns:
            out.append(float(feature_map.get(col, 0.0)))
        return out
