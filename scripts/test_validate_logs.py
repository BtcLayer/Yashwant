#!/usr/bin/env python3
"""Quick test of log validation script"""

import os
import sys
import tempfile
import shutil
import json
from pathlib import Path

# Add scripts to path
sys.path.insert(0, 'scripts')

def create_test_logs(root_dir):
    """Create sample logs for testing"""
    logs_dir = Path(root_dir) / "logs"
    
    # Valid log: signals with proper partitioning
    valid_path = logs_dir / "signals" / "date=2026-01-20" / "asset=BTCUSDT"
    valid_path.mkdir(parents=True, exist_ok=True)
    
    with open(valid_path / "signals.jsonl", 'w') as f:
        f.write(json.dumps({"ts": 1234567890, "symbol": "BTCUSDT", "asset": "BTCUSDT", "dir": 1}) + "\n")
        f.write(json.dumps({"ts": 1234567891, "symbol": "BTCUSDT", "asset": "BTCUSDT", "dir": 0}) + "\n")
    
    # Valid log: execution_log
    exec_path = logs_dir / "execution_log" / "date=2026-01-20" / "asset=ETHUSDT"
    exec_path.mkdir(parents=True, exist_ok=True)
    
    with open(exec_path / "execution_log.jsonl", 'w') as f:
        f.write(json.dumps({
            "ts": 1234567890,
            "asset": "ETHUSDT",
            "side": "BUY",
            "fill_px": 2000.0,
            "fill_qty": 1.5
        }) + "\n")
    
    # Invalid log: missing date partition
    invalid_path = logs_dir / "costs" / "asset=SOLUSDT"
    invalid_path.mkdir(parents=True, exist_ok=True)
    
    with open(invalid_path / "costs.jsonl", 'w') as f:
        f.write(json.dumps({"ts": 1234567890, "symbol": "SOLUSDT", "asset": "SOLUSDT"}) + "\n")
    
    # Deprecated log: in default namespace
    deprecated_path = logs_dir / "default" / "repro"
    deprecated_path.mkdir(parents=True, exist_ok=True)
    
    with open(deprecated_path / "repro.jsonl", 'w') as f:
        f.write(json.dumps({"ts": 1234567890, "symbol": "BTCUSDT"}) + "\n")
    
    print(f"✅ Created test logs in {root_dir}")

def main():
    # Create temp directory
    test_dir = tempfile.mkdtemp(prefix='log_validation_test_')
    
    try:
        print("=" * 70)
        print("TESTING LOG VALIDATION SCRIPT")
        print("=" * 70)
        
        # Create test logs
        create_test_logs(test_dir)
        
        # Run validation
        print(f"\n🔍 Running validation on {test_dir}...")
        print("-" * 70)
        
        from validate_logs import LogValidator
        
        validator = LogValidator(test_dir)
        success = validator.validate_all()
        
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        
        # Expected results
        expected_errors = 1  # Missing date partition
        expected_warnings = 1  # Deprecated path
        
        actual_errors = len(validator.errors)
        actual_warnings = len(validator.warnings)
        
        print(f"\nExpected: {expected_errors} errors, {expected_warnings} warnings")
        print(f"Actual:   {actual_errors} errors, {actual_warnings} warnings")
        
        if actual_errors >= expected_errors and actual_warnings >= expected_warnings:
            print("\n✅ TEST PASSED: Validator correctly identified issues")
            return 0
        else:
            print("\n❌ TEST FAILED: Validator missed some issues")
            return 1
            
    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"\n🧹 Cleaned up test directory")

if __name__ == "__main__":
    sys.exit(main())
