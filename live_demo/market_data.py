import os
import time
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd

_CACHE_TTL_SECONDS = int(os.environ.get("WARMUP_CACHE_TTL", "600"))
_CACHE_DIR = Path(
    os.environ.get("WARMUP_CACHE_DIR")
    or Path(__file__).resolve().parents[1] / "paper_trading_outputs" / "cache"
)
try:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
_IN_MEMORY_CACHE = {}


def _cache_key(symbol: str, interval: str, limit: int) -> str:
    safe_symbol = symbol.replace("/", "_").replace(":", "_")
    safe_interval = interval.replace("/", "_")
    return f"{safe_symbol}_{safe_interval}_{int(limit)}"


def _cache_path(key: str) -> Path:
    return _CACHE_DIR / f"{key}.csv"


def _store_cache(key: str, df: pd.DataFrame) -> None:
    _IN_MEMORY_CACHE[key] = {"ts": time.time(), "df": df.copy()}
    try:
        df.to_csv(_cache_path(key), index=False)
    except Exception:
        pass


def _load_cache(key: str, fresh_only: bool = True) -> Optional[pd.DataFrame]:
    now = time.time()
    cached = _IN_MEMORY_CACHE.get(key)
    if cached and (not fresh_only or now - cached["ts"] <= _CACHE_TTL_SECONDS):
        return cached["df"].copy()
    path = _cache_path(key)
    if not path.exists():
        return None
    age = now - path.stat().st_mtime
    if fresh_only and age > _CACHE_TTL_SECONDS:
        return None
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    _IN_MEMORY_CACHE[key] = {"ts": now, "df": df.copy()}
    return df


def _rows_to_df(rows) -> pd.DataFrame:
    formatted = [
        {
            "ts": int(r[0]),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": float(r[5]),
        }
        for r in rows
    ]
    return pd.DataFrame(formatted)


def _rate_limit_delay(exc: Exception, attempt: int) -> float:
    text = str(exc).lower()
    if "too many requests" in text or "429" in text:
        return min(5.0 * (attempt + 1), 30.0)
    code = getattr(exc, "code", None)
    if isinstance(code, int) and code == -1003:
        return min(5.0 * (attempt + 1), 30.0)
    return 1.5 * (attempt + 1)


class MarketData:
    def __init__(self, client, symbol: str, interval: str = "5m"):
        self.client = client
        self.symbol = symbol
        self.interval = interval

    def get_book_ticker(self) -> Optional[dict]:
        """Return best bid/ask and sizes if available from client, else None."""
        # binance-connector UMFutures
        try:
            if hasattr(self.client, "book_ticker"):
                bt = self.client.book_ticker(symbol=self.symbol)
                # Expected keys: bidPrice, bidQty, askPrice, askQty
                bid = float(bt.get("bidPrice"))
                ask = float(bt.get("askPrice"))
                bid_qty = float(bt.get("bidQty", 0))
                ask_qty = float(bt.get("askQty", 0))
                return {"bid": bid, "ask": ask, "bid_qty": bid_qty, "ask_qty": ask_qty}
        except Exception:
            pass
        # python-binance
        try:
            if hasattr(self.client, "futures_book_ticker"):
                bt = self.client.futures_book_ticker(symbol=self.symbol)
                bid = float(bt.get("bidPrice"))
                ask = float(bt.get("askPrice"))
                bid_qty = float(bt.get("bidQty", 0))
                ask_qty = float(bt.get("askQty", 0))
                return {"bid": bid, "ask": ask, "bid_qty": bid_qty, "ask_qty": ask_qty}
        except Exception:
            pass
        return None

    def get_klines(self, limit: int = 1000) -> pd.DataFrame:
        cache_key = _cache_key(self.symbol, self.interval, limit)
        cached = _load_cache(cache_key)
        if cached is not None and not cached.empty:
            return cached

        last_err = None
        for attempt in range(3):
            try:
                raw = self.client.klines(
                    symbol=self.symbol, interval=self.interval, limit=limit
                )
                df = _rows_to_df(raw)
                if not df.empty:
                    _store_cache(cache_key, df)
                return df
            except Exception as e:
                last_err = e
                time.sleep(_rate_limit_delay(e, attempt))

        fallback = _load_cache(cache_key, fresh_only=False)
        if fallback is not None and not fallback.empty:
            return fallback
        raise last_err

    def poll_last_closed_kline(
        self,
    ) -> Optional[Tuple[int, float, float, float, float, float]]:
        """Return the most recently CLOSED kline by inspecting the second-to-last item.
        Many APIs return the last element as the in-progress candle; we use the prior one.
        """
        # Retry small fetch as well
        last_err = None
        for attempt in range(3):
            try:
                k = self.client.klines(
                    symbol=self.symbol, interval=self.interval, limit=2
                )
                break
            except Exception as e:
                last_err = e
                time.sleep(1.0 * (attempt + 1))
        else:
            # Surface last error so caller can decide what to do
            raise last_err
        if not k:
            return None
        # If only one kline, ensure it's closed by comparing close time
        if len(k) == 1:
            ot, o, h, l, c, v, ct = (
                int(k[0][0]),
                float(k[0][1]),
                float(k[0][2]),
                float(k[0][3]),
                float(k[0][4]),
                float(k[0][5]),
                int(k[0][6]),
            )
            return (ot, o, h, l, c, v) if ct <= int(time.time() * 1000) else None
        # Use second-to-last as the last closed
        ot, o, h, l, c, v = (
            int(k[-2][0]),
            float(k[-2][1]),
            float(k[-2][2]),
            float(k[-2][3]),
            float(k[-2][4]),
            float(k[-2][5]),
        )
        return ot, o, h, l, c, v
