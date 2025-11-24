import os
import pandas as pd
from datetime import datetime, timezone


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FILES = {
    "ohlc": os.path.join(ROOT, "ohlc_btc_5m.csv"),
    "funding": os.path.join(ROOT, "funding_btc.csv"),
    "leaderboard": os.path.join(ROOT, "leaderboard.csv"),
    "fills": os.path.join(ROOT, "historical_trades_btc.csv"),
    "live_top": os.path.join(ROOT, "live_demo", "top_cohort.csv"),
    "live_bottom": os.path.join(ROOT, "live_demo", "bottom_cohort.csv"),
}


def ts(ms: int) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except Exception:
        return str(ms)


def span(df: pd.DataFrame, ts_candidates=("timestamp", "time", "Timestamp")):
    for c in ts_candidates:
        if c in df.columns:
            try:
                s = pd.to_numeric(df[c], errors="coerce").dropna().astype(int)
                if len(s) > 0:
                    return ts(s.min()), ts(s.max())
            except Exception:
                pass
    return None, None


def main():
    print("SCRAPE STATUS SNAPSHOT")
    for name, path in FILES.items():
        if not os.path.exists(path):
            print(f"- {name}: (missing)")
            continue
        try:
            # read small sample to get header and then entire df shape efficiently
            df = pd.read_csv(path)
            n = len(df)
            mb = os.path.getsize(path) / (1024 * 1024)
            t0, t1 = span(df)
            extra = f" span: {t0} -> {t1}" if t0 and t1 else ""
            print(f"- {name}: {n:,} rows ({mb:.1f} MB){extra}")
        except Exception as e:
            print(f"- {name}: error reading: {e}")


if __name__ == "__main__":
    main()
