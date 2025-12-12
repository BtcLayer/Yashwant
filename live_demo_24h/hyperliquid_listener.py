import asyncio
import json
import os
import random
from typing import AsyncIterator, Dict, List, Optional
import aiohttp

_CONNECTION_SEMAPHORE = asyncio.Semaphore(
    max(1, int(os.environ.get("HL_WS_MAX_PARALLEL", "1")))
)


class HyperliquidListener:
    def __init__(
        self,
        ws_url: str,
        addresses: List[str],
        coin: str = "BTC",
        mode: str = "public_trades",
        connect_retries: int = 5,
        connect_backoff_s: float = 1.5,
    ):
        """
        mode: 'user_fills' (per-address, likely requires auth) or 'public_trades' (coin-wide prints)
        """
        self.ws_url = ws_url
        self.addresses = addresses
        self.coin = coin
        self.mode = mode
        self.connect_retries = max(1, int(connect_retries))
        self.connect_backoff_s = max(0.5, float(connect_backoff_s))
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        self._ws = await self._connect_with_backoff()
        # Best-effort subscription
        if self.mode == "user_fills" and self.addresses:
            for addr in self.addresses:
                # Placeholder subscription; real API may differ
                try:
                    await self._ws.send_json(
                        {"type": "subscribeUserFills", "user": addr}
                    )
                except (aiohttp.ClientError, TypeError, AttributeError):
                    pass
        else:
            # Public trades subscription; attempt several common patterns
            payloads = [
                {"type": "subscribe", "channel": "trades", "coin": self.coin},
                {"op": "subscribe", "channel": "trades", "coin": self.coin},
                {
                    "type": "subscribe",
                    "streams": [{"type": "trades", "coin": self.coin}],
                },
                {
                    "op": "subscribe",
                    "streams": [{"channel": "trades", "coin": self.coin}],
                },
                {"type": "subscribe", "channel": "trades"},
            ]
            for p in payloads:
                try:
                    await self._ws.send_json(p)
                    break
                except (aiohttp.ClientError, TypeError, AttributeError):
                    continue
        return self

    async def _connect_with_backoff(self) -> aiohttp.ClientWebSocketResponse:
        assert self._session is not None
        delay = self.connect_backoff_s
        attempt = 0
        last_error: Optional[BaseException] = None
        while attempt < self.connect_retries:
            attempt += 1
            jitter = random.uniform(0, 0.5)
            try:
                async with _CONNECTION_SEMAPHORE:
                    return await self._session.ws_connect(self.ws_url)
            except aiohttp.client_exceptions.WSServerHandshakeError as exc:
                last_error = exc
                status = getattr(exc, "status", None)
                if status != 429 or attempt >= self.connect_retries:
                    raise
            except aiohttp.ClientError as exc:
                last_error = exc
                if attempt >= self.connect_retries:
                    raise
            await asyncio.sleep(delay + jitter)
            delay = min(delay * 1.6, 15.0)
        if last_error:
            raise last_error
        raise RuntimeError("Hyperliquid websocket connection failed without exception")

    async def __aexit__(self, exc_type, exc, tb):
        if self._ws is not None:
            await self._ws.close()
        if self._session is not None:
            await self._session.close()

    async def stream(self) -> AsyncIterator[Dict]:
        assert self._ws is not None
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                # User fills format (placeholder)
                if isinstance(data, dict) and data.get("type") == "userFill":
                    try:
                        f = data.get("data", {})
                        yield {
                            "ts": int(f.get("time", 0)),
                            "address": f.get("user", ""),
                            "coin": f.get("coin", self.coin),
                            "side": f.get("side", ""),
                            "price": float(f.get("px", 0) or 0),
                            "size": float(f.get("sz", 0) or 0),
                            "source": "user",
                        }
                    except (KeyError, ValueError, TypeError):
                        continue
                try:
                    if (
                        isinstance(data, dict)
                        and data.get("type") == "trades"
                        and isinstance(data.get("data"), list)
                    ):
                        for t in data["data"]:
                            yield self._normalize_trade(t)
                        continue
                    if isinstance(data, dict) and data.get("channel") == "trades":
                        d = data.get("data")
                        if isinstance(d, list):
                            for t in d:
                                yield self._normalize_trade(t)
                        elif isinstance(d, dict):
                            yield self._normalize_trade(d)
                        continue
                except (KeyError, TypeError, ValueError):
                    continue

    def _normalize_trade(self, t: Dict) -> Dict:
        """Map varying trade payloads to a common dict for logging.
        Expected keys may include 'time' or 'ts', 'side', 'price' or 'px', 'size' or 'sz'.
        """
        ts = int(t.get("time") or t.get("ts") or t.get("t") or 0)
        price = float(t.get("price") or t.get("px") or t.get("p") or 0)
        size = float(
            t.get("size")
            or t.get("sz")
            or t.get("q")
            or t.get("qty")
            or t.get("quantity")
            or 0
        )
        side_raw = t.get("side") or t.get("s")
        side = str(side_raw).lower() if side_raw is not None else ""
        if not side:
            is_buy = t.get("isBuy")
            if is_buy is None:
                is_buy = t.get("is_buy")
            if isinstance(is_buy, bool):
                side = "buy" if is_buy else "sell"
        return {
            "ts": ts,
            "address": "",  # public stream has no user
            "coin": self.coin,
            "side": side,
            "price": price,
            "size": size,
            "source": "public",
        }
