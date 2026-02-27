"""
tests/test_feature_warmup.py

Verifies that LiveFeatureComputer produces sane mr_ema20_z values after warmup.
These tests guard against formula regressions in features.py.

Run with:
    python -m pytest tests/test_feature_warmup.py -v
"""
import random
import statistics
import pytest
from live_demo.features import LiveFeatureComputer


# ── helpers ──────────────────────────────────────────────────────────────────

def _simulate_bars(n: int = 100, start_price: float = 95000.0, seed: int = 42):
    """Generate n realistic BTC 5m OHLCV bars."""
    random.seed(seed)
    price = start_price
    bars = []
    for _ in range(n):
        price += random.gauss(0, 80)   # ~$80 per-bar std, realistic for BTC 5m
        spread = abs(random.gauss(30, 15))
        bars.append({
            "open":   price - spread / 2,
            "high":   price + spread,
            "low":    price - spread,
            "close":  price,
            "volume": abs(random.gauss(50, 20)),
        })
    return bars


NULL_COHORT = {"pros": 0.0, "amateurs": 0.0, "mood": 0.0}


# ── tests ─────────────────────────────────────────────────────────────────────

class TestFeatureWarmup:

    def test_syntax_import(self):
        """features.py must import without errors."""
        from live_demo.features import LiveFeatureComputer, FeatureBuilder  # noqa: F401

    def test_mr_ema20_z_in_range_after_warmup(self):
        """
        After 60+ bars, mr_ema20_z must stay in [-50, +50].
        Old bug: values were -5314 to +18550 due to division by rv_1h (~0.0003).
        New fix: divide by rolling std of (close-EMA20) in price-scale ($).
        """
        lf = LiveFeatureComputer(["mr_ema20_z", "rv_1h", "mom_1"])
        bars = _simulate_bars(100)
        out_of_range = []
        for i, bar in enumerate(bars):
            feats = lf.update_and_build(bar, NULL_COHORT, 0.0)
            mr_z = feats[0]
            if i >= 60 and abs(mr_z) > 50:
                out_of_range.append((i, mr_z))

        assert not out_of_range, (
            f"mr_ema20_z out of range [-50,+50] at bars: "
            + ", ".join(f"bar{i}={v:.2f}" for i, v in out_of_range)
        )

    def test_is_warmed_transitions_correctly(self):
        """
        is_warmed() must return False before 50 bars, True from bar 50 onward.
        This gate prevents garbage features from reaching the model.
        """
        lf = LiveFeatureComputer(["mr_ema20_z"])
        bars = _simulate_bars(60)
        for i, bar in enumerate(bars):
            lf.update_and_build(bar, NULL_COHORT, 0.0)
            if i < 49:
                assert not lf.is_warmed(), (
                    f"should NOT be warmed at bar {i} (bar_count={lf._bar_count})"
                )
            else:
                assert lf.is_warmed(), (
                    f"should be warmed at bar {i} (bar_count={lf._bar_count})"
                )

    def test_mr_ema20_z_is_not_constant(self):
        """
        mr_ema20_z must vary — std dev > 0.1 after warmup.
        If it's flat/constant the model sees no signal (p_down = 0.5 every bar).
        """
        lf = LiveFeatureComputer(["mr_ema20_z"])
        bars = _simulate_bars(120)
        post_warmup_vals = []
        for i, bar in enumerate(bars):
            feats = lf.update_and_build(bar, NULL_COHORT, 0.0)
            if i >= 50:
                post_warmup_vals.append(feats[0])

        std = statistics.stdev(post_warmup_vals)
        assert std > 0.1, (
            f"mr_ema20_z is nearly constant post-warmup (std={std:.4f}). "
            "Formula may be broken or returning 0.0."
        )

    def test_bar_count_increments(self):
        """_bar_count must increment exactly once per update_and_build call."""
        lf = LiveFeatureComputer(["mr_ema20_z"])
        bars = _simulate_bars(10)
        for i, bar in enumerate(bars):
            lf.update_and_build(bar, NULL_COHORT, 0.0)
            assert lf._bar_count == i + 1, (
                f"_bar_count should be {i+1}, got {lf._bar_count}"
            )

    def test_mr_ema20_z_cold_start_is_zero(self):
        """
        First 2 bars must return mr_ema20_z=0.0 (not enough history for std).
        Ensures no division-by-zero or NaN on very first bars.
        """
        lf = LiveFeatureComputer(["mr_ema20_z"])
        bar = {"open": 94900.0, "high": 95100.0, "low": 94800.0,
               "close": 95000.0, "volume": 50.0}
        feats1 = lf.update_and_build(bar, NULL_COHORT, 0.0)
        assert feats1[0] == 0.0, f"Bar 1 mr_ema20_z should be 0.0, got {feats1[0]}"

        feats2 = lf.update_and_build(bar, NULL_COHORT, 0.0)
        assert feats2[0] == 0.0, f"Bar 2 mr_ema20_z should be 0.0, got {feats2[0]}"

    def test_no_nan_or_inf_in_features(self):
        """No feature value should ever be NaN or Inf."""
        import math
        ALL_COLS = [
            "mom_1", "mom_3", "mr_ema20_z", "rv_1h", "regime_high_vol",
            "gk_volatility", "jump_magnitude", "volume_intensity",
            "price_efficiency", "price_volume_corr", "vwap_momentum",
            "depth_proxy", "funding_rate", "funding_momentum_1h",
            "flow_diff", "S_top", "S_bot",
        ]
        lf = LiveFeatureComputer(ALL_COLS)
        bars = _simulate_bars(80)
        for i, bar in enumerate(bars):
            feats = lf.update_and_build(bar, NULL_COHORT, 0.0)
            for col, val in zip(ALL_COLS, feats):
                assert not math.isnan(val), f"bar {i} feature '{col}' is NaN"
                assert not math.isinf(val), f"bar {i} feature '{col}' is Inf"
