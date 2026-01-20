#!/usr/bin/env python3
"""Verify TASK-4: Logging path standardization"""

import os
import json
import tempfile
import shutil
from datetime import datetime

# Test the updated logging functions
def test_llm_logging():
    """Test llm_logging.py writes to partitioned paths"""
    print("=" * 60)
    print("TEST 1: llm_logging.py (write_jsonl)")
    print("=" * 60)
    
    # Import after setting up test environment
    import sys
    sys.path.insert(0, 'live_demo')
    from ops.llm_logging import write_jsonl
    
    # Create temp directory
    test_root = tempfile.mkdtemp(prefix='test_logs_')
    os.environ['PAPER_TRADING_ROOT'] = test_root
    
    try:
        # Test 1: With explicit asset
        print("\n✓ Test 1a: Explicit asset parameter")
        write_jsonl('signals', {'foo': 'bar', 'ts': 1234567890}, asset='BTC')
        
        # Check path exists
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        expected_path = os.path.join(test_root, 'logs', 'signals', f'date={date_str}', 'asset=BTC', 'signals.jsonl')
        
        if os.path.exists(expected_path):
            print(f"  ✅ PASS: File created at {expected_path}")
            with open(expected_path) as f:
                record = json.loads(f.read())
                print(f"  ✅ Record: {record}")
        else:
            print(f"  ❌ FAIL: Expected file not found at {expected_path}")
            print(f"  Files created:")
            for root, dirs, files in os.walk(test_root):
                for file in files:
                    print(f"    - {os.path.join(root, file)}")
        
        # Test 2: Asset in record
        print("\n✓ Test 1b: Asset from record")
        write_jsonl('execution', {'symbol': 'ETH', 'qty': 1.5, 'ts': 1234567890})
        
        expected_path = os.path.join(test_root, 'logs', 'execution', f'date={date_str}', 'asset=ETH', 'execution.jsonl')
        
        if os.path.exists(expected_path):
            print(f"  ✅ PASS: File created at {expected_path}")
        else:
            print(f"  ❌ FAIL: Expected file not found")
        
        # Test 3: No asset (should use UNKNOWN)
        print("\n✓ Test 1c: No asset (fallback to UNKNOWN)")
        write_jsonl('health', {'status': 'ok', 'ts': 1234567890})
        
        expected_path = os.path.join(test_root, 'logs', 'health', f'date={date_str}', 'asset=UNKNOWN', 'health.jsonl')
        
        if os.path.exists(expected_path):
            print(f"  ✅ PASS: File created at {expected_path}")
        else:
            print(f"  ❌ FAIL: Expected file not found")
        
        print("\n" + "=" * 60)
        print("RESULT: llm_logging.py tests completed")
        print("=" * 60)
        
    finally:
        # Cleanup
        shutil.rmtree(test_root, ignore_errors=True)
        del os.environ['PAPER_TRADING_ROOT']


def test_log_emitter():
    """Test log_emitter.py writes to partitioned paths"""
    print("\n" + "=" * 60)
    print("TEST 2: log_emitter.py (LogEmitter)")
    print("=" * 60)
    
    import sys
    sys.path.insert(0, 'live_demo')
    from ops.log_emitter import LogEmitter
    
    # Create temp directory
    test_root = tempfile.mkdtemp(prefix='test_emitter_')
    
    try:
        emitter = LogEmitter(root=test_root)
        
        # Test signals emission
        print("\n✓ Test 2a: emit_signals with symbol")
        emitter.emit_signals(
            ts=1234567890.0,
            symbol='BTC',
            features={'rsi': 50},
            model_out={'p_up': 0.6, 'p_down': 0.3, 'p_neutral': 0.1, 's_model': 0.3},
            decision={'dir': 1, 'alpha': 0.05},
            cohort={'pros': 0.2, 'amateurs': -0.1}
        )
        
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        expected_path = os.path.join(test_root, 'signals', f'date={date_str}', 'asset=BTC', 'signals.jsonl')
        
        if os.path.exists(expected_path):
            print(f"  ✅ PASS: File created at {expected_path}")
            with open(expected_path) as f:
                record = json.loads(f.read())
                print(f"  ✅ Symbol in record: {record.get('symbol')}")
        else:
            print(f"  ❌ FAIL: Expected file not found at {expected_path}")
            print(f"  Files created:")
            for root, dirs, files in os.walk(test_root):
                for file in files:
                    print(f"    - {os.path.join(root, file)}")
        
        # Test execution emission
        print("\n✓ Test 2b: emit_execution with symbol")
        emitter.emit_execution(
            ts=1234567890.0,
            symbol='ETH',
            exec_resp={'side': 'BUY', 'qty': 1.5, 'price': 2000},
            risk_state={'target_position': 1.5}
        )
        
        expected_path = os.path.join(test_root, 'execution', f'date={date_str}', 'asset=ETH', 'execution.jsonl')
        
        if os.path.exists(expected_path):
            print(f"  ✅ PASS: File created at {expected_path}")
        else:
            print(f"  ❌ FAIL: Expected file not found")
        
        # Test costs emission
        print("\n✓ Test 2c: emit_costs with symbol")
        emitter.emit_costs(
            ts=1234567890.0,
            symbol='SOL',
            costs={'cost_bps': 5.0, 'impact_bps': 2.0}
        )
        
        expected_path = os.path.join(test_root, 'costs', f'date={date_str}', 'asset=SOL', 'costs.jsonl')
        
        if os.path.exists(expected_path):
            print(f"  ✅ PASS: File created at {expected_path}")
        else:
            print(f"  ❌ FAIL: Expected file not found")
        
        print("\n" + "=" * 60)
        print("RESULT: log_emitter.py tests completed")
        print("=" * 60)
        
    finally:
        # Cleanup
        shutil.rmtree(test_root, ignore_errors=True)


def verify_canonical_pattern():
    """Verify the canonical pattern is correct"""
    print("\n" + "=" * 60)
    print("CANONICAL PATTERN VERIFICATION")
    print("=" * 60)
    
    pattern = "paper_trading_outputs/{timeframe}/logs/{stream}/date=YYYY-MM-DD/asset={symbol}/{stream}.jsonl"
    
    print(f"\n✓ Canonical Pattern:")
    print(f"  {pattern}")
    
    print(f"\n✓ Example paths:")
    print(f"  paper_trading_outputs/5m/logs/signals/date=2024-01-20/asset=BTC/signals.jsonl")
    print(f"  paper_trading_outputs/5m/logs/execution/date=2024-01-20/asset=ETH/execution.jsonl")
    print(f"  paper_trading_outputs/1h/logs/costs/date=2024-01-20/asset=SOL/costs.jsonl")
    
    print(f"\n✓ Benefits:")
    print(f"  - Hive-style partitioning (efficient queries)")
    print(f"  - Filter by date: date=2024-01-20")
    print(f"  - Filter by asset: asset=BTC")
    print(f"  - Filter by timeframe: 5m/ vs 1h/")
    print(f"  - Auto-detection works reliably")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("TASK-4 VERIFICATION: Logging Path Standardization")
    print("=" * 60)
    
    try:
        test_llm_logging()
        test_log_emitter()
        verify_canonical_pattern()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review test results above")
        print("2. If all tests pass, commit changes")
        print("3. Run bot in offline mode to verify real logs")
        print("4. Check logs appear in new partitioned structure")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
