#!/usr/bin/env python3
"""
Simple test script for 5m bot
"""
import sys
import os
import json
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_imports():
    """Test that all imports work correctly"""
    try:
        print("Testing imports...")
        from live_demo import main
        from ops.heartbeat import write_heartbeat
        print("OK: All imports successful")
        return True
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        return False

def test_config_loading():
    """Test that config loads correctly"""
    try:
        print("Testing config loading...")
        from live_demo.main import load_config
        config = load_config('live_demo/config.json')
        print(f"OK: Config loaded successfully")
        print(f"   - Symbol: {config.get('data', {}).get('symbol', 'N/A')}")
        print(f"   - Interval: {config.get('data', {}).get('interval', 'N/A')}")
        print(f"   - CONF_MIN: {config.get('thresholds', {}).get('CONF_MIN', 'N/A')}")
        return True
    except Exception as e:
        print(f"ERROR: Config loading failed: {e}")
        return False

def test_model_loading():
    """Test that model loads correctly"""
    try:
        print("Testing model loading...")
        from live_demo.model_runtime import ModelRuntime
        model = ModelRuntime('live_demo/models/LATEST.json')
        print("OK: Model loaded successfully")
        return True
    except Exception as e:
        print(f"ERROR: Model loading failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("5m Bot Simple Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_loading,
        test_model_loading
    ]
    
    results = []
    for test in tests:
        print(f"\n{test.__name__.replace('_', ' ').title()}:")
        results.append(test())
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("OK: All tests passed! The 5m bot should be ready to run.")
    else:
        print("ERROR: Some tests failed. Please check the errors above.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()