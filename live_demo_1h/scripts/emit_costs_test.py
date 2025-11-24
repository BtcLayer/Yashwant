from live_demo.ops.log_emitter import get_emitter
em = get_emitter()
em.emit_costs(ts=None, symbol='BTCUSDT', costs={'trade_notional': 10.0, 'fee_bps': 5.0})
print('emitted costs')
