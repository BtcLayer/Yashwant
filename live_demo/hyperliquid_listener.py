import json
from typing import AsyncIterator, Dict, List, Optional
import aiohttp


class HyperliquidListener:
    def __init__(
        self,
        ws_url: str,
        addresses: List[str],
        coin: str = "BTC",
        mode: str = "public_trades",
    ):
        """
        mode: 'user_fills' (per-address, likely requires auth) or 'public_trades' (coin-wide prints)
        """
        self.ws_url = ws_url
        self.addresses = addresses
        self.coin = coin
        self.mode = mode
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(self.ws_url)
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
            # Public trades subscription using correct Hyperliquid format
            try:
                subscription = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "trades",
                        "coin": self.coin
                    }
                }
                await self._ws.send_json(subscription)
                print(f"📡 WebSocket: Sent subscription for {self.coin} trades")
                print(f"   Subscription payload: {subscription}")
                
                # Wait for subscription confirmation (with timeout)
                try:
                    import asyncio
                    msg = await asyncio.wait_for(self._ws.receive(), timeout=5.0)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        import json as _json
                        data = _json.loads(msg.data)
                        print(f"📥 WebSocket response: {data}")
                        if data.get("channel") == "subscriptionResponse":
                            sub_data = data.get("data", {})
                            print(f"✅ WebSocket: Subscription confirmed for {self.coin}")
                            print(f"   Response data: {sub_data}")
                        else:
                            print(f"📊 WebSocket: First message channel: {data.get('channel', 'unknown')}")
                            # Not a subscription response, but connection is live
                            # This is actually okay - some APIs send data immediately
                except asyncio.TimeoutError:
                    print(f"⚠️  WebSocket: No subscription confirmation within 5s")
                    print(f"   This may be normal - trying to receive data anyway...")
                except Exception as e:
                    print(f"⚠️  WebSocket: Confirmation check error: {e}")
            except (aiohttp.ClientError, TypeError, AttributeError) as e:
                print(f"❌ WebSocket: Subscription failed: {e}")
        return self

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
                # Public trades formats (best-effort)
                try:
                    # Example shape: {"type":"trades","data":[{...}]}
                    if (
                        isinstance(data, dict)
                        and data.get("type") == "trades"
                        and isinstance(data.get("data"), list)
                    ):
                        for t in data["data"]:
                            yield self._normalize_trade(t)
                        continue
                    # Example shape: {"channel":"trades","data":{...}} or list
                    if isinstance(data, dict) and data.get("channel") == "trades":
                        d = data.get("data")
                        if isinstance(d, list):
                            for t in d:
                                yield self._normalize_trade(t)
                        elif isinstance(d, dict):
                            yield self._normalize_trade(d)
                        continue
                except (KeyError, TypeError, ValueError):
                    # Ignore unknown/ill-formed message
                    continue

    def _normalize_trade(self, t: Dict) -> Dict:
        """Map varying trade payloads to a common dict for logging.
        Expected keys may include 'time' or 'ts', 'side', 'price' or 'px', 'size' or 'sz'.
        Hyperliquid specific: 'side' is 'A' (ask/sell) or 'B' (bid/buy)
        """
        # Time
        ts = int(t.get("time") or t.get("ts") or t.get("t") or 0)
        # Price/size across potential key variants
        price = float(t.get("price") or t.get("px") or t.get("p") or 0)
        size = float(
            t.get("size")
            or t.get("sz")
            or t.get("q")
            or t.get("qty")
            or t.get("quantity")
            or 0
        )
        # Side detection via string or boolean keys
        # Hyperliquid uses 'A' = ask/sell, 'B' = bid/buy
        side_raw = t.get("side") or t.get("s")
        side = str(side_raw).upper() if side_raw is not None else ""
        
        # Map Hyperliquid format to standard buy/sell
        if side == "A":
            side = "sell"
        elif side == "B":
            side = "buy"
        elif side:
            side = side.lower()
        
        if not side:
            # Fallback to boolean flags used by some feeds
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
