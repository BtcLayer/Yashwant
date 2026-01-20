"""
Quick test to verify enhanced log emitter with schema-compliant fields
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ops.log_emitter import LogEmitter
import time
import json

def test_execution_logging():
    """Test execution logging with new is_forced and is_dry_run fields"""
    print("Testing execution logging...")
    
    emitter = LogEmitter()
    
    # Test 1: Organic model trade (not forced, dry run)
    exec_resp = {
        "side": "BUY",
        "qty": 0.001,
        "fill_price": 102500.0,
        "notional_usd": 102.5,
        "order_id": "test_001",
        "result": "FILLED"
    }
    
    risk_state = {
        "target_position": 0.001,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0
    }
    
    emitter.emit_execution(
        ts=time.time(),
        symbol="BTCUSDT",
        exec_resp=exec_resp,
        risk_state=risk_state,
        is_forced=False,  # Organic trade
        is_dry_run=True   # Paper trading
    )
    print("✓ Logged organic model trade (is_forced=False)")
    
    # Test 2: Forced smoke test trade
    emitter.emit_execution(
        ts=time.time(),
        symbol="BTCUSDT",
        exec_resp=exec_resp,
        risk_state=risk_state,
        is_forced=True,   # Forced/smoke test
        is_dry_run=True
    )
    print("✓ Logged forced smoke test trade (is_forced=True)")


def test_health_logging():
    """Test health logging with new loop_alive field"""
    print("\nTesting health logging...")
    
    emitter = LogEmitter()
    
    health_data = {
        "latency_ms": 45.2,
        "last_kline_ts": "2026-01-19T10:00:00Z",
        "data_freshness_ok": True,
        "cpu": 15.5,
        "mem": 512
    }
    
    emitter.emit_health(
        ts=time.time(),
        symbol="BTCUSDT",
        health=health_data,
        loop_alive=True
    )
    print("✓ Logged health with loop_alive=True")


def verify_log_files():
    """Verify the log files were created and contain expected fields"""
    print("\nVerifying log files...")
    
    log_base = "../../paper_trading_outputs/logs/default"
    
    # Check execution log
    exec_log = os.path.join(log_base, "execution", "execution.jsonl")
    if os.path.exists(exec_log):
        with open(exec_log, 'r') as f:
            lines = f.readlines()
            if lines:
                last_record = json.loads(lines[-1])
                print(f"\n📄 Latest execution log:")
                print(f"   is_forced: {last_record.get('is_forced')}")
                print(f"   is_dry_run: {last_record.get('is_dry_run')}")
                print(f"   side: {last_record.get('side')}")
                print(f"   qty: {last_record.get('qty')}")
                
                if 'is_forced' in last_record and 'is_dry_run' in last_record:
                    print("   ✅ Schema-compliant fields present!")
                else:
                    print("   ⚠️  Missing schema fields")
    
    # Check health log
    health_log = os.path.join(log_base, "health", "health.jsonl")
    if os.path.exists(health_log):
        with open(health_log, 'r') as f:
            lines = f.readlines()
            if lines:
                last_record = json.loads(lines[-1])
                print(f"\n📄 Latest health log:")
                print(f"   loop_alive: {last_record.get('loop_alive')}")
                print(f"   latency_ms: {last_record.get('latency_ms')}")
                
                if 'loop_alive' in last_record:
                    print("   ✅ Schema-compliant fields present!")
                else:
                    print("   ⚠️  Missing schema fields")


if __name__ == "__main__":
    print("="*60)
    print("Enhanced Log Emitter Test")
    print("="*60)
    
    test_execution_logging()
    test_health_logging()
    verify_log_files()
    
    print("\n" + "="*60)
    print("✅ Test complete! Check logs in paper_trading_outputs/logs/")
    print("="*60)
