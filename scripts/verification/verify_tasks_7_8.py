
import sys
import os
import shutil
import tempfile
import json
from unittest.mock import MagicMock

# Setup path
sys.path.insert(0, 'live_demo')

from ops.log_router import LogRouter
from risk_and_exec import RiskAndExec, RiskConfig
from reason_codes import GuardReasonCode

def test_task_8_is_forced_flag():
    print("\n[TASK-8] Testing is_forced flag in logs...")
    tmp_dir = tempfile.mkdtemp()
    try:
        # Mock config
        cfg = {
            "sinks": {"llm_jsonl": True, "emitter": False},
            "topics": {"executions": "llm"}
        }
        router = LogRouter(cfg, base_root=tmp_dir)
        router.llm_root = tmp_dir # Override for test
        
        # Emit forced execution
        router.emit_execution(
            ts=1234567890, 
            asset="BTCUSDT", 
            exec_resp={"side": "BUY", "qty": 1.0, "price": 50000}, 
            risk_state={}, 
            is_forced=True,
            is_dry_run=True
        )
        
        # Check log file
        log_path = os.path.join(tmp_dir, "execution_log", f"date={1234567890}", "asset=BTCUSDT", "execution_log.jsonl")
        # Note: date path depends on my previous fix (Task 4), which uses current date if TS processing fails, 
        # or defaults. Let's just search recursively.
        import glob
        files = glob.glob(f"{tmp_dir}/**/*.jsonl", recursive=True)
        if not files:
            print("❌ No log files created.")
            return
            
        with open(files[0], 'r') as f:
            rec = json.loads(f.read())
            
        if rec.get("is_forced") is True and rec.get("is_dry_run") is True:
            print("✅ is_forced=True and is_dry_run=True found in log.")
        else:
            print(f"❌ Flags missing or incorrect: {rec}")

    finally:
        shutil.rmtree(tmp_dir)

def test_task_7_impact_guard():
    print("\n[TASK-7] Testing Impact Guard...")
    
    # Config with max_impact_bps = 50
    cfg = RiskConfig(
        base_notional=10000.0,
        impact_k=0.1, # High impact constant
        cost_bps=5.0,
        vol_floor=1.0 # Ensure RV is not zero so target calculation works
    )
    
    # Control config
    controls = {"max_impact_bps": 50.0}
    
    risk = RiskAndExec(MagicMock(), "BTCUSDT", cfg)
    risk._pos = 0.0
    
    # 1. Test Low Impact Trade (Should Pass)
    # Target 0.1 (10% of 10k = $1k). 
    # Qty at $10 = 100 units.
    # Impact bps = k * qty * 10000 = 0.1 * 100 * 10000 = 100,000 bps? Wait.
    # My formula was impact_bps = k * qty * 10000.
    # If k=0.1 (very high), qty=100 -> impact is huge.
    
    # Let's adjust inputs to be reasonable.
    # Max impact 50 bps. 
    # k = 0.0001 (more realistic per unit).
    # Qty = 1.0. Impact = 0.0001 * 1 * 10000 = 1 bps. PASS.
    
    cfg.impact_k = 0.0001
    
    decision = {'dir': 1, 'alpha': 0.1} # Target 0.1 pos
    # Expected Qty: 0.1 * 10000 / 1000 = 1.0 unit (at price 1000)
    
    res = risk.evaluate_pretrade_guards(
        decision, 
        ts_ms=1000, 
        last_price=1000.0, 
        controls=controls
    )
    
    if res['dir'] == 1:
        print("✅ Low impact trade passed.")
    else:
        print(f"❌ Low impact trade blocked: {res}")
        
    # 2. Test High Impact Trade (Should Block)
    # Increase k to 0.1
    # Qty=1.0. Impact = 0.1 * 1 * 10000 = 1000 bps. > 50 bps. BLOCK.
    cfg.impact_k = 0.1
    
    res = risk.evaluate_pretrade_guards(
        decision, 
        ts_ms=1000, 
        last_price=1000.0, 
        controls=controls
    )
    
    if res['dir'] == 0 and res['details'].get('mode') == GuardReasonCode.IMPACT_GUARD:
        print(f"✅ High impact trade blocked correctly. Details: {res['details']}")
    else:
        print(f"❌ High impact trade NOT blocked. Result: {res}")


if __name__ == "__main__":
    test_task_8_is_forced_flag()
    test_task_7_impact_guard()
