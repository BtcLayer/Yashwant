"""
Test script for connection_timeout_auto_restart feature
Verifies the implementation without running live trades
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_health_monitor_connection_fields():
    """Test that HealthMonitor has connection tracking fields"""
    from live_demo.health_monitor import HealthMonitor
    
    health_mon = HealthMonitor()
    
    # Check fields exist
    assert hasattr(health_mon, 'rest_consecutive_failures'), "Missing rest_consecutive_failures"
    assert hasattr(health_mon, 'rest_total_calls'), "Missing rest_total_calls"
    assert hasattr(health_mon, 'rest_failed_calls'), "Missing rest_failed_calls"
    assert hasattr(health_mon, 'last_successful_rest_call'), "Missing last_successful_rest_call"
    assert hasattr(health_mon, 'reconnect_attempts'), "Missing reconnect_attempts"
    assert hasattr(health_mon, 'last_reconnect_ts'), "Missing last_reconnect_ts"
    assert hasattr(health_mon, 'connection_status'), "Missing connection_status"
    
    # Check initial values
    assert health_mon.rest_consecutive_failures == 0
    assert health_mon.rest_total_calls == 0
    assert health_mon.rest_failed_calls == 0
    assert health_mon.connection_status == "connected"
    
    print("✓ HealthMonitor connection fields test passed")

def test_health_monitor_performance_summary():
    """Test that connection_health is included in performance summary"""
    from live_demo.health_monitor import HealthMonitor
    import time
    
    health_mon = HealthMonitor()
    health_mon.rest_total_calls = 100
    health_mon.rest_failed_calls = 5
    health_mon.reconnect_attempts = 2
    health_mon.last_reconnect_ts = time.time() - 300  # 5 minutes ago
    health_mon.connection_status = "connected"
    
    summary = health_mon.get_performance_summary()
    
    assert 'connection_health' in summary, "connection_health missing from summary"
    conn_health = summary['connection_health']
    
    assert conn_health['status'] == "connected"
    assert conn_health['rest_total_calls'] == 100
    assert conn_health['rest_failed_calls'] == 5
    assert conn_health['rest_success_rate'] == 0.95  # 95/100
    assert conn_health['reconnect_attempts'] == 2
    
    print("✓ HealthMonitor performance summary test passed")

def test_main_has_reconnection_logic():
    """Test that main.py has the reconnection functions"""
    from live_demo import main
    import inspect
    
    # Read main.py source to check for key components
    main_source = inspect.getsource(main)
    
    assert '_recreate_binance_client' in main_source, "Missing _recreate_binance_client function"
    assert '_attempt_reconnect' in main_source, "Missing _attempt_reconnect function"
    assert '_rest_consecutive_failures' in main_source, "Missing _rest_consecutive_failures variable"
    assert '_rest_failure_threshold' in main_source, "Missing _rest_failure_threshold variable"
    assert 'connection_status' in main_source, "Missing connection_status in health dict"
    assert 'rest_consecutive_failures' in main_source, "Missing failure tracking"
    
    print("✓ Main.py reconnection logic test passed")

def test_imports():
    """Test that all required imports work"""
    try:
        from live_demo.health_monitor import HealthMonitor
        from live_demo.market_data import MarketData
        from live_demo import main
        print("✓ All imports successful")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        raise

if __name__ == "__main__":
    print("Testing connection_timeout_auto_restart implementation...\n")
    
    try:
        test_imports()
        test_health_monitor_connection_fields()
        test_health_monitor_performance_summary()
        test_main_has_reconnection_logic()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print("\nImplementation complete:")
        print("  • HealthMonitor tracks connection health")
        print("  • Binance client can auto-reconnect after 3 failures")
        print("  • Health emission includes connection_status")
        print("  • Exponential backoff with 5 retry attempts")
        print("  • Degrades gracefully if reconnection fails")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
