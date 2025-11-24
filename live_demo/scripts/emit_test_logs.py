import os
from live_demo.ops.llm_logging import write_jsonl
from live_demo.ops.log_emitter import get_emitter

# Emit sample LLM JSONL log
write_jsonl('equity', {'event': 'test_equity', 'equity_value': 12345.67}, asset='BTCUSDT')

# Emit sample emitter JSONL log
em = get_emitter()
em.emit_health(ts=None, symbol='BTCUSDT', health={'status': 'ok', 'metric': 1})

base = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'paper_trading_outputs', 'logs'))
print('LOG_BASE:', base)
# List created top-level topic directories once
if os.path.isdir(base):
    entries = os.listdir(base)
    print('TOPICS:', ', '.join(sorted(entries)))
else:
    print('Log base does not exist')
