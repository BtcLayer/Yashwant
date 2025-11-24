import asyncio
import aiohttp
import csv
import json
import os
import time
from typing import List, Dict, Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
TOP = os.path.join(ROOT, 'live_demo', 'top_cohort.csv')
BOT = os.path.join(ROOT, 'live_demo', 'bottom_cohort.csv')
BASE_URL = 'https://api.hyperliquid.xyz/info'

DAY_MS = 24*60*60*1000
WINDOWS = {
    '1d': 1*DAY_MS,
    '1w': 7*DAY_MS,
    '1m': 30*DAY_MS,
    '6m': 180*DAY_MS,
}

SAMPLE = 150  # limit to keep it quick
TIMEOUT = 15
CONCURRENCY = 16


def load_addrs(path: str) -> List[str]:
    addrs: List[str] = []
    with open(path, 'r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            a = (row.get('Account') or '').strip().lower()
            if a:
                addrs.append(a)
    # dedupe preserving order
    seen = set()
    out: List[str] = []
    for a in addrs:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


def to_iso(ts_ms: int) -> str:
    try:
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts_ms/1000.0))
    except Exception:
        return ''


async def fetch_addr(session: aiohttp.ClientSession, addr: str, start_ms: int, end_ms: int) -> Dict[str, Any]:
    payload = {"type": "userFillsByTime", "user": addr, "startTime": start_ms, "endTime": end_ms}
    try:
        async with session.post(BASE_URL, json=payload, timeout=TIMEOUT) as r:
            if r.status != 200:
                return {"addr": addr, "fills_btc": 0, "fills_any": 0, "status": r.status}
            data = await r.json()
            if not isinstance(data, list):
                return {"addr": addr, "fills_btc": 0, "fills_any": 0, "status": "bad_shape"}
            fills_any = len(data)
            fills_btc = sum(1 for f in data if str(f.get('coin', '')).upper() == 'BTC')
            return {"addr": addr, "fills_btc": fills_btc, "fills_any": fills_any, "status": 200}
    except Exception as e:
        return {"addr": addr, "fills_btc": 0, "fills_any": 0, "status": f"err:{type(e).__name__}"}


async def main():
    top = load_addrs(TOP)
    bot = load_addrs(BOT)
    cohort = list(dict.fromkeys(top + bot))[:SAMPLE]
    now_ms = int(time.time() * 1000)

    results: Dict[str, Any] = {}
    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession() as session:
        for label, win in WINDOWS.items():
            start_ms = now_ms - win
            end_ms = now_ms

            async def wrapped(addr: str):
                async with sem:
                    return await fetch_addr(session, addr, start_ms, end_ms)

            outs = await asyncio.gather(*(wrapped(a) for a in cohort))
            actives_btc = sum(1 for o in outs if isinstance(o.get('fills_btc'), int) and o['fills_btc'] > 0)
            total_btc = sum(int(o.get('fills_btc') or 0) for o in outs)
            actives_any = sum(1 for o in outs if isinstance(o.get('fills_any'), int) and o['fills_any'] > 0)
            total_any = sum(int(o.get('fills_any') or 0) for o in outs)
            errs = sum(1 for o in outs if str(o.get('status')).startswith('err') or o.get('status') not in (200,))

            results[label] = {
                'addresses_checked': len(cohort),
                'active_addresses_btc': actives_btc,
                'total_fills_btc': total_btc,
                'active_addresses_anycoin': actives_any,
                'total_fills_anycoin': total_any,
                'errors': errs,
                'window_start_iso': to_iso(start_ms),
                'window_end_iso': to_iso(end_ms),
            }

    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
