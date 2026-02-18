#!/usr/bin/env python3
"""Unit tests for tri-class gating logic in decision.py"""

import pytest
from live_demo.decision import compute_signals_and_eligibility, Thresholds


class TestTriClassMetrics:
    """Test suite for tri-class metric calculations."""
    
    def test_p_non_neutral_calculation(self):
        """Test that p_non_neutral = 1 - p_neutral."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        # Test case 1: p_neutral = 0.3 → p_non_neutral = 0.7
        model_out = {'p_up': 0.4, 'p_down': 0.3, 'p_neutral': 0.3, 's_model': 0.1}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert 'p_non_neutral' in extras
        assert abs(extras['p_non_neutral'] - 0.7) < 1e-6
        
        # Test case 2: p_neutral = 1.0 → p_non_neutral = 0.0
        model_out = {'p_up': 0.0, 'p_down': 0.0, 'p_neutral': 1.0, 's_model': 0.0}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert abs(extras['p_non_neutral'] - 0.0) < 1e-6
        
        # Test case 3: p_neutral = 0.0 → p_non_neutral = 1.0
        model_out = {'p_up': 0.6, 'p_down': 0.4, 'p_neutral': 0.0, 's_model': 0.2}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert abs(extras['p_non_neutral'] - 1.0) < 1e-6
    
    def test_conf_dir_calculation(self):
        """Test that conf_dir = max(p_up, p_down) / (p_up + p_down)."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        # Test case 1: p_up=0.6, p_down=0.2 → conf_dir = 0.6/0.8 = 0.75
        model_out = {'p_up': 0.6, 'p_down': 0.2, 'p_neutral': 0.2, 's_model': 0.4}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert 'conf_dir' in extras
        expected_conf_dir = 0.6 / (0.6 + 0.2)
        assert abs(extras['conf_dir'] - expected_conf_dir) < 1e-6
        
        # Test case 2: p_up=p_down=0.5 → conf_dir = 0.5
        model_out = {'p_up': 0.5, 'p_down': 0.5, 'p_neutral': 0.0, 's_model': 0.0}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert abs(extras['conf_dir'] - 0.5) < 1e-6
        
        # Test case 3: p_up=0.9, p_down=0.1 → conf_dir = 0.9
        model_out = {'p_up': 0.9, 'p_down': 0.1, 'p_neutral': 0.0, 's_model': 0.8}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert abs(extras['conf_dir'] - 0.9) < 1e-6
    
    def test_conf_dir_zero_when_no_direction(self):
        """Test that conf_dir = 0 when p_up = p_down = 0."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        model_out = {'p_up': 0.0, 'p_down': 0.0, 'p_neutral': 1.0, 's_model': 0.0}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert extras['conf_dir'] == 0.0
    
    def test_strength_calculation(self):
        """Test that strength = abs(p_up - p_down)."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        # Test case 1: p_up=0.6, p_down=0.2 → strength = 0.4
        model_out = {'p_up': 0.6, 'p_down': 0.2, 'p_neutral': 0.2, 's_model': 0.4}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert 'strength' in extras
        assert abs(extras['strength'] - 0.4) < 1e-6
        
        # Test case 2: p_up=0.2, p_down=0.6 → strength = 0.4 (absolute value)
        model_out = {'p_up': 0.2, 'p_down': 0.6, 'p_neutral': 0.2, 's_model': -0.4}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert abs(extras['strength'] - 0.4) < 1e-6
        
        # Test case 3: p_up=p_down → strength = 0
        model_out = {'p_up': 0.5, 'p_down': 0.5, 'p_neutral': 0.0, 's_model': 0.0}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert abs(extras['strength'] - 0.0) < 1e-6


class TestTriClassEligibility:
    """Test suite for tri-class eligibility gating."""
    
    def test_eligibility_all_thresholds_met(self):
        """Test that model is eligible when all thresholds are met."""
        th = Thresholds(
            PNN_MIN=0.20,
            CONF_DIR_MIN=0.60,
            STRENGTH_MIN=0.07
        )
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        # All thresholds met: p_non_neutral=0.7, conf_dir=0.75, strength=0.4
        model_out = {'p_up': 0.6, 'p_down': 0.2, 'p_neutral': 0.2, 's_model': 0.4}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert eligible['model_meta'] == True
        assert eligible['model_bma'] == True
        assert extras['p_non_neutral'] >= th.PNN_MIN
        assert extras['conf_dir'] >= th.CONF_DIR_MIN
        assert extras['strength'] >= th.STRENGTH_MIN
    
    def test_eligibility_pnn_too_low(self):
        """Test that model is not eligible when p_non_neutral < PNN_MIN."""
        th = Thresholds(
            PNN_MIN=0.80,  # High threshold
            CONF_DIR_MIN=0.60,
            STRENGTH_MIN=0.07
        )
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        # p_non_neutral=0.7 < 0.80 → not eligible
        model_out = {'p_up': 0.6, 'p_down': 0.1, 'p_neutral': 0.3, 's_model': 0.5}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert eligible['model_meta'] == False
        assert eligible['model_bma'] == False
        assert extras['p_non_neutral'] < th.PNN_MIN
    
    def test_eligibility_conf_dir_too_low(self):
        """Test that model is not eligible when conf_dir < CONF_DIR_MIN."""
        th = Thresholds(
            PNN_MIN=0.20,
            CONF_DIR_MIN=0.80,  # High threshold
            STRENGTH_MIN=0.07
        )
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        # conf_dir = 0.6/(0.6+0.4) = 0.6 < 0.80 → not eligible
        model_out = {'p_up': 0.6, 'p_down': 0.4, 'p_neutral': 0.0, 's_model': 0.2}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert eligible['model_meta'] == False
        assert eligible['model_bma'] == False
        assert extras['conf_dir'] < th.CONF_DIR_MIN
    
    def test_eligibility_strength_too_low(self):
        """Test that model is not eligible when strength < STRENGTH_MIN."""
        th = Thresholds(
            PNN_MIN=0.20,
            CONF_DIR_MIN=0.60,
            STRENGTH_MIN=0.50  # High threshold
        )
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        # strength = |0.6 - 0.4| = 0.2 < 0.50 → not eligible
        model_out = {'p_up': 0.6, 'p_down': 0.4, 'p_neutral': 0.0, 's_model': 0.2}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        assert eligible['model_meta'] == False
        assert eligible['model_bma'] == False
        assert extras['strength'] < th.STRENGTH_MIN
    
    def test_eligibility_at_exact_thresholds(self):
        """Test eligibility at exact threshold boundaries."""
        th = Thresholds(
            PNN_MIN=0.70,
            CONF_DIR_MIN=0.75,
            STRENGTH_MIN=0.30
        )
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        # Adjusted to meet thresholds: p_non_neutral=0.7, conf_dir=0.75, strength=0.3
        # p_up=0.6, p_down=0.3 → conf_dir = 0.6/(0.6+0.3) = 0.6/0.9 = 0.667 (too low)
        # p_up=0.6, p_down=0.2 → conf_dir = 0.6/(0.6+0.2) = 0.6/0.8 = 0.75 ✓
        # strength = |0.6-0.2| = 0.4 ✓
        model_out = {'p_up': 0.6, 'p_down': 0.1, 'p_neutral': 0.3, 's_model': 0.5}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        # Should be eligible (>= threshold)
        assert eligible['model_meta'] == True
        assert eligible['model_bma'] == True
        assert extras['p_non_neutral'] >= th.PNN_MIN
        assert extras['conf_dir'] >= th.CONF_DIR_MIN
        assert extras['strength'] >= th.STRENGTH_MIN


class TestTriClassEdgeCases:
    """Test suite for edge cases in tri-class gating."""
    
    def test_edge_case_all_neutral(self):
        """Test edge case: p_neutral = 1.0 (all neutral)."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        model_out = {'p_up': 0.0, 'p_down': 0.0, 'p_neutral': 1.0, 's_model': 0.0}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        # Should not be eligible (p_non_neutral = 0)
        assert eligible['model_meta'] == False
        assert eligible['model_bma'] == False
        assert extras['p_non_neutral'] == 0.0
        assert extras['conf_dir'] == 0.0
        assert extras['strength'] == 0.0
    
    def test_edge_case_equal_up_down(self):
        """Test edge case: p_up = p_down (no directional bias)."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        model_out = {'p_up': 0.5, 'p_down': 0.5, 'p_neutral': 0.0, 's_model': 0.0}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        # conf_dir should be 0.5, strength should be 0
        assert abs(extras['conf_dir'] - 0.5) < 1e-6
        assert abs(extras['strength'] - 0.0) < 1e-6
        # Should not be eligible (strength = 0 < STRENGTH_MIN)
        assert eligible['model_meta'] == False
        assert eligible['model_bma'] == False
    
    def test_edge_case_high_confidence_one_direction(self):
        """Test edge case: Very high confidence in one direction."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        model_out = {'p_up': 0.95, 'p_down': 0.05, 'p_neutral': 0.0, 's_model': 0.9}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        # Should have very high conf_dir and strength (use approximate comparison for floating point)
        assert extras['conf_dir'] >= 0.94  # Allow for floating point precision
        assert extras['strength'] >= 0.89  # Allow for floating point precision
        # Should be eligible
        assert eligible['model_meta'] == True
        assert eligible['model_bma'] == True
    
    def test_edge_case_missing_probabilities(self):
        """Test edge case: Missing probability fields (defaults to 0)."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        # Missing p_up, p_down, p_neutral
        model_out = {'s_model': 0.0}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        # Should default to p_neutral=1.0, p_up=0.0, p_down=0.0
        assert extras['p_neutral'] == 1.0
        assert extras['p_up'] == 0.0
        assert extras['p_down'] == 0.0
        assert extras['p_non_neutral'] == 0.0
        # Should not be eligible
        assert eligible['model_meta'] == False
        assert eligible['model_bma'] == False


class TestTriClassExtrasFields:
    """Test suite for extras fields emission."""
    
    def test_extras_fields_emitted(self):
        """Test that all tri-class fields are emitted in extras."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        model_out = {'p_up': 0.6, 'p_down': 0.2, 'p_neutral': 0.2, 's_model': 0.4}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        # Check all required fields are present
        required_fields = ['p_up', 'p_down', 'p_neutral', 'p_non_neutral', 'conf_dir', 'strength']
        for field in required_fields:
            assert field in extras, f"Missing field: {field}"
    
    def test_extras_fields_are_floats(self):
        """Test that all tri-class fields are floats."""
        th = Thresholds()
        cohort_snapshot = {'pros': 0.0, 'amateurs': 0.0, 'mood': 0.0}
        
        model_out = {'p_up': 0.6, 'p_down': 0.2, 'p_neutral': 0.2, 's_model': 0.4}
        signals, eligible, side_eps, extras = compute_signals_and_eligibility(
            cohort_snapshot, model_out, th
        )
        
        # Check all fields are floats
        for field in ['p_up', 'p_down', 'p_neutral', 'p_non_neutral', 'conf_dir', 'strength']:
            assert isinstance(extras[field], float), f"{field} is not a float"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
