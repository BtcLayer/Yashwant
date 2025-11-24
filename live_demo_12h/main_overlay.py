"""
Modified main.py with Overlay System Integration

This version integrates the unified overlay system to replace
the separate bot architecture with a single multi-timeframe system.
"""

import asyncio
import json
import os
from typing import Dict
import importlib
from datetime import datetime, timezone, timedelta
from collections import deque
import aiohttp
import gspread
import pandas as pd

from live_demo.market_data import MarketData
from live_demo.hyperliquid_listener import HyperliquidListener
from live_demo.funding_hl import FundingHL
from live_demo.cohort_signals import CohortState
from live_demo.features import FeatureBuilder, LiveFeatureComputer
from live_demo.model_runtime import ModelRuntime
from live_demo.decision import Thresholds, decide, gate_and_score
from live_demo.risk_and_exec import RiskConfig, RiskAndExec
from live_demo.sheets_logger import SheetsLogger
from live_demo.state import JSONState
from ops.log_emitter import get_emitter
from live_demo.ops.log_router import LogRouter
from live_demo.health_monitor import HealthMonitor
from live_demo.repro_tracker import ReproTracker
from live_demo.execution_tracker import ExecutionTracker
from live_demo.pnl_attribution import PnLAttributionTracker
from live_demo.order_intent_tracker import OrderIntentTracker
from live_demo.feature_logger import FeatureLogger
from live_demo.calibration_enhancer import CalibrationEnhancer

# Import overlay system components
from live_demo.unified_overlay_system import UnifiedOverlaySystem, OverlaySystemConfig
from live_demo.overlay_manager import BarData


def load_config(path: str) -> Dict:
    with open(path, 'r', encoding='utf-8') as fp:
        return json.load(fp)


async def run_live_with_overlay(config_path: str, dry_run: bool = False):
    """
    Main function with overlay system integration.
    This replaces the separate bot architecture with a unified overlay system.
    """
    cfg = load_config(config_path)
    sym = cfg['data']['symbol']
    interval = cfg['data']['interval']
    warmup_bars = int(cfg['data'].get('warmup_bars', 1000))
    one_shot = bool(cfg.get('execution', {}).get('one_shot', False) or os.environ.get('LIVE_DEMO_ONE_SHOT'))
    force_validation = bool(cfg.get('execution', {}).get('force_validation_trade', False))
    
    # Project root and path helper
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    def abspath(p: str):
        return p if (p and os.path.isabs(p)) else (os.path.join(project_root, p) if p else None)

    # Initialize overlay system configuration
    # Resolve absolute manifest path for reliability regardless of CWD
    manifest_rel_for_overlay = cfg.get('artifacts', {}).get('latest_manifest', 'live_demo/models/LATEST.json')
    overlay_config = OverlaySystemConfig(
        enable_overlays=cfg.get('overlay', {}).get('enabled', True),
        base_timeframe=interval,
        overlay_timeframes=cfg.get('overlay', {}).get('timeframes', ["15m", "1h"]),
        rollup_windows=cfg.get('overlay', {}).get('rollup_windows', {"15m": 3, "1h": 12}),
        timeframe_weights=cfg.get('overlay', {}).get('weights', {"5m": 0.5, "15m": 0.3, "1h": 0.2}),
        model_manifest_path=abspath(manifest_rel_for_overlay)
    )
    
    # Output root helper: unify under PAPER_TRADING_ROOT if set; else MetaStacker/paper_trading_outputs
    def paper_root() -> str:
        env = os.environ.get('PAPER_TRADING_ROOT')
        if env:
            return os.path.abspath(env)
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'paper_trading_outputs'))

    # Initialize unified overlay system
    overlay_system = UnifiedOverlaySystem(overlay_config)

    # Binance client setup (same as original)
    ex_active = cfg['exchanges'].get('active', 'testnet')
    if ex_active == 'mainnet':
        ex_cfg = cfg['exchanges'].get('binance_mainnet', {})
    else:
        ex_cfg = cfg['exchanges'].get('binance_testnet', {})
    api_key = ex_cfg.get('api_key', '')
    api_secret = ex_cfg.get('api_secret', '')
    base_url = ex_cfg.get('base_url', 'https://testnet.binancefuture.com')
    
    try:
        mod = importlib.import_module('binance.um_futures')
        UMFutures = getattr(mod, 'UMFutures')
        client = UMFutures(key=api_key, secret=api_secret, base_url=base_url)
    except ImportError:
        try:
            from binance.client import Client as PBClient
        except ImportError as e:
            raise ImportError("Neither binance-connector nor python-binance is available") from e

        class UMFuturesAdapter:
            def __init__(self, pb_client: PBClient):
                self._c = pb_client
            def klines(self, symbol: str, interval: str, limit: int = 1000):
                return self._c.futures_klines(symbol=symbol, interval=interval, limit=limit)
            def new_order(self, **kwargs):
                return self._c.futures_create_order(**kwargs)

        pb_client = PBClient(
            api_key,
            api_secret,
            testnet=(ex_active != 'mainnet'),
            requests_params={'timeout': (10, 30)}
        )
        client = UMFuturesAdapter(pb_client)
    
    md = MarketData(client, sym, interval)

    # Warmup (same as original)
    try:
        kl = md.get_klines(limit=warmup_bars)
    except Exception:
        try:
            import pandas as pd
            local_ohlc = abspath('ohlc_btc_5m.csv')
            if os.path.exists(local_ohlc):
                kl = pd.read_csv(local_ohlc, index_col=0)
                print(f"[Warmup] Loaded {len(kl)} bars from local CSV")
            else:
                raise
        except Exception:
            print("[Warmup] Failed to load klines, continuing with empty history")
            kl = None

    # Initialize components (same as original)
    # Hyperliquid funding and WS endpoints
    hl_base = cfg['exchanges']['hyperliquid']['base_url']
    hl_ws = cfg['exchanges']['hyperliquid']['ws_url']
    hl_f_cfg = cfg['exchanges']['hyperliquid'].get('funding', {})
    funding_client = FundingHL(
        rest_url=hl_base,
        coin='BTC',
        path=hl_f_cfg.get('path', '/v1/funding'),
        key_time=hl_f_cfg.get('key_time', 'time'),
        key_rate=hl_f_cfg.get('key_rate', 'funding'),
        mode=hl_f_cfg.get('mode', 'settled'),
        epoch_hours=int(hl_f_cfg.get('epoch_hours', 8)),
        ttl_seconds=int(hl_f_cfg.get('ttl_seconds', 600)),
        binance_client=client,
        binance_symbol=sym,
        request_timeout_s=float(hl_f_cfg.get('request_timeout_s', 15.0)),
        retries=int(hl_f_cfg.get('retries', 2)),
        retry_backoff_s=float(hl_f_cfg.get('retry_backoff_s', 0.75)),
    )
    cohort = CohortState(window=int(cfg['cohorts'].get('window', 12)))
    
    # Load cohort addresses
    top_file = abspath(cfg['cohorts']['top_file'])
    bottom_file = abspath(cfg['cohorts']['bottom_file'])
    top_set = set()
    bottom_set = set()
    try:
        if top_file and os.path.exists(top_file):
            df_top = pd.read_csv(top_file)
        else:
            # Fallback to assets dir
            assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
            df_top = pd.read_csv(os.path.join(assets_dir, os.path.basename(top_file)))
        col = 'Account' if 'Account' in df_top.columns else ('address' if 'address' in df_top.columns else None)
        if col:
            top_set = set(df_top[col].dropna().astype(str).str.lower().tolist())
    except Exception:
        top_set = set()
    try:
        if bottom_file and os.path.exists(bottom_file):
            df_bot = pd.read_csv(bottom_file)
        else:
            assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
            df_bot = pd.read_csv(os.path.join(assets_dir, os.path.basename(bottom_file)))
        colb = 'Account' if 'Account' in df_bot.columns else ('address' if 'address' in df_bot.columns else None)
        if colb:
            bottom_set = set(df_bot[colb].dropna().astype(str).str.lower().tolist())
    except Exception:
        bottom_set = set()
    
    # Initialize feature builder and computer
    # Initialize feature builder and computer (schema from model runtime)
    manifest_rel = cfg['artifacts']['latest_manifest']
    manifest_abs = abspath(manifest_rel)
    mr = ModelRuntime(manifest_abs)
    fb = FeatureBuilder(mr.feature_schema_path)
    lf = LiveFeatureComputer(fb.columns, timeframe=interval)
    
    # Initialize overlay system with base feature computer
    overlay_system.initialize(lf)
    
    # Initialize other components (same as original)
    creds_path = abspath(cfg['sheets']['creds_json'])
    sheet_id = cfg['sheets']['sheet_id']
    headers = ['ts_ist', 'ts', 'address', 'coin', 'side', 'price', 'size']
    logger = SheetsLogger(creds_path, sheet_id, headers=headers)
    # Log router (per-topic sink fan-out, matches main.py behavior)
    log_router = LogRouter(cfg.get('logging', {}))
    
    # Initialize tracking systems
    health_monitor = HealthMonitor()
    repro_tracker = ReproTracker()
    execution_tracker = ExecutionTracker()
    pnl_attribution = PnLAttributionTracker()
    order_intent_tracker = OrderIntentTracker()
    feature_logger = FeatureLogger()
    calibration_enhancer = CalibrationEnhancer()

    # Thresholds and risk (same as original)
    th_cfg = cfg['thresholds']
    th = Thresholds(**th_cfg)
    
    _interval_to_minutes = {
        '1m': 1.0, '3m': 3.0, '5m': 5.0, '15m': 15.0, '30m': 30.0,
        '1h': 60.0, '2h': 120.0, '4h': 240.0, '12h': 720.0, '1d': 1440.0
    }
    bar_minutes = _interval_to_minutes.get(interval, 5.0)
    
    risk_cfg_dict = dict(cfg['risk'])
    risk_cfg_dict['bar_minutes'] = bar_minutes
    risk_cfg = RiskConfig(**risk_cfg_dict)
    starting_equity = float(cfg.get('paper', {}).get('starting_equity', 10000.0))
    risk = RiskAndExec(client, sym, risk_cfg)
    
    # Seed ADV20 USD
    try:
        last_warm_close = float(kl['close'].iloc[-1])
        adv20 = cfg['cohorts'].get('adv_window_days', 20)
        risk.adv20_usd = float(last_warm_close * float(adv20))
    except Exception:
        risk.adv20_usd = 0.0

    # Initialize variables
    last_close = None
    last_ts = None
    bar_count = 0
    equity = None
    
    # Health tracking
    from collections import deque as _deque
    _health_pred_window = int(cfg.get('execution', {}).get('health_pred_window', 60))
    _health_emit_every = int(cfg.get('execution', {}).get('health_emit_every_bars', 60))
    _health_preds = _deque(maxlen=_health_pred_window)
    _health_smodels = _deque(maxlen=_health_pred_window)
    _health_exec_count = 0
    
    # Dedup set for user fill trade IDs
    seen_user_fill_ids = set()
    
    # Daily risk controls
    session_peak_equity = starting_equity
    stopped_for_day = False

    def to_iso(ts_val):
        try:
            t = float(ts_val)
        except (TypeError, ValueError):
            return ''
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        if t > 1e12:
            dt = datetime.fromtimestamp(t/1000.0, tz=timezone.utc).astimezone(tz_ist)
        elif t > 1e9:
            dt = datetime.fromtimestamp(t, tz=timezone.utc).astimezone(tz_ist)
        else:
            return ''
        return dt.isoformat()

    # Bandit integration (same as original)
    bandit_cfg = cfg.get('execution', {}).get('bandit', {})
    bandit = None
    bandit_io = None
    if bandit_cfg and bool(bandit_cfg.get('enabled', False)):
        state_rel = bandit_cfg.get('state_path', os.path.join('paper_trading_outputs', 'runtime_bandit.json'))
        bandit_state_path = state_rel if os.path.isabs(state_rel) else os.path.join(paper_root(), os.path.basename(state_rel))
        try:
            from live_demo.bandit import BanditStateIO
            bandit_io = BanditStateIO(path=bandit_state_path)
            bandit = bandit_io.load(n_arms=4)
        except (ImportError, OSError, ValueError, TypeError) as e:
            raise RuntimeError(f"Failed to initialize bandit: {e}") from e

    # Track last decision for reward update
    last_exec_pos: float = 0.0
    last_close_value: float = None
    last_chosen_arm: str | None = None

    # Hyperliquid WebSocket setup (same as original)
    fill_queue = deque(maxlen=20000)
    
    async def _consume_ws(hl: HyperliquidListener):
        try:
            async for fmsg in hl.stream():
                try:
                    if len(fill_queue) == fill_queue.maxlen:
                        # drop oldest implicitly
                        pass
                except Exception:
                    pass
                fill_queue.append(fmsg)
        except (aiohttp.ClientError, asyncio.CancelledError):
            pass

    # Helper functions (same as original)
    async def _fallback_public_mood_binance(ts_end_ms: int, interval_ms: int) -> float:
        start_ms = int(ts_end_ms - interval_ms)
        url = 'https://fapi.binance.com/fapi/v1/aggTrades'
        params = {
            'symbol': sym,
            'startTime': start_ms,
            'endTime': ts_end_ms,
            'limit': 1000,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        net = sum(float(t['qty']) if t['m'] else -float(t['qty']) for t in data)
                        return net
        except Exception:
            pass
        return 0.0

    async def _poll_user_fills_by_time(ts_end_ms: int, interval_ms: int):
        # Poll userFillsByTime for cohort addresses and return processed fill dicts for BTC
        url = hl_base  # e.g., https://api.hyperliquid.xyz/info
        # Use a wider window (2x interval) to avoid boundary misses
        start_ms = max(0, int(ts_end_ms - (2 * interval_ms)))
        addresses_to_query = list(top_set.union(bottom_set))
        if not addresses_to_query:
            return []
        results = []
        sem = asyncio.Semaphore(8)

        async def fetch_for_addr(session: aiohttp.ClientSession, addr: str):
            payload = {
                "type": "userFillsByTime",
                "user": addr,
                "startTime": start_ms,
                "endTime": ts_end_ms,
            }
            async with sem:
                try:
                    async with session.post(url, json=payload, timeout=10) as resp:
                        if resp.status != 200:
                            return
                        data = await resp.json()
                        if not isinstance(data, list):
                            return
                        for f in data:
                            try:
                                if str(f.get('coin', '')).upper() != 'BTC':
                                    continue
                                tsf = int(f.get('time'))
                                px = float(f.get('px'))
                                sz = float(f.get('sz'))
                                side_raw = str(f.get('side') or '').upper()
                                side = 'buy' if side_raw in ('A', 'BUY', 'BID') else 'sell'
                                tid = str(f.get('tid') or f.get('hash') or f"{tsf}:{px}:{sz}")
                                uid = f"{addr}:{tid}"
                                # dedupe within this poll batch via a local set is optional; rely on outer loop set
                                results.append({
                                    'ts': tsf,
                                    'address': addr,
                                    'coin': 'BTC',
                                    'side': side,
                                    'price': px,
                                    'size': sz,
                                    'source': 'user',
                                })
                            except (ValueError, TypeError):
                                continue
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    return

        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*(fetch_for_addr(session, a) for a in addresses_to_query))
        # Best-effort local debug of poll summary
        try:
            dbg_path = os.path.join(paper_root(), 'user_fills_poll_debug.csv')
            os.makedirs(os.path.dirname(dbg_path), exist_ok=True)
            if not os.path.exists(dbg_path):
                with open(dbg_path, 'w', encoding='utf-8') as fh:
                    fh.write('ts_iso,ts,window_ms,addresses,results_count\n')
            with open(dbg_path, 'a', encoding='utf-8') as fh:
                fh.write(f"{to_iso(ts_end_ms)},{ts_end_ms},{2*interval_ms},{len(addresses_to_query)},{len(results)}\n")
        except OSError:
            pass
        return results

    # Start background consumer task
    # Start WS consumer inside async context
    _consumer_task = None
    ws_context = HyperliquidListener(hl_ws, addresses=list(top_set.union(bottom_set)), coin='BTC', mode='public_trades')
    hl_cm = ws_context
    await hl_cm.__aenter__()
    _consumer_task = asyncio.create_task(_consume_ws(hl_cm))

    print(f"[Overlay System] Starting unified overlay system for {sym}")
    print(f"[Overlay System] Timeframes: {overlay_config.overlay_timeframes}")
    print(f"[Overlay System] Rollup windows: {overlay_config.rollup_windows}")
    print(f"[Overlay System] Timeframe weights: {overlay_config.timeframe_weights}")

    # Main trading loop with overlay system
    while True:
        try:
            # 1) Poll last closed kline
            row = md.poll_last_closed_kline()
        except Exception as e:
            try:
                err_log_path = os.path.join(paper_root(), 'live_errors.log')
                os.makedirs(os.path.dirname(err_log_path), exist_ok=True)
                with open(err_log_path, 'a', encoding='utf-8') as err_log_fh:
                    err_log_fh.write('\n=== poll_last_closed_kline error ===\n')
                    err_log_fh.write('Type: ' + type(e).__name__ + '\n')
                    err_log_fh.write('Message: ' + str(e) + '\n')
            except OSError:
                pass
            await asyncio.sleep(2)
            continue
            
        if row is None:
            await asyncio.sleep(2)
            continue
            
        ts, o, h, l, c, v = row
        if last_ts is not None and ts <= last_ts:
            await asyncio.sleep(1)
            continue

        # Update returns and last_close
        if last_close is not None:
            risk.update_returns(last_close, c)
        last_close = c
        last_ts = ts

        # 2) Ingest HL fills (same as original)
        drained_fills = []
        max_drains = 5000
        public_count = 0
        while fill_queue and max_drains > 0:
            fill = fill_queue.popleft()
            src = str(fill.get('source') or '')
            if src == 'user':
                addr = str(fill.get('address') or '').lower()
                if addr and (addr in top_set or addr in bottom_set):
                    if addr in top_set:
                        w = {'pros': 1.0, 'amateurs': 0.0, 'mood': 1.0}
                    elif addr in bottom_set:
                        w = {'pros': 0.0, 'amateurs': 1.0, 'mood': 1.0}
                    else:
                        w = {'pros': 0.0, 'amateurs': 0.0, 'mood': 1.0}
                    cohort.update_from_fill(fill, weights=w)
                    drained_fills.append(fill)
            elif src == 'public' and str(fill.get('coin') or '').upper() == 'BTC':
                cohort.update_from_fill(fill, weights={'pros': 0.0, 'amateurs': 0.0, 'mood': 1.0})
                public_count += 1
            max_drains -= 1

        # Fallback mood from Binance
        if public_count == 0:
            interval_map = {
                '1m': 60_000, '3m': 180_000, '5m': 300_000, '15m': 900_000, '30m': 1_800_000,
                '1h': 3_600_000, '2h': 7_200_000, '4h': 14_400_000, '12h': 43_200_000, '1d': 86_400_000
            }
            interval_ms = interval_map.get(interval, 300_000)
            net = await _fallback_public_mood_binance(ts, interval_ms)
            if abs(net) > 0:
                synthetic = {
                    'ts': ts,
                    'address': '',
                    'coin': 'BTC',
                    'side': 'buy' if net > 0 else 'sell',
                    'price': c,
                    'size': abs(net),
                    'source': 'public',
                }
                cohort.update_from_fill(synthetic, weights={'pros': 0.0, 'amateurs': 0.0, 'mood': 1.0})

        # Poll user fills by time
        interval_map = {
            '1m': 60_000, '3m': 180_000, '5m': 300_000, '15m': 900_000, '30m': 1_800_000,
            '1h': 3_600_000, '2h': 7_200_000, '4h': 14_400_000, '12h': 43_200_000, '1d': 86_400_000
        }
        interval_ms = interval_map.get(interval, 300_000)
        polled_user_fills = await _poll_user_fills_by_time(ts, interval_ms)
        for uf in polled_user_fills:
            addr = str(uf.get('address') or '').lower()
            if addr and (addr in top_set or addr in bottom_set):
                if addr in top_set:
                    w = {'pros': 1.0, 'amateurs': 0.0, 'mood': 1.0}
                elif addr in bottom_set:
                    w = {'pros': 0.0, 'amateurs': 1.0, 'mood': 1.0}
                else:
                    w = {'pros': 0.0, 'amateurs': 0.0, 'mood': 1.0}
                cohort.update_from_fill(uf, weights=w)
                drained_fills.append(uf)

        # Log drained fills to Sheets
        for fill_row in drained_fills:
            logger.buffer(
                tab=cfg['sheets']['tabs']['hyperliquid'],
                row=[to_iso(fill_row.get('ts')), fill_row.get('ts'), fill_row.get('address'), 
                     fill_row.get('coin'), fill_row.get('side'), fill_row.get('price'), fill_row.get('size')]
            )

        # 3) Funding
        fnd = await funding_client.fetch_latest()
        funding_rate = float(fnd['funding']) if fnd else 0.0
        funding_stale = bool(fnd.get('stale')) if isinstance(fnd, dict) else False

        # 4) Add market data to overlay system
        bar_data = {
            'timestamp': datetime.fromtimestamp(ts/1000.0, tz=timezone.utc).isoformat(),
            'bar_id': bar_count,
            'open': o,
            'high': h,
            'low': l,
            'close': c,
            'volume': v,
            'funding': funding_rate,
            'spread_bps': 0.0,  # Could be calculated from order book
            'rv_1h': 0.0  # Could be calculated from recent bars
        }
        
        overlay_bars = overlay_system.add_market_data(bar_data)

        # 5) Generate overlay decision
        cohort_signals = cohort.snapshot()
        overlay_decision = overlay_system.generate_decision(cohort_signals, bar_count)
        
        # Extract decision components
        direction = overlay_decision.direction
        alpha = overlay_decision.alpha
        confidence = overlay_decision.confidence
        
        # Log overlay decision details
        try:
            log_router.emit_ensemble(
                ts=ts,
                asset=sym,
                raw_preds={
                    'overlay_direction': direction,
                    'overlay_alpha': alpha,
                    'overlay_confidence': confidence,
                    'chosen_timeframes': overlay_decision.chosen_timeframes,
                    'alignment_rule': overlay_decision.alignment_rule
                },
                meta={'overlay_system': True, 'manifest': manifest_rel}
            )
        except Exception:
            pass

        # 6) Risk management and execution (same as original)
        if not stopped_for_day:
            target_pos = risk.target_position(direction, alpha)
            
            if abs(target_pos - last_exec_pos) > risk_cfg.rebalance_min_pos_delta:
                exec_result = risk.mirror_to_exchange(target_pos, c, dry_run=dry_run)
                
                if exec_result:
                    last_exec_pos = target_pos
                    # Update bandit rewards if enabled
                    if bandit and last_chosen_arm:
                        # Calculate reward based on price movement
                        if last_close_value is not None:
                            price_change = (c - last_close_value) / last_close_value
                            reward = price_change * direction  # Reward if direction was correct
                            bandit.update(last_chosen_arm, reward)
                    
                    last_close_value = c
                    last_chosen_arm = overlay_decision.alignment_rule  # Use alignment rule as arm

        # 7) Logging and monitoring (same as original)
        try:
            # Log overlay system status
            system_status = overlay_system.get_system_status()
            performance_stats = overlay_system.get_performance_stats()
            
            # Log to sheets
            logger.buffer(
                tab=cfg['sheets']['tabs']['signals'],
                row=[to_iso(ts), sym, bar_count, direction, alpha, confidence, 
                     overlay_decision.alignment_rule, str(overlay_decision.chosen_timeframes)]
            )
            
        except Exception as e:
            print(f"[Overlay System] Logging error: {e}")

        # 8) Health monitoring (same as original)
        if bar_count % _health_emit_every == 0:
            try:
                health_metrics = health_monitor.get_health_metrics()
                # Route health via router to match unified logging behavior
                log_router.emit_health(ts=ts, asset=sym, health=health_metrics)
            except Exception:
                pass

        bar_count += 1
        
        # Check for daily stop
        if not stopped_for_day:
            current_equity = starting_equity + (risk.pnl_total or 0.0)
            if current_equity > session_peak_equity:
                session_peak_equity = current_equity
            
            drawdown = (current_equity - session_peak_equity) / session_peak_equity
            if drawdown <= -risk_cfg.daily_stop_dd_pct / 100.0:
                stopped_for_day = True
                print(f"[Daily Stop] Stopped for day due to drawdown: {drawdown:.2%}")

        # Sleep until next bar
        await asyncio.sleep(1)

    # Cleanup WS
    try:
        if _consumer_task:
            _consumer_task.cancel()
            try:
                await _consumer_task
            except asyncio.CancelledError:
                pass
    finally:
        try:
            await hl_cm.__aexit__(None, None, None)
        except Exception:
            pass


# Keep original function for backward compatibility
async def run_live(config_path: str, dry_run: bool = False):
    """Original run_live function - now calls overlay version"""
    return await run_live_with_overlay(config_path, dry_run)


if __name__ == '__main__':
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'live_demo/config.json'
    dry_run = '--dry-run' in sys.argv
    asyncio.run(run_live_with_overlay(config_path, dry_run))
