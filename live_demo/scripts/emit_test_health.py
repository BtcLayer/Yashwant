import time, os
from ops.log_emitter import get_emitter

em = get_emitter()
# Emit a test health record
ts = int(time.time() * 1000)
health = {
    "recent_bars": 5,
    "mean_p_down": 0.48,
    "mean_p_up": 0.52,
    "mean_s_model": 0.07,
    "exec_count_recent": 1,
    "funding_stale": False,
    "equity": 10000.0,
}
em.emit_health(ts=ts, symbol="BTCUSDT", health=health)
print("emitted", ts)
# Print path of created health file
root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        if fn.endswith("health.jsonl"):
            print("file", os.path.join(dirpath, fn))
