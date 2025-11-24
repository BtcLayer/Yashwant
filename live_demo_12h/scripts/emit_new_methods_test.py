from live_demo.ops.log_emitter import get_emitter

em = get_emitter()
em.emit_order_intent({'ts': None, 'asset': 'BTCUSDT', 'decision': {'dir':1}})
em.emit_feature_log({'ts': None, 'asset': 'BTCUSDT', 'bar_id': 1, 'features': {'x':1}})
em.emit_calibration({'ts': None, 'asset': 'BTCUSDT', 'a':0.0, 'b':1.0, 'realized': 0.0})
em.emit_repro(ts=None, symbol='BTCUSDT', repro={'config':'ok'})
print('emitted new methods')
