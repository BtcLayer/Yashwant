import aiohttp
import asyncio
from typing import Optional, Dict, Any, Tuple
import os
import json


class FundingHL:
    def __init__(
        self,
        rest_url: str,
        coin: str = "BTC",
        path: str = "/v1/funding",
        key_time: str = "time",
        key_rate: str = "funding",
        mode: str = "settled",  # 'settled' (epoch-aligned) or 'predicted' (TTL)
        epoch_hours: int = 8,     # used when mode='settled'
        ttl_seconds: int = 600,   # used when mode='predicted'
        binance_client: Optional[object] = None,
        binance_symbol: str = "BTCUSDT",
        # Robustness knobs
        request_timeout_s: float = 15.0,
        retries: int = 2,
        retry_backoff_s: float = 0.75,
    ) -> None:
        self.rest_url = rest_url.rstrip("/")
        self.coin = coin
        self.path = path
        self.key_time = key_time
        self.key_rate = key_rate
        self.mode = mode
        self.epoch_hours = max(1, int(epoch_hours))
        self.ttl_seconds = max(60, int(ttl_seconds))
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_good: Optional[Dict[str, Any]] = None
        self._next_refresh_ts_ms: Optional[int] = None
        self._binance_client = binance_client
        self._binance_symbol = binance_symbol
        # Robustness settings
        self._request_timeout_s = float(request_timeout_s)
        self._retries = max(0, int(retries))
        self._retry_backoff_s = max(0.0, float(retry_backoff_s))

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def close(self):
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def fetch_latest(self) -> Optional[Dict[str, Any]]:
        """
        Returns dict with {'ts': epoch_ms, 'coin': 'BTC', 'funding': float, 'stale': bool}
        Strategy:
          1) Try GET "{rest_url}{path}?coin={coin}" (legacy style used by our config)
          2) If that fails, try POST to "{rest_url}" with common Info API payloads
             e.g., {"type":"funding","coin": coin} or {"type":"fundingHistory","coin": coin}
          3) Heuristically parse payloads for time/rate keys across variants
        Caching: If a fresh value is available within TTL/epoch, return cached with stale=False.
        If network/parse fails but a prior good value exists, return it with stale=True.
        """
        # If we have a cached value and caching policy says still valid, return it
        if self._last_good is not None and self._next_refresh_ts_ms is not None:
            import time

            now_ms = int(time.time() * 1000)
            if now_ms < self._next_refresh_ts_ms:
                # Within cache window
                fresh = dict(self._last_good)
                fresh["stale"] = False
                return fresh

        # PRIORITY FIX: If Binance client is available and rest_url is Hyperliquid default,
        # skip Hyperliquid API calls entirely (they timeout when not accessible)
        if self._binance_client is not None and "hyperliquid" in self.rest_url.lower():
            fb = await self._fetch_binance_fallback()
            if fb is not None:
                return fb

        await self._ensure_session()
        # 1) Try GET on configured path (legacy) with retries
        url = f"{self.rest_url}{self.path}?coin={self.coin}"
        for attempt in range(self._retries + 1):
            try:
                assert self._session is not None
                async with self._session.get(url, timeout=self._request_timeout_s) as r:
                    if r.status == 200:
                        data = await r.json()
                        self._write_debug(
                            {
                                "source": "GET",
                                "attempt": attempt,
                                "url": url,
                                "status": r.status,
                                "data": data,
                            }
                        )
                        parsed = self._extract_funding(data)
                        if parsed is not None:
                            ts, rate = parsed
                            out = {
                                "ts": ts,
                                "coin": self.coin,
                                "funding": rate,
                                "stale": False,
                            }
                            self._next_refresh_ts_ms = self._compute_next_refresh(ts)
                            self._last_good = out
                            return out
                    else:
<<<<<<< HEAD
                        self._write_debug({'source': 'GET', 'attempt': attempt, 'url': url, 'status': r.status, 'note': 'non_200'})
            except (aiohttp.ClientError, ValueError, KeyError, AssertionError, TypeError) as e:
                self._write_debug({'source': 'GET', 'attempt': attempt, 'url': url, 'error': f'request_failed: {e}'})
            # backoff before next attempt if any
=======
                        self._write_debug(
                            {
                                "source": "GET",
                                "attempt": attempt,
                                "url": url,
                                "status": r.status,
                                "note": "non_200",
                            }
                        )
            except (
                aiohttp.ClientError,
                ValueError,
                KeyError,
                AssertionError,
                TypeError,
            ) as e:
                self._write_debug(
                    {
                        "source": "GET",
                        "attempt": attempt,
                        "url": url,
                        "error": f"request_failed: {e}",
                    }
                )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
            if attempt < self._retries:
                await asyncio.sleep(self._retry_backoff_s)
        # 2) Try fundingHistory with explicit time window (matches working scraper pattern)
        import time as _time

        now_ms = int(_time.time() * 1000)
        # Use a 48h window to be safe and pick the last record
        start_ms = now_ms - 48 * 60 * 60 * 1000
        payload = {
            "type": "fundingHistory",
            "coin": self.coin,
            "startTime": start_ms,
            "endTime": now_ms,
        }
        for attempt in range(self._retries + 1):
            try:
                assert self._session is not None
                async with self._session.post(
                    self.rest_url, json=payload, timeout=self._request_timeout_s
                ) as r:
                    if r.status != 200:
<<<<<<< HEAD
                        self._write_debug({'source': 'POST', 'attempt': attempt, 'url': self.rest_url, 'payload': payload, 'status': r.status})
                        # Try again if attempts remain
=======
                        self._write_debug(
                            {
                                "source": "POST",
                                "attempt": attempt,
                                "url": self.rest_url,
                                "payload": payload,
                                "status": r.status,
                            }
                        )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
                        if attempt < self._retries:
                            await asyncio.sleep(self._retry_backoff_s)
                            continue
                        break
                    data = await r.json()
<<<<<<< HEAD
                    self._write_debug({'source': 'POST', 'attempt': attempt, 'url': self.rest_url, 'payload': payload, 'status': r.status, 'data': data})
                    # fundingHistory returns a list; take the last record
=======
                    self._write_debug(
                        {
                            "source": "POST",
                            "attempt": attempt,
                            "url": self.rest_url,
                            "payload": payload,
                            "status": r.status,
                            "data": data,
                        }
                    )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
                    if isinstance(data, list) and data:
                        last = data[-1]
                    elif (
                        isinstance(data, dict)
                        and isinstance(data.get("data"), list)
                        and data["data"]
                    ):
                        last = data["data"][-1]
                    else:
                        self._write_debug({'source': 'POST', 'attempt': attempt, 'url': self.rest_url, 'payload': payload, 'status': r.status, 'parse': 'no_list'})
                        # Try again if attempts remain
                        if attempt < self._retries:
                            await asyncio.sleep(self._retry_backoff_s)
                            continue
                        break
                    # Extract time and fundingRate
                    try:
                        ts = int(last.get("time"))
                        rate = float(last.get("fundingRate"))
                    except (ValueError, TypeError, AttributeError, KeyError):
                        # Fallback to heuristic parser
                        parsed = self._extract_funding(last)
                        if parsed is None:
                            self._write_debug({'source': 'POST', 'attempt': attempt, 'url': self.rest_url, 'payload': payload, 'status': r.status, 'parse': 'no_match_last'})
                            if attempt < self._retries:
                                await asyncio.sleep(self._retry_backoff_s)
                                continue
                            break
                        ts, rate = parsed
                    out = {"ts": ts, "coin": self.coin, "funding": rate, "stale": False}
                    self._next_refresh_ts_ms = self._compute_next_refresh(ts)
                    self._last_good = out
                    return out
            except (
                aiohttp.ClientError,
                ValueError,
                KeyError,
                AssertionError,
                TypeError,
            ) as e:
                self._write_debug(
                    {
                        "source": "POST",
                        "attempt": attempt,
                        "url": self.rest_url,
                        "payload": payload,
                        "error": f"request_failed: {e}",
                    }
                )
                if attempt < self._retries:
                    await asyncio.sleep(self._retry_backoff_s)
                    continue
                break
        # 3) Fallback to stale or None
        # 2.5) Try Binance fallback if configured
        fb = await self._fetch_binance_fallback()
        if fb is not None:
            return fb
        if self._last_good is not None:
            stale = dict(self._last_good)
            stale["stale"] = True
            return stale
        return None

    def _compute_next_refresh(self, ts_ms: int) -> int:
<<<<<<< HEAD
        """
        Given the timestamp (ms) of the funding payload, compute next refresh boundary.
        - settled: next multiple of epoch_hours from the hour of ts (UTC-aligned assumption)
        - predicted: ts + ttl_seconds
        """
        if self.mode == 'predicted':
=======
        if self.mode == "predicted":
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
            return ts_ms + self.ttl_seconds * 1000
        # settled mode: align to epoch grid using ts_ms
        import datetime

        dt = datetime.datetime.utcfromtimestamp(ts_ms / 1000.0).replace(
            minute=0, second=0, microsecond=0
        )
        h = dt.hour
        step = self.epoch_hours
        next_bucket = ((h // step) + 1) * step
        # roll to next day if needed
        add_days = 0
        if next_bucket >= 24:
            next_bucket -= 24
            add_days = 1
        dt_next = (dt + datetime.timedelta(days=add_days)).replace(hour=next_bucket)
        return int(dt_next.timestamp() * 1000)

    # --------- payload extraction helpers ---------
    def _extract_funding(self, data: Any) -> Optional[Tuple[int, float]]:
        """
        Heuristically parse various response shapes and find a (ts_ms, rate) pair.
        Accepted shapes include:
          - dict with keys like {'time', 'funding'}
          - dict with 'data' -> dict or list-of-dicts
          - list of dicts (take last)
        Time keys tried: [self.key_time, 'time','ts','timestamp','t']
        Rate keys tried: [self.key_rate, 'funding','fundingRate','rate','currentFunding','predictedFunding','predictedFundingRate']
        Returns None if no reasonable pair found.
        """
        # If list, take last element
        if isinstance(data, list) and data:
            data = data[-1]
        if not isinstance(data, dict):
            return None
        # If wrapped in {'data': ...}, unwrap
        candidate = data
        if "data" in data:
            d = data.get("data")
            if isinstance(d, list) and d:
                candidate = d[-1]
            elif isinstance(d, dict):
                candidate = d
        # Now candidate should be a dict with possible keys
        if not isinstance(candidate, dict):
            return None
        time_keys = [self.key_time, "time", "ts", "timestamp", "t"]
        rate_keys = [
            self.key_rate,
            "funding",
            "fundingRate",
            "rate",
            "currentFunding",
            "predictedFunding",
            "predictedFundingRate",
        ]
        ts_val = None
        rate_val = None
        for k in time_keys:
            if k and k in candidate:
                try:
                    ts_val = int(candidate[k])
                    break
                except (ValueError, TypeError):
                    continue
        for k in rate_keys:
            if k and k in candidate:
                try:
                    rate_val = float(candidate[k])
                    break
                except (ValueError, TypeError):
                    continue
        if ts_val is None or rate_val is None:
            return None
        # Normalize ts to ms if in seconds
        if ts_val < 1_000_000_000_000:  # < ~2001-09-09 in ms
            ts_val *= 1000
        return ts_val, rate_val

    def _write_debug(self, record: Dict[str, Any]) -> None:
        """Write funding fetch/parse debug info to paper_trading_outputs/funding_debug.json (best-effort)."""
        try:
<<<<<<< HEAD
            # Prefer unified PAPER_TRADING_ROOT if set; otherwise resolve to repo-level paper_trading_outputs
            env_root = os.environ.get('PAPER_TRADING_ROOT')
            if env_root:
                # If env points to a timeframe subdir (e.g., .../paper_trading_outputs/12h), write at its parent root
                pt_root = os.path.abspath(os.path.join(env_root, os.pardir))
            else:
                # live_demo_12h/... -> repo_root (..)
                repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
                pt_root = os.path.join(repo_root, 'paper_trading_outputs')
            out_dir = os.path.abspath(pt_root)
=======
            out_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "paper_trading_outputs")
            )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, "funding_debug.json")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False))
                f.write("\n")
        except OSError:
            pass

    async def _fetch_binance_fallback(self) -> Optional[Dict[str, Any]]:
        """Try to get funding from Binance UMFutures premium index endpoint as a proxy.
        Returns same shape: {'ts': epoch_ms, 'coin': self.coin, 'funding': float, 'stale': False}
        """
        if self._binance_client is None:
            return None
        try:
<<<<<<< HEAD
            # Try binance-connector UMFutures premium_index
            if hasattr(self._binance_client, 'premium_index'):
                resp = self._binance_client.premium_index(symbol=self._binance_symbol)
                # Expect dict with 'lastFundingRate' and 'nextFundingTime' or server time
                rate = float(resp.get('lastFundingRate')) if isinstance(resp, dict) and resp.get('lastFundingRate') is not None else None
                ts = int(resp.get('nextFundingTime')) if isinstance(resp, dict) and resp.get('nextFundingTime') is not None else None
=======
            if hasattr(self._binance_client, "premium_index"):
                resp = self._binance_client.premium_index(symbol=self._binance_symbol)
                rate = (
                    float(resp.get("lastFundingRate"))
                    if isinstance(resp, dict)
                    and resp.get("lastFundingRate") is not None
                    else None
                )
                ts = (
                    int(resp.get("nextFundingTime"))
                    if isinstance(resp, dict)
                    and resp.get("nextFundingTime") is not None
                    else None
                )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
                if rate is None:
                    raise ValueError("missing lastFundingRate")
                if ts is None:
                    import time

                    ts = int(time.time() * 1000)
<<<<<<< HEAD
                out = {"ts": ts, "coin": self.coin, "funding": rate, "stale": False, "source": "binance"}
                self._write_debug({'source': 'BINANCE', 'symbol': self._binance_symbol, 'data': resp})
                # Cache policy: for fallback, refresh in 10 minutes
                self._next_refresh_ts_ms = ts + 10 * 60 * 1000
                self._last_good = out
                return out
            # python-binance
            if hasattr(self._binance_client, 'futures_premium_index'):
                resp = self._binance_client.futures_premium_index(symbol=self._binance_symbol)
                rate = float(resp.get('lastFundingRate')) if isinstance(resp, dict) and resp.get('lastFundingRate') is not None else None
                ts = int(resp.get('nextFundingTime')) if isinstance(resp, dict) and resp.get('nextFundingTime') is not None else None
=======
                out = {
                    "ts": ts,
                    "coin": self.coin,
                    "funding": rate,
                    "stale": False,
                    "source": "binance",
                }
                self._write_debug(
                    {"source": "BINANCE", "symbol": self._binance_symbol, "data": resp}
                )
                self._next_refresh_ts_ms = ts + 10 * 60 * 1000
                self._last_good = out
                return out
            if hasattr(self._binance_client, "futures_premium_index"):
                resp = self._binance_client.futures_premium_index(
                    symbol=self._binance_symbol
                )
                rate = (
                    float(resp.get("lastFundingRate"))
                    if isinstance(resp, dict)
                    and resp.get("lastFundingRate") is not None
                    else None
                )
                ts = (
                    int(resp.get("nextFundingTime"))
                    if isinstance(resp, dict)
                    and resp.get("nextFundingTime") is not None
                    else None
                )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
                if rate is None:
                    raise ValueError("missing lastFundingRate")
                if ts is None:
                    import time

                    ts = int(time.time() * 1000)
                out = {
                    "ts": ts,
                    "coin": self.coin,
                    "funding": rate,
                    "stale": False,
                    "source": "binance",
                }
                self._write_debug(
                    {"source": "BINANCE", "symbol": self._binance_symbol, "data": resp}
                )
                self._next_refresh_ts_ms = ts + 10 * 60 * 1000
                self._last_good = out
                return out
        except (KeyError, ValueError, TypeError, AttributeError) as e:
            self._write_debug(
                {"source": "BINANCE", "symbol": self._binance_symbol, "error": str(e)}
            )
            return None
