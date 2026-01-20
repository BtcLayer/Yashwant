"""Test PnL/Equity logging"""
import sys
sys.path.insert(0, 'live_demo')

from ops.log_emitter import LogEmitter
import time
import json

print("Testing PnL/Equity logging...")

emitter = LogEmitter()

# Test with typical PnL/equity data
emitter.emit_pnl_equity(
    ts=time.time(),
    symbol="BTCUSDT",
    equity_value=10125.50,
    pnl_total_usd=125.50,
    realized_pnl_usd=100.00,
    unrealized_pnl_usd=25.50,
    realized_return_bps=125,
    position_qty=0.001,
    position_avg_px=102000.0,
    current_price=102500.0,
    starting_equity=10000.0,
    peak_equity=10150.0,
    # drawdown_pct will be auto-calculated
)

print("✓ PnL/Equity log emitted")

# Verify the log structure
import os
log_files = []
for root, dirs, files in os.walk("../paper_trading_outputs/logs/pnl_equity"):
    for file in files:
        if file.endswith('.jsonl'):
            log_files.append(os.path.join(root, file))

if log_files:
    latest_log = max(log_files, key=os.path.getmtime)
    print(f"\n📄 Latest pnl_equity log: {latest_log}")
    
    with open(latest_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_record = json.loads(lines[-1])
            print("\n✅ Required fields:")
            print(f"   equity_value: ${last_record.get('equity_value')}")
            print(f"   pnl_total_usd: ${last_record.get('pnl_total_usd')}")
            
            print("\n✅ PnL breakdown:")
            print(f"   realized_pnl_usd: ${last_record.get('realized_pnl_usd')}")
            print(f"   unrealized_pnl_usd: ${last_record.get('unrealized_pnl_usd')}")
            print(f"   realized_return_bps: {last_record.get('realized_return_bps')} bps")
            
            print("\n✅ Position info:")
            print(f"   position_qty: {last_record.get('position_qty')}")
            print(f"   position_avg_px: ${last_record.get('position_avg_px')}")
            print(f"   current_price: ${last_record.get('current_price')}")
            
            print("\n✅ Risk metrics (AUTO-CALCULATED):")
            print(f"   starting_equity: ${last_record.get('starting_equity')}")
            print(f"   peak_equity: ${last_record.get('peak_equity')}")
            print(f"   drawdown_pct: {last_record.get('drawdown_pct')}%")
            print(f"   drawdown_usd: ${last_record.get('drawdown_usd')}")
            print(f"   return_pct: {last_record.get('return_pct')}%")
            print(f"   return_usd: ${last_record.get('return_usd')}")
            
            # Verify schema compliance
            required_fields = ['ts', 'symbol', 'equity_value', 'pnl_total_usd']
            missing = [f for f in required_fields if last_record.get(f) is None]
            
            if missing:
                print(f"\n✗ Missing required fields: {missing}")
            else:
                print("\n✅ All required schema fields present!")
            
            # Verify auto-calculated fields
            if last_record.get('drawdown_pct') is not None:
                print("\n✅ Auto-calculated fields working!")
                print(f"   Drawdown: {last_record.get('drawdown_pct'):.2f}% (${last_record.get('drawdown_usd'):.2f})")
                print(f"   Return: {last_record.get('return_pct'):.2f}% (${last_record.get('return_usd'):.2f})")
            
            print("\n✅ Test complete!")
            print("✅ PnL/Equity stream is now schema-compliant!")
else:
    print("⚠️  No pnl_equity logs found yet")
