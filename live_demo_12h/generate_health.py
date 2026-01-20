import json
import os
from datetime import datetime

def save_health_snapshot(log_dir="paper_trading_outputs/12h/logs"):
    """
    Generate health snapshot for 12h bot by analyzing log files.
    
    Adapted from 5m bot implementation for 12h timeframe.
    """
    signals_path = os.path.join(log_dir, "signals.jsonl")
    snapshot_path = os.path.join(log_dir, "snapshot_health.jsonl")
    
    current_ts = int(datetime.now().timestamp() * 1000)
    
    stats = {
        "ts": current_ts,
        "timeframe": "12h",  # Explicit timeframe marker
        "connectivity": "OFFLINE_REPLAY" if os.environ.get('LIVE_DEMO_OFFLINE') == "1" else "CONNECTED",
        "streams": {"signals": 0, "orders": 0},
        "vetos": {"neutral_signal": 0, "risk_blocked": 0},
        "staleness_ms": None
    }

    # Find all signals.jsonl and order_intent.jsonl files recursively
    signals_files = []
    order_intent_files = []
    
    for root, dirs, files in os.walk(log_dir):
        if "signals.jsonl" in files:
            signals_files.append(os.path.join(root, "signals.jsonl"))
        if "order_intent.jsonl" in files:
            order_intent_files.append(os.path.join(root, "order_intent.jsonl"))

    if not signals_files and not order_intent_files:
        # If no logs yet, write snapshot with zero counts
        os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
        with open(snapshot_path, "a") as f:
            f.write(json.dumps(stats) + "\n")
        return

    # Parse logs to count events
    last_signal_ts = 0
    
    # Process Order Intent logs for pre-trade vetoes
    for oi_path in order_intent_files:
        try:
            with open(oi_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        data = json.loads(line)
                        rc = data.get("reason_codes", {})
                        
                        # In order_intent, False means FAILED/VETOED
                        # If intent was HOLD (side == HOLD), check why
                        if data.get("side") == "HOLD":
                            # Count all FALSE conditions as contributing vetoes
                            vetoed_by = []
                            for reason, passed in rc.items():
                                if passed is False:
                                    vetoed_by.append(reason)
                                    stats["vetos"][reason] = stats["vetos"].get(reason, 0) + 1
                            
                            # If no specific reason found but still HOLD, count as neutral/unknown
                            if not vetoed_by:
                                stats["vetos"]["neutral_signal"] = stats["vetos"].get("neutral_signal", 0) + 1

                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"⚠️ Error reading {oi_path}: {e}")

    # Process Signals logs for post-decision guards and general stats
    for s_path in signals_files:
        try:
            with open(s_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        data = json.loads(line)
                        stats["streams"]["signals"] += 1
                        
                        ts = data.get("ts", 0)
                        if ts > last_signal_ts:
                            last_signal_ts = ts
                        
                        # Count Decision Types
                        decision = data.get("decision") or data.get("sanitized", {}).get("decision") or {}
                        decision_dir = decision.get("dir", 0)
                        details = decision.get("details", {})
                        mode = details.get("mode", "")
                        
                        # Guard veto (post-decision) - only count if explicitly set mode
                        if decision_dir == 0 and mode:
                            try:
                                reason = mode
                                stats["vetos"][reason] = stats["vetos"].get(reason, 0) + 1
                            except Exception:
                                pass
                        
                        if decision_dir != 0:
                            stats["streams"]["orders"] += 1
                            
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"⚠️ Error reading {s_path}: {e}")

    # Calculate staleness
    if last_signal_ts > 0:
        stats["staleness_ms"] = current_ts - last_signal_ts

    # Save as a single line (JSONL)
    os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
    with open(snapshot_path, "a") as f:
        f.write(json.dumps(stats) + "\n")
    
    # Format summary for vetoes
    veto_summary = ", ".join([f"{k}: {v}" for k, v in stats["vetos"].items() if v > 0])
    print(f"✅ Health Snapshot generated at {snapshot_path}")
    print(f"📊 [12h] Summary: {stats['streams']['signals']} bars, {stats['streams']['orders']} orders. Vetoes: {veto_summary}. Staleness: {stats['staleness_ms']}ms")

if __name__ == "__main__":
    save_health_snapshot()
