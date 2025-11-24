"""Small Prometheus exporter scaffold for health summaries.

Provides a tiny HTTP endpoint exposing last-seen health metrics as Prometheus gauges.
This file is intentionally minimal — use as a scaffold to run in a small background thread or process.
"""

from prometheus_client import start_http_server, Gauge
import threading
import time

_gauges = {
    "mean_p_up": Gauge(
        "bot_health_mean_p_up", "Mean p_up over recent window", ["symbol"]
    ),
    "mean_p_down": Gauge(
        "bot_health_mean_p_down", "Mean p_down over recent window", ["symbol"]
    ),
    "mean_s_model": Gauge(
        "bot_health_mean_s_model", "Mean s_model over recent window", ["symbol"]
    ),
    "exec_count_recent": Gauge(
        "bot_health_exec_count_recent", "Executions in recent window", ["symbol"]
    ),
}

_last_values = {}


def update_health_metrics(symbol: str, health: dict):
    try:
        if health.get("mean_p_up") is not None:
            _gauges["mean_p_up"].labels(symbol=symbol).set(
                float(health.get("mean_p_up"))
            )
        if health.get("mean_p_down") is not None:
            _gauges["mean_p_down"].labels(symbol=symbol).set(
                float(health.get("mean_p_down"))
            )
        if health.get("mean_s_model") is not None:
            _gauges["mean_s_model"].labels(symbol=symbol).set(
                float(health.get("mean_s_model"))
            )
        if health.get("exec_count_recent") is not None:
            _gauges["exec_count_recent"].labels(symbol=symbol).set(
                int(health.get("exec_count_recent"))
            )
    except Exception:
        pass


def start_exporter(port: int = 8000, host: str = "0.0.0.0"):
    # Start prometheus client HTTP server on a background thread
    def _serve():
        start_http_server(port, addr=host)
        # keep thread alive
        while True:
            time.sleep(3600)

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    start_exporter()
    print("metrics exporter started on 8000")
    while True:
        time.sleep(3600)
