"""
Test Suite for Overlay System Implementation

This module provides comprehensive tests for the overlay system
to ensure it works correctly before deployment.
"""

import unittest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json
from datetime import datetime
import pytz

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from overlay_manager import OverlayManager, OverlayConfig, BarData
from overlay_features import OverlayFeatureComputer, OverlayFeatures
from overlay_signal_generator import OverlaySignalGenerator, OverlaySignal, OverlaySignalResult
from enhanced_signal_combiner import EnhancedSignalCombiner, CombinedSignal, AlignmentRule
from unified_overlay_system import UnifiedOverlaySystem, OverlaySystemConfig, OverlayDecision

IST = pytz.timezone("Asia/Kolkata")

class TestOverlayManager(unittest.TestCase):
    """Test suite for OverlayManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = OverlayConfig(
            base_timeframe="5m",
            overlay_timeframes=["15m", "1h"],
            rollup_windows={"15m": 3, "1h": 12}
        )
        self.manager = OverlayManager(self.config)
    
    def test_add_bar(self):
        """Test adding bars and generating overlays"""
        # Create test bar
        bar = BarData(
            timestamp=datetime.now(IST),
            bar_id=1,
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=100.0,
            funding=0.0001,
            spread_bps=2.0,
            rv_1h=0.02
        )
        
        # Add bar
        overlay_bars = self.manager.add_bar(bar)
        
        # Check that 5m bar was added
        self.assertEqual(len(self.manager.base_bars), 1)
        self.assertEqual(self.manager.base_bars[0].bar_id, 1)
        
        # Check that no overlay bars were generated yet (need more bars)
        self.assertEqual(len(overlay_bars), 0)
    
    def test_rollup_generation(self):
        """Test rollup bar generation"""
        # Add multiple bars to trigger rollup
        for i in range(5):
            bar = BarData(
                timestamp=datetime.now(IST),
                bar_id=i+1,
                open=50000.0 + i*10,
                high=50100.0 + i*10,
                low=49900.0 + i*10,
                close=50050.0 + i*10,
                volume=100.0,
                funding=0.0001,
                spread_bps=2.0,
                rv_1h=0.02
            )
            overlay_bars = self.manager.add_bar(bar)
            
            # After 3 bars, should generate 15m rollup
            if i >= 2:
                self.assertIn("15m", overlay_bars)
                self.assertEqual(overlay_bars["15m"].bar_id, 1)  # First rollup bar
        
        # Check 15m rollup values
        rollup_15m = self.manager.overlay_bars["15m"][0]
        self.assertEqual(rollup_15m.open, 50000.0)  # First bar's open
        self.assertEqual(rollup_15m.close, 50070.0)   # Third bar's close
        self.assertEqual(rollup_15m.high, 50120.0)  # Max high
        self.assertEqual(rollup_15m.low, 49900.0)    # Min low
        self.assertEqual(rollup_15m.volume, 300.0)  # Sum of volumes
    
    def test_timeframe_readiness(self):
        """Test timeframe readiness checks"""
        # Initially not ready
        self.assertFalse(self.manager.is_timeframe_ready("5m"))
        self.assertFalse(self.manager.is_timeframe_ready("15m"))
        
        # Add enough bars
        for i in range(60):
            bar = BarData(
                timestamp=datetime.now(IST),
                bar_id=i+1,
                open=50000.0,
                high=50100.0,
                low=49900.0,
                close=50050.0,
                volume=100.0,
                funding=0.0001,
                spread_bps=2.0,
                rv_1h=0.02
            )
            self.manager.add_bar(bar)
        
        # Now should be ready
        self.assertTrue(self.manager.is_timeframe_ready("5m"))
        self.assertTrue(self.manager.is_timeframe_ready("15m"))


class TestOverlayFeatureComputer(unittest.TestCase):
    """Test suite for OverlayFeatureComputer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_base_computer = Mock()
        self.mock_base_computer.update_and_build.return_value = [0.1, 0.2, 0.3, 0.4, 0.5] * 3 + [0.1, 0.2]  # 17 features
        
        self.mock_overlay_manager = Mock()
        self.mock_overlay_manager.is_timeframe_ready.return_value = True
        self.mock_overlay_manager.get_latest_bars.return_value = []
        
        self.computer = OverlayFeatureComputer(self.mock_base_computer, self.mock_overlay_manager)
    
    def test_compute_overlay_features(self):
        """Test overlay feature computation"""
        # Mock bars
        bars = [
            BarData(
                timestamp=datetime.now(IST),
                bar_id=1,
                open=50000.0,
                high=50100.0,
                low=49900.0,
                close=50050.0,
                volume=100.0,
                funding=0.0001,
                spread_bps=2.0,
                rv_1h=0.02
            )
        ]
        
        cohort_signals = {"S_top": 0.1, "S_bot": -0.1}
        
        # Compute features
        features = self.computer.compute_overlay_features("5m", bars, cohort_signals)
        
        # Check result
        self.assertIsInstance(features, OverlayFeatures)
        self.assertEqual(features.timeframe, "5m")
        self.assertEqual(len(features.features), 17)
        self.assertEqual(len(features.feature_names), 17)
    
    def test_compute_all_timeframe_features(self):
        """Test computing features for all timeframes"""
        # Mock overlay manager
        self.mock_overlay_manager.config.overlay_timeframes = ["15m", "1h"]
        self.mock_overlay_manager.is_timeframe_ready.side_effect = lambda tf: tf in ["5m", "15m", "1h"]
        self.mock_overlay_manager.get_latest_bars.return_value = []
        
        cohort_signals = {"S_top": 0.1, "S_bot": -0.1}
        
        # Compute all features
        all_features = self.computer.compute_all_timeframe_features(cohort_signals)
        
        # Check that features were computed for all timeframes
        self.assertIn("5m", all_features)
        self.assertIn("15m", all_features)
        self.assertIn("1h", all_features)
        
        for tf, features in all_features.items():
            self.assertIsInstance(features, OverlayFeatures)
            self.assertEqual(features.timeframe, tf)


class TestOverlaySignalGenerator(unittest.TestCase):
    """Test suite for OverlaySignalGenerator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_model_runtime = Mock()
        self.mock_model_runtime.infer.return_value = {
            'p_up': 0.4,
            'p_down': 0.3,
            'p_neutral': 0.3,
            's_model': 0.1
        }
        
        self.mock_feature_computer = Mock()
        self.mock_feature_computer.compute_all_timeframe_features.return_value = {
            "5m": OverlayFeatures(
                timeframe="5m",
                features=[0.1] * 17,
                feature_names=["feature_" + str(i) for i in range(17)],
                timestamp="2025-10-22T10:05:00+05:30",
                bar_id=1
            ),
            "15m": OverlayFeatures(
                timeframe="15m",
                features=[0.2] * 17,
                feature_names=["feature_" + str(i) for i in range(17)],
                timestamp="2025-10-22T10:05:00+05:30",
                bar_id=1
            )
        }
        
        self.generator = OverlaySignalGenerator(self.mock_model_runtime, self.mock_feature_computer)
    
    def test_generate_signals(self):
        """Test signal generation for all timeframes"""
        cohort_signals = {"S_top": 0.1, "S_bot": -0.1}
        base_bar_id = 1
        
        # Generate signals
        result = self.generator.generate_signals(cohort_signals, base_bar_id)
        
        # Check result
        self.assertIsInstance(result, OverlaySignalResult)
        self.assertIn("5m", result.signals)
        self.assertIn("15m", result.signals)
        
        # Check individual signals
        for tf, signal in result.signals.items():
            self.assertIsInstance(signal, OverlaySignal)
            self.assertEqual(signal.timeframe, tf)
            self.assertIn(signal.direction, [-1, 0, 1])
            self.assertGreaterEqual(signal.alpha, 0.0)
            self.assertLessEqual(signal.alpha, 1.0)
            self.assertGreaterEqual(signal.confidence, 0.0)
            self.assertLessEqual(signal.confidence, 1.0)
    
    def test_signal_calculation(self):
        """Test signal direction and strength calculation"""
        # Test positive signal
        direction, alpha, confidence = self.generator._calculate_signal_components(
            0.6, 0.2, 0.2, 0.4
        )
        self.assertEqual(direction, 1)
        self.assertGreater(alpha, 0.0)
        self.assertEqual(confidence, 0.6)
        
        # Test negative signal
        direction, alpha, confidence = self.generator._calculate_signal_components(
            0.2, 0.6, 0.2, -0.4
        )
        self.assertEqual(direction, -1)
        self.assertGreater(alpha, 0.0)
        self.assertEqual(confidence, 0.6)
        
        # Test neutral signal
        direction, alpha, confidence = self.generator._calculate_signal_components(
            0.35, 0.35, 0.3, 0.0
        )
        self.assertEqual(direction, 0)
        self.assertEqual(alpha, 0.0)


class TestEnhancedSignalCombiner(unittest.TestCase):
    """Test suite for EnhancedSignalCombiner"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'timeframe_weights': {"5m": 0.5, "15m": 0.3, "1h": 0.2}
        }
        self.combiner = EnhancedSignalCombiner(self.config)
    
    def test_agreement_rule(self):
        """Test agreement rule"""
        # Create agreeing signals
        signals = {
            "5m": OverlaySignal(
                timeframe="5m",
                direction=1,
                alpha=0.3,
                confidence=0.7,
                raw_prediction={},
                features=[],
                timestamp="2025-10-22T10:05:00+05:30",
                bar_id=1
            ),
            "15m": OverlaySignal(
                timeframe="15m",
                direction=1,
                alpha=0.4,
                confidence=0.8,
                raw_prediction={},
                features=[],
                timestamp="2025-10-22T10:05:00+05:30",
                bar_id=1
            )
        }
        
        signal_result = OverlaySignalResult(
            signals=signals,
            timestamp="2025-10-22T10:05:00+05:30",
            base_bar_id=1,
            model_version="test"
        )
        
        # Combine signals
        combined = self.combiner.combine_signals(signal_result)
        
        # Check result
        self.assertIsInstance(combined, CombinedSignal)
        self.assertEqual(combined.direction, 1)
        self.assertGreater(combined.alpha, 0.0)
        self.assertEqual(combined.alignment_rule, "agreement")
    
    def test_weighted_average_rule(self):
        """Test weighted average rule"""
        # Create signals with different directions
        signals = {
            "5m": OverlaySignal(
                timeframe="5m",
                direction=1,
                alpha=0.3,
                confidence=0.7,
                raw_prediction={},
                features=[],
                timestamp="2025-10-22T10:05:00+05:30",
                bar_id=1
            ),
            "15m": OverlaySignal(
                timeframe="15m",
                direction=-1,
                alpha=0.2,
                confidence=0.6,
                raw_prediction={},
                features=[],
                timestamp="2025-10-22T10:05:00+05:30",
                bar_id=1
            ),
            "1h": OverlaySignal(
                timeframe="1h",
                direction=1,
                alpha=0.4,
                confidence=0.8,
                raw_prediction={},
                features=[],
                timestamp="2025-10-22T10:05:00+05:30",
                bar_id=1
            )
        }
        
        signal_result = OverlaySignalResult(
            signals=signals,
            timestamp="2025-10-22T10:05:00+05:30",
            base_bar_id=1,
            model_version="test"
        )
        
        # Combine signals
        combined = self.combiner.combine_signals(signal_result)
        
        # Check result
        self.assertIsInstance(combined, CombinedSignal)
        self.assertIn(combined.direction, [-1, 0, 1])
        self.assertGreaterEqual(combined.alpha, 0.0)
        self.assertLessEqual(combined.alpha, 1.0)

    def test_halve_on_1h_opposition(self):
        """Ensure alpha is halved when 1h opposes the combined direction."""
        config = {
            'timeframe_weights': {"5m": 0.6, "15m": 0.3, "1h": 0.1},
            'alignment_rules': {'halve_on_1h_opposition': True}
        }
        comb = EnhancedSignalCombiner(config)
        # Make 5m and 15m point up with strong alpha; 1h points down
        signals = {
            "5m": OverlaySignal(
                timeframe="5m", direction=1, alpha=0.6, confidence=0.8,
                raw_prediction={}, features=[], timestamp="2025-10-22T10:05:00+05:30", bar_id=1
            ),
            "15m": OverlaySignal(
                timeframe="15m", direction=1, alpha=0.5, confidence=0.7,
                raw_prediction={}, features=[], timestamp="2025-10-22T10:05:00+05:30", bar_id=1
            ),
            "1h": OverlaySignal(
                timeframe="1h", direction=-1, alpha=0.4, confidence=0.6,
                raw_prediction={}, features=[], timestamp="2025-10-22T10:05:00+05:30", bar_id=1
            )
        }
        sr = OverlaySignalResult(signals=signals, timestamp="2025-10-22T10:05:00+05:30", base_bar_id=1, model_version="test")
        combined = comb.combine_signals(sr)
        self.assertEqual(combined.direction, 1)
        # With halving, alpha should be <= mean(0.6,0.5)=0.55 and roughly halved
        self.assertLessEqual(combined.alpha, 0.55)
        self.assertIn('halve_on_1h_opposition', combined.alignment_rule)


class TestUnifiedOverlaySystem(unittest.TestCase):
    """Test suite for UnifiedOverlaySystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = OverlaySystemConfig(
            enable_overlays=True,
            base_timeframe="5m",
            overlay_timeframes=["15m", "1h"],
            rollup_windows={"15m": 3, "1h": 12},
            model_manifest_path="test_models/LATEST.json"
        )
        self.system = UnifiedOverlaySystem(self.config)
    
    def test_initialization(self):
        """Test system initialization"""
        # Mock base feature computer
        mock_base_computer = Mock()
        
        # Mock model runtime
        with patch('unified_overlay_system.ModelRuntime') as mock_model_runtime:
            mock_model_runtime.return_value = Mock()
            
            # Initialize system
            self.system.initialize(mock_base_computer)
            
            # Check initialization
            self.assertTrue(self.system.is_initialized)
            self.assertIsNotNone(self.system.feature_computer)
            self.assertIsNotNone(self.system.signal_generator)
            self.assertIsNotNone(self.system.signal_combiner)
    
    def test_add_market_data(self):
        """Test adding market data"""
        bar_data = {
            'timestamp': '2025-10-22T10:05:00+05:30',
            'bar_id': 1,
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50050.0,
            'volume': 100.0,
            'funding': 0.0001,
            'spread_bps': 2.0,
            'rv_1h': 0.02
        }
        
        # Add market data
        overlay_bars = self.system.add_market_data(bar_data)
        
        # Check that data was added
        self.assertEqual(len(self.system.overlay_manager.base_bars), 1)
        self.assertEqual(self.system.overlay_manager.base_bars[0].bar_id, 1)
    
    def test_generate_decision(self):
        """Test decision generation"""
        # Mock initialization
        mock_base_computer = Mock()
        with patch('unified_overlay_system.ModelRuntime') as mock_model_runtime:
            mock_model_runtime.return_value = Mock()
            self.system.initialize(mock_base_computer)
        
        # Mock signal generation
        mock_signal_result = OverlaySignalResult(
            signals={},
            timestamp="2025-10-22T10:05:00+05:30",
            base_bar_id=1,
            model_version="test"
        )
        
        with patch.object(self.system.signal_generator, 'generate_signals', return_value=mock_signal_result):
            with patch.object(self.system.signal_combiner, 'combine_signals') as mock_combine:
                mock_combine.return_value = CombinedSignal(
                    direction=1,
                    alpha=0.3,
                    confidence=0.7,
                    chosen_timeframes=["5m", "15m"],
                    alignment_rule="agreement",
                    individual_signals={},
                    reasoning="Test agreement"
                )
                
                # Generate decision
                decision = self.system.generate_decision({"S_top": 0.1, "S_bot": -0.1}, 1)
                
                # Check result
                self.assertIsInstance(decision, OverlayDecision)
                self.assertEqual(decision.direction, 1)
                self.assertEqual(decision.alpha, 0.3)
                self.assertEqual(decision.confidence, 0.7)
                self.assertEqual(decision.alignment_rule, "agreement")
    
    def test_system_status(self):
        """Test system status reporting"""
        status = self.system.get_system_status()
        
        # Check status structure
        self.assertIn('is_initialized', status)
        self.assertIn('model_loaded', status)
        self.assertIn('timeframe_status', status)
        self.assertIn('config', status)
        
        # Check timeframe status
        for tf in ["5m", "15m", "1h"]:
            self.assertIn(tf, status['timeframe_status'])
            tf_status = status['timeframe_status'][tf]
            self.assertIn('bar_count', tf_status)
            self.assertIn('is_ready', tf_status)
            self.assertIn('last_bar_id', tf_status)


def run_overlay_tests():
    """Run all overlay system tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestOverlayManager))
    test_suite.addTest(unittest.makeSuite(TestOverlayFeatureComputer))
    test_suite.addTest(unittest.makeSuite(TestOverlaySignalGenerator))
    test_suite.addTest(unittest.makeSuite(TestEnhancedSignalCombiner))
    test_suite.addTest(unittest.makeSuite(TestUnifiedOverlaySystem))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_overlay_tests()
    if success:
        print("\n✅ All overlay system tests passed!")
    else:
        print("\n❌ Some overlay system tests failed!")
        sys.exit(1)
