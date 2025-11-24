from live_demo.ops.log_emitter import get_emitter
em = get_emitter()
em.emit_signals(ts=None, symbol='BTCUSDT', features={'mom_1':0.01}, model_out={'s_model':0.1}, decision={'dir':1,'alpha':0.3}, cohort={'pros':0.1,'amateurs':-0.05,'mood':0.0})
print('emitted signals')
