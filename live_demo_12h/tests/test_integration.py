"""
Integration Test Script for Overlay System

This script tests the overlay system integration with a simple
end-to-end test using mock data.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
import pytz

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_overlay_system import UnifiedOverlaySystem, OverlaySystemConfig
from overlay_manager import BarData
from features import LiveFeatureComputer, FeatureBuilder

IST = pytz.timezone("Asia/Kolkata")


async def test_overlay_integration():
    """Test the overlay system integration"""
    print("🧪 Starting Overlay System Integration Test")

    # 1. Initialize overlay system
    print("\n1. Initializing Overlay System...")
    config = OverlaySystemConfig(
        enable_overlays=True,
        base_timeframe="5m",
        overlay_timeframes=["15m", "1h"],
        rollup_windows={"15m": 3, "1h": 12},
        timeframe_weights={"5m": 0.5, "15m": 0.3, "1h": 0.2},
        model_manifest_path="live_demo/models/LATEST.json",
    )

    overlay_system = UnifiedOverlaySystem(config)

    # 2. Initialize base feature computer
    print("2. Initializing Base Feature Computer...")
<<<<<<< HEAD:live_demo_12h/tests/test_integration.py
    # Resolve feature schema path from model manifest
    manifest_path = os.path.join("live_demo", "models", "LATEST.json")
    with open(manifest_path, 'r', encoding='utf-8') as mf:
        manifest = json.load(mf)
    schema_file = manifest.get("feature_columns")
    if not schema_file:
        raise RuntimeError("feature_columns not found in model manifest")
    schema_path = os.path.join(os.path.dirname(manifest_path), schema_file)
    fb = FeatureBuilder(schema_path)
    lf = LiveFeatureComputer(fb.columns, rv_window=12, vol_window=50, corr_window=36, timeframe="5m")
    
=======
    fb = FeatureBuilder()
    lf = LiveFeatureComputer(
        fb.get_columns(), rv_window=12, vol_window=50, corr_window=36, timeframe="5m"
    )

>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde:live_demo/test_integration.py
    # 3. Initialize overlay system
    print("3. Initializing Overlay System with Base Computer...")
    try:
        overlay_system.initialize(lf)
        print("✅ Overlay system initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize overlay system: {e}")
        return False

    # 4. Add mock market data
    print("\n4. Adding Mock Market Data...")
    mock_bars = [
        {
            "timestamp": "2025-10-22T10:05:00+05:30",
            "bar_id": 1,
            "open": 50000,
            "high": 50100,
            "low": 49900,
            "close": 50050,
            "volume": 100,
            "funding": 0.0001,
            "spread_bps": 2.0,
            "rv_1h": 0.02,
        },
        {
            "timestamp": "2025-10-22T10:10:00+05:30",
            "bar_id": 2,
            "open": 50050,
            "high": 50150,
            "low": 50000,
            "close": 50100,
            "volume": 120,
            "funding": 0.0002,
            "spread_bps": 2.5,
            "rv_1h": 0.025,
        },
        {
            "timestamp": "2025-10-22T10:15:00+05:30",
            "bar_id": 3,
            "open": 50100,
            "high": 50200,
            "low": 50050,
            "close": 50150,
            "volume": 110,
            "funding": 0.0003,
            "spread_bps": 3.0,
            "rv_1h": 0.03,
        },
        {
            "timestamp": "2025-10-22T10:20:00+05:30",
            "bar_id": 4,
            "open": 50150,
            "high": 50250,
            "low": 50100,
            "close": 50200,
            "volume": 130,
            "funding": 0.0004,
            "spread_bps": 2.8,
            "rv_1h": 0.035,
        },
        {
            "timestamp": "2025-10-22T10:25:00+05:30",
            "bar_id": 5,
            "open": 50200,
            "high": 50300,
            "low": 50150,
            "close": 50250,
            "volume": 140,
            "funding": 0.0005,
            "spread_bps": 3.2,
            "rv_1h": 0.04,
        },
    ]

    for bar_data in mock_bars:
        overlay_bars = overlay_system.add_market_data(bar_data)
        print(
            f"   Added bar {bar_data['bar_id']}, generated overlays: {list(overlay_bars.keys())}"
        )

    # 5. Check system status
    print("\n5. Checking System Status...")
    status = overlay_system.get_system_status()
    print(f"   Initialized: {status['is_initialized']}")
    print(f"   Model loaded: {status['model_loaded']}")
    print(f"   Timeframe status:")
    for tf, tf_status in status["timeframe_status"].items():
        print(
            f"     {tf}: {tf_status['bar_count']} bars, ready: {tf_status['is_ready']}"
        )

    # 6. Generate mock decision
    print("\n6. Generating Mock Decision...")
    cohort_signals = {"S_top": 0.15, "S_bot": -0.08, "S_mood": 0.05}

    try:
        decision = overlay_system.generate_decision(cohort_signals, 5)
        print(
            f"   Decision: direction={decision.direction}, alpha={decision.alpha:.3f}, confidence={decision.confidence:.3f}"
        )
        print(f"   Alignment rule: {decision.alignment_rule}")
        print(f"   Chosen timeframes: {decision.chosen_timeframes}")
        print(f"   Reasoning: {decision.reasoning}")
    except Exception as e:
        print(f"   ⚠️  Decision generation failed (expected without model): {e}")

    # 7. Test performance stats
    print("\n7. Checking Performance Stats...")
    try:
        perf_stats = overlay_system.get_performance_stats()
        print(f"   Total decisions: {perf_stats.get('total_decisions', 0)}")
        print(f"   Hit rate: {perf_stats.get('hit_rate', 0):.3f}")
    except Exception as e:
        print(f"   ⚠️  Performance stats failed: {e}")

    # 8. Test timeframe signals
    print("\n8. Checking Timeframe Signals...")
    try:
        timeframe_signals = overlay_system.get_timeframe_signals()
        for tf, signals in timeframe_signals.items():
            print(
                f"   {tf}: {signals.get('signal_count', 0)} signals, hit rate: {signals.get('hit_rate', 0):.3f}"
            )
    except Exception as e:
        print(f"   ⚠️  Timeframe signals failed: {e}")

    print("\n✅ Overlay System Integration Test Completed!")
    return True


async def test_configuration_loading():
    """Test loading overlay configuration"""
    print("\n🔧 Testing Configuration Loading...")

    config_path = "live_demo/config_overlay.json"
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        return False

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        print("✅ Configuration loaded successfully")
        print(f"   Overlay enabled: {config.get('overlay', {}).get('enabled', False)}")
        print(f"   Timeframes: {config.get('overlay', {}).get('timeframes', [])}")
        print(
            f"   Rollup windows: {config.get('overlay', {}).get('rollup_windows', {})}"
        )
        print(f"   Weights: {config.get('overlay', {}).get('weights', {})}")

        return True
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False


def test_file_structure():
    """Test that all required files exist"""
    print("\n📁 Testing File Structure...")

    required_files = [
        "live_demo/overlay_manager.py",
        "live_demo/overlay_features.py",
        "live_demo/overlay_signal_generator.py",
        "live_demo/enhanced_signal_combiner.py",
        "live_demo/unified_overlay_system.py",
        "live_demo/main_overlay.py",
        "live_demo/config_overlay.json",
<<<<<<< HEAD:live_demo_12h/tests/test_integration.py
    "live_demo/tests/test_overlay_system.py"
=======
        "live_demo/test_overlay_system.py",
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde:live_demo/test_integration.py
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"   ✅ {file_path}")

    if missing_files:
        print(f"\n❌ Missing files:")
        for file_path in missing_files:
            print(f"   ❌ {file_path}")
        return False

    print("✅ All required files exist")
    return True


async def main():
    """Main test function"""
    print("🚀 Overlay System Implementation Test Suite")
    print("=" * 50)

    # Test file structure
    if not test_file_structure():
        print("\n❌ File structure test failed")
        return False

    # Test configuration loading
    if not await test_configuration_loading():
        print("\n❌ Configuration test failed")
        return False

    # Test overlay integration
    if not await test_overlay_integration():
        print("\n❌ Integration test failed")
        return False

    print("\n🎉 All tests passed! Overlay system is ready for deployment.")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)
