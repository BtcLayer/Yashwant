import time
from typing import Tuple, Optional
import pandas as pd


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
        # Simple retry with backoff to withstand transient API hiccups
        last_err = None
        for attempt in range(3):
            try:
                k = self.client.klines(
                    symbol=self.symbol, interval=self.interval, limit=limit
                )
                break
            except Exception as e:  # broad catch to avoid crashing; upstream logs error
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        else:
            # Re-raise last error if all retries failed
            raise last_err
        rows = []
        for r in k:
            rows.append(
                {
                    "ts": int(r[0]),
                    "open": float(r[1]),
                    "high": float(r[2]),
                    "low": float(r[3]),
                    "close": float(r[4]),
                    "volume": float(r[5]),
                }
            )
        return pd.DataFrame(rows)

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
