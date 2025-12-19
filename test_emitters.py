#!/usr/bin/env python3
"""Test script to verify emitters and logging infrastructure work correctly."""

import os
import sys
from datetime import datetime
import pytz

# Set up paths
os.environ["PAPER_TRADING_ROOT"] = "paper_trading_outputs/logs/test"
os.environ["STRATEGY_ID"] = "ensemble_test_v1.1"
os.environ["SCHEMA_VERSION"] = "v1.1"

IST = pytz.timezone("Asia/Kolkata")

def test_log_emitter():
    """Test the ops log emitter with v1.1 metadata."""
    print("Testing ops.log_emitter...")
    from ops.log_emitter import get_emitter
    
    emitter = get_emitter(bot_version="test", base_dir="paper_trading_outputs/logs/test")
    
    # Emit test signals
    emitter.emit_signals(
        ts=int(datetime.now(IST).timestamp() * 1000),
        symbol="BTCUSDT",
        features={"close": 100.0, "volume": 1000},
        model_out={"pred_bps": 50.0, "conf": 0.8},
        decision={"dir": 1, "alpha": 100.0},
        cohort="test"
    )
    
    # Emit test ensemble
    emitter.emit_ensemble(
        ts=int(datetime.now(IST).timestamp() * 1000),
        symbol="BTCUSDT",
        raw_preds={"s_model": 0.001, "p_up": 0.4, "p_down": 0.3},
        meta={"test": True}
    )
    
    print("✅ ops.log_emitter test passed")

def test_health_snapshot_emitter():
    """Test the health snapshot emitter."""
    print("\nTesting live_demo.emitters.health_snapshot_emitter...")
    from live_demo.emitters.health_snapshot_emitter import HealthSnapshotEmitter, HealthSnapshot
    
    emitter = HealthSnapshotEmitter(base_logs_dir="paper_trading_outputs/logs/test")
    
    snapshot = HealthSnapshot(
        equity_value=10000.0,
        drawdown_current=-0.01,
        daily_pnl=100.0,
        rolling_sharpe=1.5,
        trade_count=10,
        win_rate=0.6,
        turnover=0.5,
        error_counts=0,
        risk_breaches=0
    )
    
    emitter.maybe_emit(snapshot)
    print("✅ health_snapshot_emitter test passed")

def test_heartbeat():
    """Test heartbeat writing."""
    print("\nTesting ops.heartbeat...")
    from ops.heartbeat import write_heartbeat
    
    path = write_heartbeat(
        base_dir="paper_trading_outputs/logs",
        bot_version="test",
        last_bar_id=123
    )
    
    print(f"✅ Heartbeat written to: {path}")

def verify_files():
    """Verify that log files were created."""
    print("\nVerifying generated files...")
    
    test_dir = "paper_trading_outputs/logs/test"
    expected_files = [
        f"{test_dir}/signals/signals.jsonl",
        f"{test_dir}/ensemble/ensemble.jsonl",
        f"{test_dir}/1h/health_snapshot/snapshot.jsonl",
        "paper_trading_outputs/logs/test/heartbeat/heartbeat.json"
    ]
    
    all_exist = True
    for filepath in expected_files:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"  ✅ {filepath} ({size} bytes)")
        else:
            print(f"  ❌ {filepath} (NOT FOUND)")
            all_exist = False
    
    return all_exist

def main():
    """Run all emitter tests."""
    print("=" * 60)
    print("Ensemble v1.1 - Emitter & Logging Test")
    print("=" * 60)
    
    try:
        test_log_emitter()
        test_health_snapshot_emitter()
        test_heartbeat()
        
        if verify_files():
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED - Emitters working correctly!")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("❌ SOME FILES MISSING - Check errors above")
            print("=" * 60)
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
