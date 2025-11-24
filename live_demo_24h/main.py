import asyncio
import json
import os
from typing import Dict
import importlib
from datetime import datetime, timezone, timedelta
from collections import deque
import aiohttp
import gspread

from live_demo_24h.market_data import MarketData
from live_demo_24h.hyperliquid_listener import HyperliquidListener
from live_demo_24h.funding_hl import FundingHL
from live_demo_24h.cohort_signals import CohortState
from live_demo_24h.features import FeatureBuilder, LiveFeatureComputer
from live_demo_24h.model_runtime import ModelRuntime
from live_demo_24h.decision import Thresholds, decide, gate_and_score
from live_demo_24h.risk_and_exec import RiskConfig, RiskAndExec
from live_demo_24h.sheets_logger import SheetsLogger
from live_demo_24h.state import JSONState
from ops.log_emitter import get_emitter
from live_demo_24h.health_monitor import HealthMonitor
from live_demo_24h.repro_tracker import ReproTracker
from live_demo_24h.execution_tracker import ExecutionTracker
from live_demo_24h.pnl_attribution import PnLAttributionTracker
from live_demo_24h.order_intent_tracker import OrderIntentTracker
from live_demo_24h.feature_logger import FeatureLogger
from live_demo_24h.calibration_enhancer import CalibrationEnhancer
from live_demo_24h.unified_overlay_system import UnifiedOverlaySystem, OverlaySystemConfig
from live_demo_24h.alerts.alert_router import get_alert_router
from ops.llm_logging import write_jsonl
from live_demo_24h.ops.log_router import LogRouter
from live_demo_24h.ops.bma import bma_weights, rolling_ic, series_vol


def _deep_merge(base: Dict, override: Dict) -> Dict:
    out = dict(base or {})
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str) -> Dict:
    """Load primary config and merge overlay + local overrides.

    Precedence (later wins): primary -> overlay (selected keys) -> local env.
    """
    with open(path, 'r', encoding='utf-8') as fp:
        cfg = json.load(fp)
    try:
        base_dir = os.path.dirname(path)
        overlay_path = os.path.join(base_dir, 'config_overlay.json')
        if os.path.exists(overlay_path):
            with open(overlay_path, 'r', encoding='utf-8') as fov:
                ov = json.load(fov)
            pick = {k: ov.get(k) for k in ['alignment', 'overlay', 'logging'] if k in ov}
            cfg = _deep_merge(cfg, {k: v for k, v in pick.items() if v is not None})
    except Exception:
        pass
    try:
        local_override = os.path.join(base_dir, 'config', 'config.local.json')
        if os.path.exists(local_override):
            with open(local_override, 'r', encoding='utf-8') as flo:
                loc = json.load(flo)
            cfg = _deep_merge(cfg, loc)
    except Exception:
        pass
    return cfg


async def run_live(config_path: str, dry_run: bool = False):
    cfg = load_config(config_path)
    sym = cfg['data']['symbol']
    interval = cfg['data']['interval']
    warmup_bars = int(cfg['data'].get('warmup_bars', 1000))
    one_shot = bool(cfg.get('execution', {}).get('one_shot', False) or os.environ.get('LIVE_DEMO_ONE_SHOT'))
    offline = bool(os.environ.get('LIVE_DEMO_OFFLINE')) or bool(cfg.get('execution', {}).get('offline', False))
    force_validation = bool(cfg.get('execution', {}).get('force_validation_trade', False))
    try:
        if not os.environ.get('PAPER_TRADING_ROOT'):
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
            tf_root = os.path.join(repo_root, 'paper_trading_outputs', '24h')
            os.makedirs(tf_root, exist_ok=True)
            try:
                os.makedirs(os.path.join(tf_root, 'logs'), exist_ok=True)
                os.makedirs(os.path.join(tf_root, 'sheets_fallback'), exist_ok=True)
            except Exception:
                pass
            os.environ['PAPER_TRADING_ROOT'] = tf_root
    except Exception:
        pass
    # Project root and path helper
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    def abspath(p: str):
        return (
            p
            if (p and os.path.isabs(p))
            else (os.path.join(project_root, p) if p else None)
        )

    # Exchange client: support Binance (testnet/mainnet) or Hyperliquid
    # Select exchange environment for data. We always respect dry_run for execution.
    ex_active = cfg["exchanges"].get("active", "testnet")
    
    if ex_active == "hyperliquid":
        # Use Hyperliquid for market data
        hl_base = cfg["exchanges"]["hyperliquid"]["base_url"]
        
        class HyperliquidClientAdapter:
            """Adapter to make Hyperliquid API compatible with MarketData interface"""
            def __init__(self, base_url: str, symbol: str):
                self.base_url = base_url
                self.symbol = symbol
                # Map interval to Hyperliquid format
                self.interval_map = {
                    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                    "1h": "1h", "4h": "4h", "12h": "12h", "1d": "1d"
                }
            
            def klines(self, symbol: str, interval: str, limit: int = 1000):
                """Get candles from Hyperliquid API"""
                import requests
                import time
                from datetime import datetime, timezone
                
                # Map interval
                hl_interval = self.interval_map.get(interval, interval)
                
                # Hyperliquid uses coin name (BTC) not symbol (BTCUSDT)
                coin = symbol.replace("USDT", "").replace("USD", "")
                
                # Calculate start time (limit * interval in seconds)
                interval_seconds = {
                    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
                    "1h": 3600, "4h": 14400, "12h": 43200, "1d": 86400
                }
                seconds_per_candle = interval_seconds.get(hl_interval, 300)
                end_time = int(time.time() * 1000)
                start_time = end_time - (limit * seconds_per_candle * 1000)
                
                # Hyperliquid API endpoint for candles
                # Hyperliquid uses POST to base_url with type-based requests
                # Requires startTime and endTime (epoch milliseconds), not n
                url = self.base_url  # e.g., https://api.hyperliquid.xyz/info
                payload = {
                    "type": "candleSnapshot",
                    "req": {
                        "coin": coin,
                        "interval": hl_interval,
                        "startTime": start_time,
                        "endTime": end_time
                    }
                }
                
                try:
                    response = requests.post(url, json=payload, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    
                    if not data:
                        raise ValueError("Invalid Hyperliquid API response")
                    
                    # Hyperliquid returns array directly: [{"t": start_ms, "T": end_ms, "s": "BTC", "i": "5m", "o": open, "c": close, "h": high, "l": low, "v": volume, "n": count}, ...]
                    if isinstance(data, list):
                        candles = data
                    elif isinstance(data, dict):
                        candles = data.get("data", [])
                    else:
                        raise ValueError("Unexpected Hyperliquid response format")
                    
                    if not candles:
                        raise ValueError("No candle data in response")
                    # Convert to Binance-like format: [timestamp, open, high, low, close, volume, ...]
                    result = []
                    for candle in candles:
                        # Hyperliquid uses: t (start time), T (end time), o (open), c (close), h (high), l (low), v (volume)
                        result.append([
                            int(candle["t"]),  # timestamp (start time)
                            float(candle["o"]),  # open
                            float(candle["h"]),  # high
                            float(candle["l"]),  # low
                            float(candle["c"]),  # close
                            float(candle.get("v", 0)),  # volume
                            int(candle["T"]),  # close time (end time)
                        ])
                    return result
                except Exception as e:
                    raise RuntimeError(f"Hyperliquid API error: {e}") from e
            
            def new_order(self, **kwargs):
                # Placeholder for order execution (not used in dry_run mode)
                return {"status": "dry_run"}
        
        client = HyperliquidClientAdapter(hl_base, sym)
        pb_client = None
    else:
        # Use Binance (testnet or mainnet)
        if ex_active == "mainnet":
            ex_cfg = cfg["exchanges"].get("binance_mainnet", {})
        else:
            ex_cfg = cfg["exchanges"].get("binance_testnet", {})
        api_key = ex_cfg.get("api_key", "")
        api_secret = ex_cfg.get("api_secret", "")
        base_url = ex_cfg.get("base_url", "https://testnet.binancefuture.com")
        pb_client = None
        try:
            # Preferred: binance-connector
            mod = importlib.import_module("binance.um_futures")
            UMFutures = getattr(mod, "UMFutures")
            client = UMFutures(key=api_key, secret=api_secret, base_url=base_url)
        except ImportError:
            # Fallback: python-binance with a light adapter
            try:
                from binance.client import Client as PBClient  # python-binance
            except ImportError as e:
                raise ImportError(
                    "Neither binance-connector (binance.um_futures) nor python-binance is available"
                ) from e

            class UMFuturesAdapter:
                def __init__(self, pb_client: PBClient):
                    self._c = pb_client

                def klines(self, symbol: str, interval: str, limit: int = 1000):
                    return self._c.futures_klines(
                        symbol=symbol, interval=interval, limit=limit
                    )

                def new_order(self, **kwargs):
                    # Map to python-binance futures create order
                    # Expected keys: symbol, side, type, quantity
                    return self._c.futures_create_order(**kwargs)

            # Increase HTTP timeout to reduce ReadTimeout crashes on slow responses
            # Use higher connect/read timeouts to reduce ReadTimeouts
            # requests supports a (connect, read) timeout tuple
            pb_client = PBClient(
                api_key,
                api_secret,
                testnet=(ex_active != "mainnet"),
                requests_params={"timeout": (10, 30)},
            )
            client = UMFuturesAdapter(pb_client)
    md = MarketData(client, sym, interval)

    # Warmup
    try:
        kl = md.get_klines(limit=warmup_bars)
    except Exception:
        # Fallback: attempt to seed warmup from local CSV (if available)
        try:
            import pandas as pd  # local import to avoid hard dependency at top

            local_ohlc = abspath("ohlc_btc_1d.csv")
            if local_ohlc and os.path.exists(local_ohlc):
                df = pd.read_csv(local_ohlc)
                # Expect columns: ts,open,high,low,close,volume (or a superset)
                cols = ["ts", "open", "high", "low", "close", "volume"]
                if all(c in df.columns for c in cols):
                    kl = df[cols].tail(min(len(df), warmup_bars)).copy()
                else:
                    raise RuntimeError("Local OHLC missing required columns")
            else:
                raise RuntimeError("Local OHLC CSV not found")
        except Exception as e:
            # Re-raise original warmup failure if local fallback unavailable
            raise e
    if kl is None or len(kl) == 0:
        raise RuntimeError("No klines returned for warmup")

    # HL funding and fills
    hl_base = cfg["exchanges"]["hyperliquid"]["base_url"]
    hl_ws = cfg["exchanges"]["hyperliquid"]["ws_url"]
    hl_f_cfg = cfg["exchanges"]["hyperliquid"].get("funding", {})
    funding_client = FundingHL(
        rest_url=hl_base,
        coin="BTC",
        path=hl_f_cfg.get("path", "/v1/funding"),
        key_time=hl_f_cfg.get("key_time", "time"),
        key_rate=hl_f_cfg.get("key_rate", "funding"),
        mode=hl_f_cfg.get("mode", "settled"),
        epoch_hours=int(hl_f_cfg.get("epoch_hours", 8)),
        ttl_seconds=int(hl_f_cfg.get("ttl_seconds", 600)),
        binance_client=(client if pb_client is None else pb_client),
        binance_symbol=sym,
        request_timeout_s=float(hl_f_cfg.get("request_timeout_s", 15.0)),
        retries=int(hl_f_cfg.get("retries", 2)),
        retry_backoff_s=float(hl_f_cfg.get("retry_backoff_s", 0.75)),
    )

    # Cohort state
    cohort = CohortState(window=12)
    # ADV20 from warmup volume
    adv20 = (
        kl["volume"].tail(12 * 20).mean()
        if len(kl) >= 12 * 20
        else max(1.0, kl["volume"].mean())
    )
    cohort.set_adv20(float(adv20))

    # Load cohort addresses
    addresses = []
    top_set = set()
    bottom_set = set()
    try:
        import pandas as pd

        top_path = cfg["cohorts"]["top_file"]
        bot_path = cfg["cohorts"]["bottom_file"]
        if top_path:
            try:
                df_top = pd.read_csv(abspath(top_path))
                if "Account" in df_top.columns:
                    top_list = (
                        df_top["Account"].dropna().astype(str).str.lower().tolist()
                    )
                    top_set = set(top_list)
                    addresses.extend(top_list)
            except (FileNotFoundError, OSError, ValueError, KeyError):
                # Fallback: try live_demo/assets/<basename>
                try:
                    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
                    alt_top = os.path.join(assets_dir, os.path.basename(top_path))
                    df_top = pd.read_csv(alt_top)
                    if 'Account' in df_top.columns:
                        top_list = df_top['Account'].dropna().astype(str).str.lower().tolist()
                        top_set = set(top_list)
                        addresses.extend(top_list)
                except Exception:
                    pass
        if bot_path:
            try:
                df_bot = pd.read_csv(abspath(bot_path))
                if "Account" in df_bot.columns:
                    bot_list = (
                        df_bot["Account"].dropna().astype(str).str.lower().tolist()
                    )
                    bottom_set = set(bot_list)
                    addresses.extend(bot_list)
            except (FileNotFoundError, OSError, ValueError, KeyError):
                # Fallback: try live_demo/assets/<basename>
                try:
                    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
                    alt_bot = os.path.join(assets_dir, os.path.basename(bot_path))
                    df_bot = pd.read_csv(alt_bot)
                    if 'Account' in df_bot.columns:
                        bot_list = df_bot['Account'].dropna().astype(str).str.lower().tolist()
                        bottom_set = set(bot_list)
                        addresses.extend(bot_list)
                except Exception:
                    pass
        addresses = list(dict.fromkeys(addresses))  # dedupe preserving order
    except (ImportError, ValueError, KeyError):
        addresses = []

    # Artifacts/model
    manifest_rel = cfg["artifacts"]["latest_manifest"]
    manifest = abspath(manifest_rel)
    mr = ModelRuntime(manifest)
    fb = FeatureBuilder(mr.feature_schema_path)
    lf = LiveFeatureComputer(fb.columns, timeframe="1d")

    # Logger
    sheet_id = cfg["sheets"]["sheet_id"]
    creds_path = abspath(cfg["sheets"].get("creds_json"))
    # Sheet tab headers (optional but helpful)
    tabs = cfg["sheets"]["tabs"]
    headers = {
        tabs['hyperliquid']: ['ts_iso','ts','address','coin','side','price','size'],
        # Signals: extended to include both model arms and BMA details for full transparency
        tabs['signals']: [
            'ts_iso','ts','open','high','low','close','volume',
            'S_top','S_bot','S_mood',
            'p_down','p_neutral','p_up',
            's_model','s_model_meta','s_model_bma',
            'model_source','bma_w_base','bma_w_prob','pred_bma_bps',
            'dir','alpha','funding','funding_stale','position','exec_resp'
        ],
        tabs['mirror']: ['ts_iso','ts','dir','alpha','price','notional_usd','intended_notional','target_pos','current_pos','exch_qty_before','exch_qty_after','reconciled','exec_resp'],
        # Bandit: split model eligibility into meta and bma (4-arm: mood removed)
        tabs.get('bandit', 'bandit'): [
            'ts_iso','ts','event','chosen','raw','dir','alpha',
            'eligible_pros','eligible_amateurs','eligible_model_meta','eligible_model_bma',
            'reward','counts','means','variances'
        ],
        tabs.get('executions', 'executions_paper'): ['ts_iso','ts','side','qty','mid_price','fill_price','notional_usd','intended_notional','target_pos','paper_qty','paper_avg_px','realized_pnl','unrealized_pnl','fee','impact','equity','raw']
    }
    # Optional equity tab header if configured
    if tabs.get('equity'):
        headers[tabs['equity']] = ['ts_iso','ts','last_price','paper_qty','paper_avg_px','realized','unrealized','equity']
    # Optional overlay tab header
    if tabs.get('overlay'):
        headers[tabs['overlay']] = ['ts_iso','ts','dir','alpha','confidence','alignment_rule','chosen_timeframes','individual_signals']
    # Optional KPI tab header for scorecard
    if tabs.get('kpi'):
        headers[tabs['kpi']] = ['ts_iso','ts','sharpe_1w','max_dd_pct','turnover_bps_day','in_band_share','gate_sharpe','gate_dd','gate_cost','gate_turnover','summary']
    # Optional health metrics tab header
    if tabs.get('health'):
        headers[tabs['health']] = [
            'ts_iso','ts','recent_bars','mean_p_down','mean_p_up','mean_s_model','exec_count_recent','funding_stale','equity',
            'ws_queue_drops','ws_reconnects','ws_staleness_ms',
            'Sharpe_roll_1d','Sharpe_roll_1w','Sortino_1w','max_dd_to_date','time_in_mkt','hit_rate_w','turnover_bps_day',
            'capacity_participation','ic_drift','calibration_drift','leakage_flag','same_bar_roundtrip_flag','in_band_share'
        ]
    # Optional alerts tab header
    if tabs.get('alerts'):
        headers[tabs['alerts']] = ['ts_iso','ts','type','staleness_ms','reconnects','queue_drops','payload_json']
    # Determine per-timeframe root
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    tf_root = os.path.join(repo_root, 'paper_trading_outputs', '24h')
    os.makedirs(tf_root, exist_ok=True)
    try:
        os.makedirs(os.path.join(tf_root, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(tf_root, 'sheets_fallback'), exist_ok=True)
    except Exception:
        pass
    logger = SheetsLogger(creds_path, sheet_id, headers=headers, root_dir=tf_root)
    # Ensure tabs and headers exist before any rows are buffered/appended (best-effort inside method)
    logger.ensure_headers()
    # Log router (per-topic sink fan-out)
    log_router = LogRouter(cfg.get('logging', {}), bot_version='24h', base_root=os.path.join(tf_root, 'logs'))
    # Initialize unified emitter once for this run (used in multiple places)
    try:
        emitter = get_emitter('24h', base_dir=os.path.join(tf_root, 'logs'))
    except Exception:
        emitter = None

    # Output root helper: prefer PAPER_TRADING_ROOT when it is a subfolder of the repo paper_trading_outputs
    def paper_root() -> str:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        repo_paper = os.path.abspath(os.path.join(repo_root, 'paper_trading_outputs'))
        env = os.environ.get('PAPER_TRADING_ROOT')
        if env:
            try:
                env_abs = os.path.abspath(env)
                if os.path.commonpath([env_abs, repo_paper]) == repo_paper:
                    return env_abs
            except Exception:
                pass
        return repo_paper

    # State
    _ = JSONState(os.path.join(paper_root(), 'runtime_state.json'))
    # Initialize tracking systems
    health_monitor = HealthMonitor()
    repro_tracker = ReproTracker()
    execution_tracker = ExecutionTracker()
    pnl_attribution = PnLAttributionTracker()
    order_intent_tracker = OrderIntentTracker()
    feature_logger = FeatureLogger()
    calibration_enhancer = CalibrationEnhancer()

    # Thresholds and risk
    th_cfg = cfg["thresholds"]
    th = Thresholds(**th_cfg)
    # Derive bar duration in minutes from interval string
    _interval_to_minutes = {
        "1m": 1.0,
        "3m": 3.0,
        "5m": 5.0,
        "15m": 15.0,
        "30m": 30.0,
        "1h": 60.0,
        "2h": 120.0,
        "4h": 240.0,
        "12h": 720.0,
        "1d": 1440.0,
    }
    bar_minutes = _interval_to_minutes.get(interval, 5.0)
    # Inject bar_minutes into risk config for correct annualization/cooldown per TF
    risk_cfg_dict = dict(cfg["risk"])
    risk_cfg_dict["bar_minutes"] = bar_minutes
    risk_cfg = RiskConfig(**risk_cfg_dict)
    starting_equity = float(cfg.get("paper", {}).get("starting_equity", 10000.0))
    risk = RiskAndExec(client, sym, risk_cfg)
    # Seed ADV20 USD for ADV cap logic using last warmup close
    try:
        last_warm_close = float(kl["close"].iloc[-1])
        risk.adv20_usd = float(last_warm_close * float(adv20))
    except Exception:
        risk.adv20_usd = 0.0

    last_close = None
    last_ts = None
    bar_count = 0

    equity = None
    # Health tracking
    _health_pred_window = int(cfg.get('execution', {}).get('health_pred_window', 60))
    _health_emit_every = int(cfg.get('execution', {}).get('health_emit_every_bars', 60))
    _health_preds = deque(maxlen=_health_pred_window)
    _health_smodels = deque(maxlen=_health_pred_window)
    _health_exec_count = 0
    # Dedup set for user fill trade IDs to avoid double processing
    seen_user_fill_ids = set()
    # Basic WS backpressure visibility (counts when deque would drop oldest)
    ws_queue_drops = 0
    ws_reconnects = 0
    last_ws_msg_ts_ms = None
    # Daily risk controls
    session_peak_equity = starting_equity

    # BMA state: keep last-bar predictions (for alignment) and rolling histories
    bma_preds_hist = {
        'base': deque(maxlen=3000),
        'prob': deque(maxlen=3000),
    }
    bma_realized_hist = deque(maxlen=3000)
    prev_base_pred_bps = None
    prev_prob_pred_bps = None
    last_realized_bps_buffer = None  # realized for the last completed bar, set later in the loop
    bma_weights_state = [1.0, 0.0]  # default weights for ['base','prob']
    stopped_for_day = False

    def to_iso(ts_val):
        try:
            t = float(ts_val)
        except (TypeError, ValueError):
            return ""
        # Heuristic: ms vs s
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        if t > 1e12:
            dt = datetime.fromtimestamp(t / 1000.0, tz=timezone.utc).astimezone(tz_ist)
        elif t > 1e9:
            dt = datetime.fromtimestamp(t, tz=timezone.utc).astimezone(tz_ist)
        else:
            return ""
        # Return ISO-8601 with explicit IST offset (+05:30)
        return dt.isoformat()

    def hour_bucket(ts_val) -> int:
        try:
            t = float(ts_val)
        except (TypeError, ValueError):
            return -1
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        if t > 1e12:
            dt = datetime.fromtimestamp(t/1000.0, tz=timezone.utc).astimezone(tz_ist)
        elif t > 1e9:
            dt = datetime.fromtimestamp(t, tz=timezone.utc).astimezone(tz_ist)
        else:
            return -1
        return int(dt.hour)

    def weekday_idx(ts_val) -> int:
        try:
            t = float(ts_val)
        except (TypeError, ValueError):
            return -1
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        if t > 1e12:
            dt = datetime.fromtimestamp(t/1000.0, tz=timezone.utc).astimezone(tz_ist)
        elif t > 1e9:
            dt = datetime.fromtimestamp(t, tz=timezone.utc).astimezone(tz_ist)
        else:
            return -1
        # Monday=0, Sunday=6
        return int(dt.weekday())

    # For reliability, use public trades for logging; only user fills would require a different authenticated stream
    # Subscribe to user fills for cohort addresses; only these get logged in the Hyperliquid sheet
    # Optional bandit integration
    bandit_cfg = cfg.get("execution", {}).get("bandit", {})
    bandit = None
    bandit_io = None
    if bandit_cfg and bool(bandit_cfg.get('enabled', False)):
        # Resolve bandit state inside unified paper root
        state_rel = bandit_cfg.get('state_path', os.path.join('paper_trading_outputs', 'runtime_bandit.json'))
        bandit_state_path = state_rel if os.path.isabs(state_rel) else os.path.join(paper_root(), os.path.basename(state_rel))
        try:
            from live_demo.bandit import BanditStateIO

            bandit_io = BanditStateIO(path=bandit_state_path)
            # 4 arms: pros, amateurs, model_meta, model_bma (mood removed)
            bandit = bandit_io.load(n_arms=4)
        except (ImportError, OSError, ValueError, TypeError) as e:
            raise RuntimeError(f"Failed to initialize bandit: {e}") from e

    # Track last decision for reward update (bandit)
    last_exec_pos: float = 0.0
    last_close_value: float = None
    # Track previously selected arm for correct reward attribution
    last_chosen_arm: str | None = None
    # Track raw signal magnitude used for reward shaping
    last_chosen_raw_val: float | None = None
    # (debug CSV logging removed)

    # Helper: Binance aggTrades fallback for public mood (per-bar)
    async def _fallback_public_mood_binance(ts_end_ms: int, interval_ms: int) -> float:
        start_ms = int(ts_end_ms - interval_ms)
        url = "https://fapi.binance.com/fapi/v1/aggTrades"
        params = {
            "symbol": sym,
            "startTime": start_ms,
            "endTime": ts_end_ms,
            "limit": 1000,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=8) as resp:
                    if resp.status != 200:
                        return 0.0
                    data = await resp.json()
                    if not isinstance(data, list):
                        return 0.0
                    taker_buy = 0.0
                    taker_sell = 0.0
                    for t in data:
                        try:
                            qty = float(t.get("q") or 0.0)
                            buyer_is_maker = bool(t.get("m"))
                        except (ValueError, TypeError):
                            continue
                        # If buyer is maker, the taker is the seller => taker sell volume
                        if buyer_is_maker:
                            taker_sell += qty
                        else:
                            taker_buy += qty
                    return taker_buy - taker_sell
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return 0.0

    # Optional overlay system
    use_overlay = bool(cfg.get('execution', {}).get('use_overlay', False)) or bool(cfg.get('overlay', {}).get('enable', False))
    overlay_sys = None
    if use_overlay:
        try:
            ov_base = cfg.get('overlay', {}) or {}
            ov_cfg = OverlaySystemConfig(
                enable_overlays=bool(ov_base.get('enabled', True)),
                base_timeframe=interval,
                model_manifest_path=manifest,
                alignment_rules=cfg.get('alignment', {}),
                overlay_timeframes=ov_base.get('timeframes'),
                rollup_windows=ov_base.get('rollup_windows'),
                timeframe_weights=ov_base.get('weights'),
                signal_thresholds=ov_base.get('signal_thresholds')
            )
            overlay_sys = UnifiedOverlaySystem(ov_cfg)
            overlay_sys.initialize(lf)
        except Exception:
            overlay_sys = None

    # If offline mode is enabled, stub network-dependent components
    if offline:
        class _HLStub:
            def __init__(self, *args, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc, tb):
                return False
            async def stream(self):
                if False:
                    yield {}
        local_HL = _HLStub
        # Stub funding client
        async def _fetch_latest_stub():
            return {"funding": 0.0, "stale": True}
        try:
            funding_client.fetch_latest = _fetch_latest_stub  # type: ignore[assignment]
        except Exception:
            pass
        # Provide one last-closed bar from warmup
        try:
            last_row = kl[['ts','open','high','low','close','volume']].iloc[-1]
            offline_row = (int(last_row['ts']), float(last_row['open']), float(last_row['high']), float(last_row['low']), float(last_row['close']), float(last_row['volume']))
        except Exception:
            import time as _t
            _now_ms = int(_t.time()*1000)
            offline_row = (_now_ms, 0.0, 0.0, 0.0, 0.0, 0.0)
        _used_offline = {'done': False}
        def _offline_poll_last_closed_kline():
            if _used_offline['done']:
                return None
            _used_offline['done'] = True
            return offline_row
        try:
            md.poll_last_closed_kline = _offline_poll_last_closed_kline  # type: ignore[assignment]
        except Exception:
            pass
        async def _fallback_public_mood_binance(ts_end_ms: int, interval_ms: int) -> float:  # type: ignore[func-redecl]
            return 0.0
    else:
        local_HL = HyperliquidListener

    # Switch to public trades to drive 'mood' from market-wide flow (or stub in offline)
    async with local_HL(
        hl_ws, addresses=addresses, coin="BTC", mode="public_trades"
    ) as hl:
        used_force = False
        # Background consumer to continuously read WS messages
        fill_queue = deque(maxlen=20000)

        async def _consume_ws():
            try:
                async for fmsg in hl.stream():
                    # Count a drop if deque is full before appending (oldest will be discarded)
                    try:
                        nonlocal ws_queue_drops
                        nonlocal last_ws_msg_ts_ms
                        if len(fill_queue) == fill_queue.maxlen:
                            ws_queue_drops += 1
                    except Exception:
                        pass
                    # Update last observed WS activity time
                    try:
                        from time import time as _now
                        last_ws_msg_ts_ms = int(_now() * 1000)
                    except Exception:
                        pass
                    fill_queue.append(fmsg)
            except (aiohttp.ClientError, asyncio.CancelledError):
                # Ignore; main loop will continue and funding still works. Reconnect on outer restart.
                try:
                    nonlocal ws_reconnects
                    ws_reconnects += 1
                except Exception:
                    pass
        async def _poll_user_fills_by_time(ts_end_ms: int, interval_ms: int):
            if offline:
                return []
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
                                    if str(f.get("coin", "")).upper() != "BTC":
                                        continue
                                    tsf = int(f.get("time"))
                                    px = float(f.get("px"))
                                    sz = float(f.get("sz"))
                                    side_raw = str(f.get("side") or "").upper()
                                    side = (
                                        "buy"
                                        if side_raw in ("A", "BUY", "BID")
                                        else "sell"
                                    )
                                    tid = str(
                                        f.get("tid")
                                        or f.get("hash")
                                        or f"{tsf}:{px}:{sz}"
                                    )
                                    uid = f"{addr}:{tid}"
                                    # dedupe
                                    if uid in seen_user_fill_ids:
                                        continue
                                    seen_user_fill_ids.add(uid)
                                    results.append(
                                        {
                                            "ts": tsf,
                                            "address": addr,
                                            "coin": "BTC",
                                            "side": side,
                                            "price": px,
                                            "size": sz,
                                            "source": "user",
                                        }
                                    )
                                except (ValueError, TypeError):
                                    continue
                    except (aiohttp.ClientError, asyncio.TimeoutError):
                        return

            async with aiohttp.ClientSession() as session:
                await asyncio.gather(
                    *(fetch_for_addr(session, a) for a in addresses_to_query)
                )
            # Best-effort local debug of poll summary
            try:
                out_dir = paper_root()
                os.makedirs(out_dir, exist_ok=True)
                dbg_path = os.path.join(out_dir, "user_fills_poll_debug.csv")
                if not os.path.exists(dbg_path):
                    with open(dbg_path, "w", encoding="utf-8") as fh:
                        fh.write("ts_iso,ts,window_ms,addresses,results_count\n")
                with open(dbg_path, "a", encoding="utf-8") as fh:
                    fh.write(
                        f"{to_iso(ts_end_ms)},{ts_end_ms},{2*interval_ms},{len(addresses_to_query)},{len(results)}\n"
                    )
            except OSError:
                pass
            return results

        # Start background consumer task to process Hyperliquid public trades
        _consumer_task = asyncio.create_task(_consume_ws())

        while True:
            # 1) Poll last closed kline (resilient to transient API errors)
            try:
                row = md.poll_last_closed_kline()
            except Exception as e:
                # Log and retry without crashing the run
                try:
                    err_log_path = os.path.join(paper_root(), 'live_errors.log')
                    os.makedirs(os.path.dirname(err_log_path), exist_ok=True)
                    with open(err_log_path, "a", encoding="utf-8") as err_log_fh:
                        err_log_fh.write("\n=== poll_last_closed_kline error ===\n")
                        err_log_fh.write("Type: " + type(e).__name__ + "\n")
                        err_log_fh.write("Message: " + str(e) + "\n")
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

            # Update BMA histories with previous bar's aligned data (prev preds vs last realized)
            try:
                if last_realized_bps_buffer is not None and prev_base_pred_bps is not None and prev_prob_pred_bps is not None:
                    bma_preds_hist['base'].append(float(prev_base_pred_bps))
                    bma_preds_hist['prob'].append(float(prev_prob_pred_bps))
                    bma_realized_hist.append(float(last_realized_bps_buffer))
                    # Recompute weights from history (using config window/kappa) unless frozen
                    ens_cfg = cfg.get('ensemble', {}) or {}
                    bma_cfg = ens_cfg.get('bma', {}) or {}
                    if not bool(bma_cfg.get('freeze', False)):
                        win = int(bma_cfg.get('ic_window_bars', 200))
                        kappa = float(bma_cfg.get('kappa', 8.0))
                        ic_base = rolling_ic(bma_preds_hist['base'], bma_realized_hist, window=win)
                        ic_prob = rolling_ic(bma_preds_hist['prob'], bma_realized_hist, window=win)
                        vol_base = series_vol(bma_preds_hist['base'], window=win)
                        vol_prob = series_vol(bma_preds_hist['prob'], window=win)
                        bma_weights_state = bma_weights([ic_base, ic_prob], [vol_base, vol_prob], kappa=kappa)
            except Exception:
                pass

            # 2) Ingest HL fills seen since last bar (drain queued)
            drained_fills = []
            # Drain up to a reasonable cap to avoid blocking too long
            max_drains = 5000
            public_count = 0
            while fill_queue and max_drains > 0:
                fill = fill_queue.popleft()
                src = str(fill.get("source") or "")
                if src == "user":
                    # Only consider events for our cohort addresses
                    addr = str(fill.get("address") or "").lower()
                    if addr and (addr in top_set or addr in bottom_set):
                        # Weight pros vs amateurs based on cohort membership
                        if addr in top_set:
                            w = {"pros": 1.0, "amateurs": 0.0, "mood": 1.0}
                        elif addr in bottom_set:
                            w = {"pros": 0.0, "amateurs": 1.0, "mood": 1.0}
                        else:
                            w = {"pros": 0.0, "amateurs": 0.0, "mood": 1.0}
                        cohort.update_from_fill(fill, weights=w)
                        drained_fills.append(fill)  # keep user-fill logging to Sheets
                elif src == "public" and str(fill.get("coin") or "").upper() == "BTC":
                    # Update only 'mood' from public trades; no Sheets logging per-trade to avoid noise
                    cohort.update_from_fill(
                        fill, weights={"pros": 0.0, "amateurs": 0.0, "mood": 1.0}
                    )
                    public_count += 1
                max_drains -= 1

            # Fallback: if no public prints captured for this bar, derive mood from Binance aggTrades
            if public_count == 0:
                # ts is the close time of the last closed bar. Interval derived from config (e.g. 5m)
                # Map interval string to milliseconds
                interval_map = {
                    "1m": 60_000,
                    "3m": 180_000,
                    "5m": 300_000,
                    "15m": 900_000,
                    "30m": 1_800_000,
                    "1h": 3_600_000,
                    "2h": 7_200_000,
                    "4h": 14_400_000,
                    "12h": 43_200_000,
                    "1d": 86_400_000,
                }
                interval_ms = interval_map.get(interval, 300_000)
                net = await _fallback_public_mood_binance(ts, interval_ms)
                if abs(net) > 0:
                    synthetic = {
                        "ts": ts,
                        "address": "",
                        "coin": "BTC",
                        "side": "buy" if net > 0 else "sell",
                        "price": c,
                        "size": abs(net),
                        "source": "public",
                    }
                    cohort.update_from_fill(
                        synthetic, weights={"pros": 0.0, "amateurs": 0.0, "mood": 1.0}
                    )

            # Poll user fills by time to update pros/amateurs even when WS user fills aren't available
            interval_map = {
                "1m": 60_000,
                "3m": 180_000,
                "5m": 300_000,
                "15m": 900_000,
                "30m": 1_800_000,
                "1h": 3_600_000,
                "2h": 7_200_000,
                "4h": 14_400_000,
                "12h": 43_200_000,
                "1d": 86_400_000,
            }
            interval_ms = interval_map.get(interval, 300_000)
            polled_user_fills = await _poll_user_fills_by_time(ts, interval_ms)
            for uf in polled_user_fills:
                addr = str(uf.get("address") or "").lower()
                if addr and (addr in top_set or addr in bottom_set):
                    # Weight pros vs amateurs based on cohort membership
                    if addr in top_set:
                        w = {"pros": 1.0, "amateurs": 0.0, "mood": 1.0}
                    elif addr in bottom_set:
                        w = {"pros": 0.0, "amateurs": 1.0, "mood": 1.0}
                    else:
                        w = {"pros": 0.0, "amateurs": 0.0, "mood": 1.0}
                    cohort.update_from_fill(uf, weights=w)
                    drained_fills.append(uf)

            # Route drained fills via router (emitter/llm) and continue Sheets buffering (back-compat)
            for fill_row in drained_fills:
                try:
                    log_router.emit_hyperliquid_fill(ts=fill_row.get('ts'), asset=sym, fill=fill_row)
                except Exception:
                    pass
                try:
                    logger.buffer(
                        tab=cfg['sheets']['tabs']['hyperliquid'],
                        row=[
                            to_iso(fill_row.get('ts')),
                            fill_row.get('ts'),
                            fill_row.get('address'),
                            fill_row.get('coin'),
                            fill_row.get('side'),
                            fill_row.get('price'),
                            fill_row.get('size')
                        ]
                    )
                except Exception:
                    pass

            # 3) Funding
            fnd = await funding_client.fetch_latest()
            funding_rate = float(fnd["funding"]) if fnd else 0.0
            funding_stale = bool(fnd.get("stale")) if isinstance(fnd, dict) else False

            # 4) Build features
            bar_row = {
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
            }
            x = lf.update_and_build(bar_row, cohort.snapshot(), funding_rate)

            # 5) Model inference
            model_out = mr.infer(x)
            # Compute BMA blend across ['base','prob'] arms using current weights and honor ensemble.source
            try:
                ens_cfg = cfg.get('ensemble', {}) or {}
                enable_bma = bool(ens_cfg.get('enable_bma', False))
                source = str(ens_cfg.get('source', 'bma')).lower()
                p_up = float(model_out.get('p_up', 0.0)) if isinstance(model_out, dict) else 0.0
                p_down = float(model_out.get('p_down', 0.0)) if isinstance(model_out, dict) else 0.0
                s_model = float(model_out.get('s_model', 0.0)) if isinstance(model_out, dict) else 0.0
                base_pred_bps = 10000.0 * s_model
                prob_pred_bps = 10000.0 * (p_up - p_down)
                # Current BMA weights (from previous bar's realized alignment)
                w_base, w_prob = (bma_weights_state + [0.0, 0.0])[:2]
                pred_bma_bps = (w_base * base_pred_bps) + (w_prob * prob_pred_bps)
                # Emit ensemble with fields
                raw_preds2 = dict(model_out)
                raw_preds2['pred_bma_bps'] = float(pred_bma_bps)
                raw_preds2['bma_w_base'] = float(w_base)
                raw_preds2['bma_w_prob'] = float(w_prob)
                raw_preds2['ensemble_source'] = source
                log_router.emit_ensemble(ts=ts, asset=sym, raw_preds=raw_preds2, meta={'manifest': manifest_rel})
                # Store current predictions for next-bar alignment
                prev_base_pred_bps = base_pred_bps
                prev_prob_pred_bps = prob_pred_bps
                # Build decision-time model_out using requested source
                decision_model_out = dict(model_out)
                # Always expose both meta and bma signals for bandit arms
                decision_model_out['s_model_meta'] = s_model
                decision_model_out['s_model_bma'] = float(pred_bma_bps) / 10000.0
                # Preserve single-source s_model for non-bandit gates and logging
                if source == 'bma' and enable_bma:
                    decision_model_out['s_model'] = decision_model_out['s_model_bma']
                elif source in ('stacked', 'base'):
                    decision_model_out['s_model'] = s_model
                else:
                    # Fallback: if unknown source, keep original
                    decision_model_out = {**decision_model_out, 's_model': s_model}
            except Exception:
                # Fallback to original emission if anything goes wrong
                log_router.emit_ensemble(ts=ts, asset=sym, raw_preds=model_out, meta={'manifest': manifest_rel})
                # Best effort: still expose meta as both signals to avoid missing keys downstream
                decision_model_out = {**model_out, 's_model_meta': float(model_out.get('s_model', 0.0) if isinstance(model_out, dict) else 0.0), 's_model_bma': float(model_out.get('s_model', 0.0) if isinstance(model_out, dict) else 0.0)}
            # Log features (dedicated feature logging)
            try:
                # Enrich market_data for feature logging (mid, spread, rv_1h, funding)
                spread_bps_est = None
                try:
                    bt0 = md.get_book_ticker()
                    if bt0 and bt0.get('bid') and bt0.get('ask'):
                        bid1 = float(bt0['bid'])
                        ask1 = float(bt0['ask'])
                        if bid1 > 0 and ask1 > 0:
                            mid0 = (bid1 + ask1) / 2.0
                            spread_bps_est = 10000.0 * ((ask1 - bid1) / mid0)
                except Exception:
                    spread_bps_est = None
                rv1h_val = None
                try:
                    if isinstance(lf.columns, list) and 'rv_1h' in lf.columns:
                        idx_rv = lf.columns.index('rv_1h')
                        if 0 <= idx_rv < len(x):
                            rv1h_val = float(x[idx_rv])
                except Exception:
                    rv1h_val = None
                market_data_enriched = {
                    **bar_row,
                    'mid': c,
                    'spread_bps': spread_bps_est,
                    'rv_1h': rv1h_val,
                    'funding_8h': funding_rate,
                }
                feature_log = feature_logger.log_features_dict(
                    ts=ts,
                    bar_id=bar_count,
                    asset=sym,
                    market_data=market_data_enriched,
                    features=x,
                    feature_names=list(lf.columns) if isinstance(lf.columns, list) else [],
                )
                if feature_log:
                    try:
                        emitter = get_emitter()
                        emitter.emit_feature_log(feature_log)
                    except Exception:
                        pass
            except Exception:
                pass
            # Update health trackers
            try:
                _health_preds.append(
                    (
                        float(model_out.get("p_down", 0.0)),
                        float(model_out.get("p_up", 0.0)),
                    )
                )
            except Exception:
                pass
            try:
                _health_smodels.append(float(model_out.get("s_model", 0.0)))
            except Exception:
                pass

            # Log calibration (enhanced with realized returns)
            try:
                # Calculate realized return for calibration
                realized_return = 0.0
                if bar_count > 0 and last_close is not None and c is not None:
                    realized_return = (
                        (c - last_close) / last_close
                    ) * 10000  # Convert to bps

                # Get calibration parameters from model output
                calibration_params = {
                    "a": model_out.get("a", 0.0),
                    "b": model_out.get("b", 1.0),
                }

                calibration_log = calibration_enhancer.log_calibration_dict(
                    ts=ts,
                    bar_id=bar_count,
                    asset=sym,
                    calibration_params=calibration_params,
                    prediction=model_out.get("s_model", 0.0),
                    realized_return=realized_return,
                )
                if calibration_log:
                    emitter.emit_calibration(calibration_log)
            except Exception:
                pass

            # 6) Decision (bandit)
            # Read epsilon and model_optimism from config (defaults 0.0)
            try:
                eps = float(
                    cfg.get("execution", {}).get("bandit", {}).get("epsilon", 0.0)
                )
            except (ValueError, TypeError):
                eps = 0.0
            try:
                optimism = float(
                    cfg.get("execution", {})
                    .get("bandit", {})
                    .get("model_optimism", 0.0)
                )
            except (ValueError, TypeError):
                optimism = 0.0
            if bandit is not None:
                d = decide(cohort.snapshot(), decision_model_out, th, bandit=bandit, epsilon=eps, model_optimism=optimism)
            else:
                d = gate_and_score(cohort.snapshot(), decision_model_out, th)
            decision = d
            # Annotate decision details with source info when BMA is enabled
            try:
                ens_cfg = cfg.get('ensemble', {}) or {}
                src = str(ens_cfg.get('source', 'bma')).lower()
                if bool(ens_cfg.get('enable_bma', False)):
                    det_prev = decision.get('details', {}) if isinstance(decision, dict) else {}
                    decision = {
                        **decision,
                        'details': {**det_prev, 'model_source': src, 'bma_w_base': float(w_base), 'bma_w_prob': float(w_prob), 'pred_bma_bps': float(pred_bma_bps)}
                    }
            except Exception:
                pass
            # If overlay is enabled and system initialized, let it form/override the decision
            if overlay_sys and overlay_sys.is_initialized:
                try:
                    # Add market data to overlay system
                    # Build ISO UTC 'Z' timestamp using already-imported datetime/timezone
                    ts_utc = datetime.fromtimestamp(ts/1000.0, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                    overlay_sys.add_market_data({
                        'timestamp': ts_utc,
                        'bar_id': bar_count,
                        'open': o, 'high': h, 'low': l, 'close': c, 'volume': v,
                        'funding': funding_rate,
                        'spread_bps': None,
                        'rv_1h': None,
                    })
                    ovd = overlay_sys.generate_decision({'pros': cohort.pros, 'amateurs': cohort.amateurs, 'mood': cohort.mood}, bar_count)
                    # Map overlay decision to local decision structure
                    decision = {
                        'dir': int(getattr(ovd, 'direction', decision.get('dir', 0))),
                        'alpha': float(getattr(ovd, 'alpha', decision.get('alpha', 0.0))),
                        'details': {
                            **(decision.get('details', {}) if isinstance(decision, dict) else {}),
                            'overlay': {
                                'enabled': True,
                                'confidence': float(getattr(ovd, 'confidence', 0.0)),
                                'chosen_timeframes': list(getattr(ovd, 'chosen_timeframes', []) or []),
                                'alignment_rule': str(getattr(ovd, 'alignment_rule', '')),
                                'individual_signals': getattr(ovd, 'individual_signals', {}) or {}
                            }
                        }
                    }
                    # Enforce exact alignment behavior from config in main loop
                    try:
                        arules = (cfg.get('alignment', {}) or {}).get('rules') or cfg.get('alignment', {}) or {}
                        # Compute calibrated prediction and band
                        cal_cfg2 = cfg.get('calibration', {})
                        band_bps2 = float(cal_cfg2.get('band_bps', 15))
                        a2 = float(model_out.get('a', 0.0)) if isinstance(model_out, dict) else 0.0
                        b2 = float(model_out.get('b', 1.0)) if isinstance(model_out, dict) else 1.0
                        s_src = float((decision_model_out if 'decision_model_out' in locals() else model_out).get('s_model', 0.0)) if isinstance(model_out, dict) else 0.0
                        pred_cal_bps2 = 10000.0 * (a2 + (b2 * s_src))
                        indiv = decision['details']['overlay'].get('individual_signals', {}) or {}
                        # Extract timeframe directions
                        d5 = int((indiv.get('5m') or {}).get('dir', 0))
                        d15 = int((indiv.get('15m') or {}).get('dir', 0))
                        d1h = int((indiv.get('1h') or {}).get('dir', 0))
                        # If 5m opposes 15m, skip unless |pred_cal_bps| > conflict_mult * band
                        conflict_mult = float(arules.get('conflict_band_mult', 2.0))
                        if d5 != 0 and d15 != 0 and d5 != d15:
                            if abs(pred_cal_bps2) <= (conflict_mult * band_bps2):
                                decision['dir'] = 0
                                decision['alpha'] = 0.0
                                decision['details']['overlay']['alignment_rule'] = decision['details']['overlay'].get('alignment_rule','') + '+conflict_band_skip'
                        # If 1h disagrees with final dir, halve size (alpha)
                        if int(d1h) != 0 and int(d1h) != int(decision.get('dir', 0)) and int(decision.get('dir', 0)) != 0:
                            decision['alpha'] = 0.5 * float(decision.get('alpha', 0.0))
                            decision['details']['overlay']['alignment_rule'] = decision['details']['overlay'].get('alignment_rule','') + '+halve_on_1h_opposition'
                            decision['details']['overlay']['alignment_enforcement'] = 'applied'
                    except Exception:
                        pass
                    # Emit overlay_status via router (LLM-friendly)
                    try:
                        indiv = {}
                        ind = getattr(ovd, 'individual_signals', {}) or {}
                        for tf, sig in (ind.items() if isinstance(ind, dict) else []):
                            try:
                                indiv[str(tf)] = {
                                    'dir': int(getattr(sig, 'direction', 0)),
                                    'alpha': float(getattr(sig, 'alpha', 0.0)),
                                    'conf': float(getattr(sig, 'confidence', 0.0)),
                                }
                            except Exception:
                                continue
                        log_router.emit_overlay_status(
                            ts=ts,
                            asset=sym,
                            status={
                                'bar_id': int(bar_count),
                                'confidence': float(getattr(ovd, 'confidence', 0.0)),
                                'alignment_rule': str(getattr(ovd, 'alignment_rule', '')),
                                'chosen_timeframes': list(getattr(ovd, 'chosen_timeframes', []) or []),
                                'individual_signals': indiv,
                            }
                        )
                        # Also buffer an overlay row to Sheets if configured
                        try:
                            overlay_tab = cfg['sheets']['tabs'].get('overlay')
                            if overlay_tab:
                                logger.buffer(
                                    tab=overlay_tab,
                                    row=[
                                        to_iso(ts), ts,
                                        decision.get('dir'),
                                        decision.get('alpha'),
                                        float(getattr(ovd, 'confidence', 0.0)),
                                        str(getattr(ovd, 'alignment_rule', '')),
                                        ",".join(list(getattr(ovd, 'chosen_timeframes', []) or [])),
                                        json.dumps(indiv)
                                    ]
                                )
                        except Exception:
                            pass
                    except Exception:
                        pass
                except Exception:
                    pass
            # Optional compact ensemble handled by router above per config
            # Log order intent (pre-trade decision)
            try:
                order_intent = order_intent_tracker.log_order_intent_dict(
                    ts=ts,
                    bar_id=bar_count,
                    asset=sym,
                    decision=decision,
                    model_out=model_out,
                    market_data=bar_row,
                    risk_state={"position": risk.get_position()},
                )
                if order_intent:
                    emitter.emit_order_intent(order_intent)
            except Exception:
                pass

            # Bandit selection log (event: select) + persist state early
            det = decision.get("details", {}) if isinstance(decision, dict) else {}
            elig = det.get("eligible", {}) if isinstance(det, dict) else {}
            if bandit is not None:
                chosen_for_reward = det.get('chosen')
                raw_val_for_reward = det.get('raw_val')
                logger.buffer(
                    tab=cfg["sheets"]["tabs"].get("bandit", "bandit"),
                    row=[
                        to_iso(ts), ts,
                        'select',
                        chosen_for_reward or '',
                        raw_val_for_reward if raw_val_for_reward is not None else '',
                        decision.get('dir', ''),
                        decision.get('alpha', ''),
                        int(bool(elig.get('pros', False))),
                        int(bool(elig.get('amateurs', False))),
                        int(bool(elig.get('model_meta', False))),
                        int(bool(elig.get('model_bma', False))),
                        '',  # reward not known yet at selection time
                        '', '', ''  # counts/means/variances after update
                    ],
                )
                # Persist bandit state immediately so runtime_bandit.json appears even before first reward
                try:
                    if bandit_io is not None:
                        bandit_io.save(bandit)
                except Exception:
                    pass
                # Track raw signal for improved reward shaping next bar
                try:
                    last_chosen_raw_val = float(raw_val_for_reward) if raw_val_for_reward is not None else None
                except Exception:
                    last_chosen_raw_val = None
            # (debug CSV select logging removed)

            # 6.2) Pre-trade guards (spread, funding, flip-gap, delta-pi-min, throttle, adv-hour)
            try:
                bt = md.get_book_ticker()
                decision = risk.evaluate_pretrade_guards(
                    decision,
                    ts_ms=ts,
                    book_ticker=bt,
                    funding_rate=funding_rate,
                    last_price=c,
                    controls=cfg.get('risk_controls', {}),
                    microstructure_cfg=cfg.get('microstructure', {})
                )
            except Exception:
                pass
            # 6.3) Calibration no-trade band gate (±band_bps on calibrated prediction in bps)
            try:
                cal_cfg = cfg.get('calibration', {})
                band_bps = float(cal_cfg.get('band_bps', 15))
                a = float(model_out.get('a', 0.0)) if isinstance(model_out, dict) else 0.0
                b = float(model_out.get('b', 1.0)) if isinstance(model_out, dict) else 1.0
                s_model_cal = float((decision_model_out if 'decision_model_out' in locals() else model_out).get('s_model', 0.0)) if isinstance(model_out, dict) else 0.0
                pred_cal_bps = 10000.0 * (a + (b * s_model_cal))
                try:
                    health_monitor.update_inband(pred_cal_bps, band_bps)
                except Exception:
                    pass
                try:
                    in_band_flag = bool(abs(pred_cal_bps) <= band_bps)
                    write_jsonl('calibration_log', {
                        'asset': sym,
                        'a': float(a),
                        'b': float(b),
                        'pred_cal_bps': float(pred_cal_bps),
                        'in_band_flag': bool(in_band_flag),
                        'band_bps': float(band_bps),
                    }, asset=sym)
                except Exception:
                    pass
                if abs(pred_cal_bps) <= band_bps:
                    details_prev = decision.get('details', {}) if isinstance(decision, dict) else {}
                    decision = {
                        **decision,
                        'dir': 0,
                        'alpha': 0.0,
                        'details': {**details_prev, 'mode': 'calibration_band_gate', 'pred_cal_bps': pred_cal_bps, 'band_bps': band_bps}
                    }
            except Exception:
                pass
            except Exception:
                pass

            # 7) Risk + execution
            # Warm-up skip: avoid trading for the first N bars
            warm_skip = int(getattr(risk.cfg, "warmup_skip_bars", 0) or 0)
            if bar_count < warm_skip:
                exec_resp = None
            else:
                # Optionally force a small validation trade once if neutral decision
                if decision["dir"] == 0 and force_validation and not used_force:
                    decision = {
                        **decision,
                        "dir": 1,
                        "alpha": max(0.05, abs(model_out.get("s_model", 0.1))),
                    }
                    used_force = True
                # If daily stop triggered, enforce flat
                if stopped_for_day:
                    tgt = 0.0
                    exec_resp = risk.mirror_to_exchange(
                        tgt, last_price=c, dry_run=dry_run
                    )
                elif not risk.in_cooldown(ts):
                    tgt = (
                        risk.target_position(decision["dir"], decision["alpha"])
                        if decision["dir"] != 0
                        else 0.0
                    )
                    # Select execution mode
                    mode = str(cfg.get("execution", {}).get("mode", "market")).lower()
                    if mode == "passive_then_cross":
                        bt = md.get_book_ticker()
                        timeout_s = float(cfg.get('execution', {}).get('passive_timeout_s', 10))
                        risk.notify_order_attempt(ts)
                        exec_resp = risk.mirror_passive_then_cross(tgt, last_price=c, book=bt, timeout_s=timeout_s, dry_run=dry_run)
                    else:
                        risk.notify_order_attempt(ts)
                        exec_resp = risk.mirror_to_exchange(tgt, last_price=c, dry_run=dry_run)
                    risk.set_cooldown(ts)
                else:
                    exec_resp = None

            # Emit sizing/risk JSONL (post sizing/before logging exec)
            try:
                write_jsonl("sizing_risk_log", {
                    "asset": sym,
                    "forecast_vol_20": None,
                    "target_vol_ann": float(getattr(risk.cfg, 'sigma_target', 0.0) or 0.0),
                    # Use the same s_model source as decision for consistency
                    "raw_score_bps": round(10000.0 * float((decision_model_out if 'decision_model_out' in locals() else model_out).get('s_model', 0.0)), 1),
                    "position_after": float(risk.get_position()),
                    "notional_usd": None,
                    "adv_cap_hit": False,
                    "overlay_conf": float(decision.get('details',{}).get('overlay',{}).get('confidence', 0.0)) if isinstance(decision, dict) else 0.0,
                }, asset=sym)
            except Exception:
                pass

            # 7.5) Execution tracking and PnL attribution
            if exec_resp:
                try:
                    # Track execution details
                    # Update risk state with executed notional and flip timing
                    try:
                        risk.post_execution_update(exec_resp, ts)
                    except Exception:
                        pass
                    execution_id = execution_tracker.start_execution(
                        asset=sym,
                        bar_id=bar_count,
                        side=exec_resp.get("side", "UNKNOWN"),
                        order_type=exec_resp.get("order_type", "MARKET"),
                        limit_px=exec_resp.get("limit_px"),
                    )

                    # Complete execution tracking
                    execution_tracker.complete_execution(
                        execution_id=execution_id,
                        fill_px=exec_resp.get("price"),
                        fill_qty=exec_resp.get("qty"),
                        route=exec_resp.get("route", "BINANCE"),
                        slip_bps=exec_resp.get("slip_bps"),
                        ioc_ms=exec_resp.get("ioc_ms"),
                    )

                    # Update PnL attribution
                    if exec_resp.get("qty") and exec_resp.get("price"):
                        position_change = float(exec_resp.get("qty", 0))
                        fill_price = float(exec_resp.get("price", 0))
                        pnl_attribution.update_position(position_change, fill_price, ts)

                        # Add fees and impact
                        if exec_resp.get('fee'):
                            pnl_attribution.add_fee(float(exec_resp.get('fee', 0)), ts)
                        if exec_resp.get('impact'):
                            pnl_attribution.add_impact(float(exec_resp.get('impact', 0)), ts)
                    
                    # Fetch execution log (kept for potential future use),
                    # but avoid emitting here to prevent duplicate 'executions' entries.
                    execution_log = execution_tracker.get_execution_log(ts, sym, bar_count)
                    
                    # Emit PnL attribution log via router (costs domain)
                    pnl_log = pnl_attribution.get_attribution_log(ts, sym, bar_count)
                    if pnl_log:
                        log_router.emit_costs(ts=ts, asset=sym, costs=pnl_log)
                except Exception:
                    pass

            # 7.6) Bandit reward update based on realized pnl proxy from last bar
            # Use the arm chosen on the previous bar (last_chosen_arm)
            if bandit is not None and last_close_value is not None and last_chosen_arm is not None:
                try:
                    # Realized return (bps) since last bar
                    realized_bps = 10000.0 * ((c / last_close_value) - 1.0)
                    # Reward shaping: prefer using raw signal magnitude as exposure proxy
                    if last_chosen_raw_val is not None:
                        reward = realized_bps * float(last_chosen_raw_val)
                    else:
                        # Fallback to position-based reward (legacy behaviour)
                        r = (c / last_close_value) - 1.0
                        reward = r * (
                            last_exec_pos if isinstance(last_exec_pos, (int, float)) else 0.0
                        )
                    chosen = last_chosen_arm
                    arm_index = {'pros': 0, 'amateurs': 1, 'model_meta': 2, 'model_bma': 3, 'model': 2}.get(str(chosen), None)
                    if arm_index is not None:
                        bandit.update(int(arm_index), float(reward))
                        if bandit_io is not None:
                            bandit_io.save(bandit)
                        logger.buffer(
                            tab=cfg["sheets"]["tabs"].get("bandit", "bandit"),
                            row=[
                                to_iso(ts), ts, "update", chosen,
                                '', '', '', '', '', '', '',
                                float(reward),
                                json.dumps([float(x) for x in getattr(bandit, "counts", [])]),
                                json.dumps([float(x) for x in getattr(bandit, "means", [])]),
                                json.dumps([float(x) for x in getattr(bandit, "variances", [])]),
                            ],
                        )
                except (ValueError, TypeError, KeyError):
                    pass
            # Compute realized bps for the just-completed bar (for BMA alignment next bar)
            try:
                if last_close_value is not None:
                    last_realized_bps_buffer = 10000.0 * ((float(c) / float(last_close_value)) - 1.0)
            except Exception:
                pass
            # Update trackers for next bar
            last_close_value = c
            last_exec_pos = tgt if "tgt" in locals() else 0.0
            # chosen arm is available at decision['details'].get('chosen') if needed for logging
            last_chosen_arm = (
                decision.get("details", {}).get("chosen")
                if bandit is not None
                else None
            )

            # Mirror log
            # Compute per-bar equity on last known price and update daily stop state
            try:
                ps = risk.get_paper_state()
                paper_qty = ps["paper_qty"]
                paper_avg_px = ps["paper_avg_px"]
                realized = ps["realized_pnl"]
                unrealized = (
                    (c - paper_avg_px) * paper_qty if abs(paper_qty) > 1e-12 else 0.0
                )
                equity = starting_equity + realized + unrealized
                # Track peak equity and trigger daily stop if drawdown exceeds threshold
                try:
                    session_peak_equity = max(session_peak_equity, equity)
                    dd_pct = (
                        100.0
                        * (session_peak_equity - equity)
                        / max(1e-9, session_peak_equity)
                    )
                    stop_thr = float(getattr(risk.cfg, "daily_stop_dd_pct", 0.0) or 0.0)
                    if (not stopped_for_day) and stop_thr > 0.0 and dd_pct >= stop_thr:
                        stopped_for_day = True
                except Exception:
                    pass
                # Optionally write a compact equity row to a dedicated tab if present
                equity_tab = cfg["sheets"]["tabs"].get("equity")
                if equity_tab:
                    logger.buffer(
                        tab=equity_tab,
                        row=[
                            to_iso(ts),
                            ts,
                            c,
                            paper_qty,
                            paper_avg_px,
                            realized,
                            unrealized,
                            equity,
                        ],
                    )
                # Compute realized return (bps) vs previous close if available
                realized_ret_bps = None
                try:
                    if last_close_value is not None:
                        realized_ret_bps = 10000.0 * ((float(c) / float(last_close_value)) - 1.0)
                except Exception:
                    realized_ret_bps = None
                # Equity/PnL compact (llm per config)
                log_router.emit_equity(asset=sym, ts=ts, pnl_total_usd=round(float(realized + unrealized), 2), equity_value=round(float(equity), 2), realized_return_bps=realized_ret_bps)
            except (TypeError, ValueError, KeyError):
                equity = ""

            if exec_resp:
                _qty_val_m = (
                    exec_resp.get("qty") if isinstance(exec_resp, dict) else 0.0
                )
                _px_val_m = (
                    exec_resp.get("price") if isinstance(exec_resp, dict) else 0.0
                )
                _notional_m = (
                    abs(float(_qty_val_m) * float(_px_val_m))
                    if _qty_val_m is not None and _px_val_m is not None
                    else ""
                )
                _intended_notional = (
                    abs(float(tgt) * float(risk.cfg.base_notional))
                    if "tgt" in locals()
                    else ""
                )
                logger.buffer(
                    tab=cfg["sheets"]["tabs"]["mirror"],
                    row=[
                        to_iso(ts),
                        ts,
                        decision["dir"],
                        decision["alpha"],
                        c,
                        _notional_m,
                        _intended_notional,
                        tgt,
                        risk.get_position(),
                        (
                            exec_resp.get("exch_qty_before")
                            if isinstance(exec_resp, dict)
                            else ""
                        ),
                        (
                            exec_resp.get("exch_qty_after")
                            if isinstance(exec_resp, dict)
                            else ""
                        ),
                        (
                            exec_resp.get("reconciled")
                            if isinstance(exec_resp, dict)
                            else ""
                        ),
                        json.dumps(exec_resp),
                    ],
                )
                # Routed execution emission (emitter and/or llm based on config)
                log_router.emit_execution(ts=ts, asset=sym, exec_resp=exec_resp, risk_state={'position': risk.get_position()}, bar_id=bar_count)
                # health exec counter
                try:
                    _health_exec_count += 1
                except Exception:
                    pass
                # Write detailed paper execution row
                try:
                    # Compute notionals
                    _qty_val = (
                        exec_resp.get("qty") if isinstance(exec_resp, dict) else 0.0
                    )
                    _px_val = (
                        exec_resp.get("price") if isinstance(exec_resp, dict) else 0.0
                    )
                    _notional = (
                        abs(float(_qty_val) * float(_px_val))
                        if _qty_val is not None and _px_val is not None
                        else ""
                    )
                    _intended = (
                        abs(float(tgt) * float(risk.cfg.base_notional))
                        if "tgt" in locals()
                        else ""
                    )
                    logger.buffer(
                        tab=cfg["sheets"]["tabs"].get("executions", "executions_paper"),
                        row=[
                            to_iso(ts),
                            ts,
                            exec_resp.get("side"),
                            exec_resp.get("qty"),
                            exec_resp.get("mid_price"),
                            exec_resp.get("price"),
                            _notional,
                            _intended,
                            tgt,
                            exec_resp.get("paper_qty"),
                            exec_resp.get("paper_avg_px"),
                            exec_resp.get("realized_pnl"),
                            exec_resp.get("unrealized_pnl"),
                            exec_resp.get("fee"),
                            exec_resp.get("impact"),
                            equity,
                            json.dumps(exec_resp),
                        ],
                    )
                except (TypeError, ValueError, KeyError):
                    pass
                else:
                    # Emit costs via router (best-effort)
                    try:
                        trade_notional = abs(float(_qty_val) * float(_px_val)) if (_qty_val is not None and _px_val is not None) else 0.0
                        fee_bps = float(getattr(risk.cfg, 'cost_bps', 0.0) or 0.0)
                        impact_usd = float(exec_resp.get('impact', 0.0) or 0.0)
                        impact_bps = (impact_usd / trade_notional * 10000.0) if trade_notional > 0 else None
                        slip_bps = exec_resp.get('slip_bps')
                        cost_bps_total = None
                        if impact_bps is not None:
                            cost_bps_total = round(fee_bps + (float(slip_bps) if slip_bps else 0.0) + impact_bps, 1)
                        costs_payload = {
                            "trade_notional": round(trade_notional, 2),
                            "fee_bps": round(fee_bps, 1),
                            "slip_bps": slip_bps,
                            "impact_k": float(getattr(risk.cfg, 'impact_k', 0.0) or 0.0),
                            "impact_bps": round(impact_bps, 1) if impact_bps is not None else None,
                            "adv_ref": round(float(getattr(risk, 'adv20_usd', 0.0) or 0.0), 2),
                            "cost_usd": round(float(exec_resp.get('fee', 0.0) or 0.0) + impact_usd, 2),
                            "cost_bps_total": cost_bps_total,
                            # Explicit USD components for LLM diagnostics
                            "fee_usd": round(float(exec_resp.get('fee', 0.0) or 0.0), 2),
                            "slip_usd": round((trade_notional * float(slip_bps) / 10000.0), 2) if (slip_bps is not None and trade_notional > 0) else None,
                            "impact_usd": round(impact_usd, 2),
                        }
                        log_router.emit_costs(ts=ts, asset=sym, costs=costs_payload)
                    except Exception:
                        pass

            # 8) Sheets logging (signals)
            # Extract BMA details from decision (populated above) if present
            try:
                det2 = decision.get('details', {}) if isinstance(decision, dict) else {}
                model_source = det2.get('model_source')
                bma_w_base = det2.get('bma_w_base')
                bma_w_prob = det2.get('bma_w_prob')
                pred_bma_bps = det2.get('pred_bma_bps')
            except Exception:
                model_source = None; bma_w_base = None; bma_w_prob = None; pred_bma_bps = None
            # Prefer explicit s_model_meta/bma from decision_model_out when available
            s_meta = float((decision_model_out or {}).get('s_model_meta', model_out.get('s_model', 0.0))) if isinstance(model_out, dict) else 0.0
            s_bma = float((decision_model_out or {}).get('s_model_bma', model_out.get('s_model', 0.0))) if isinstance(model_out, dict) else 0.0
            logger.buffer(
                tab=cfg["sheets"]["tabs"]["signals"],
                row=[
                    to_iso(ts), ts, o, h, l, c, v,
                    cohort.pros, cohort.amateurs, cohort.mood,
                    model_out.get('p_down'), model_out.get('p_neutral'), model_out.get('p_up'), model_out.get('s_model'),
                    s_meta, s_bma, model_source, bma_w_base, bma_w_prob, pred_bma_bps,
                    decision['dir'], decision['alpha'], funding_rate, funding_stale,
                    risk.get_position(), json.dumps(exec_resp) if exec_resp else ''
                ]
            )
            # Emit signals JSONL for observability (best-effort)
            try:
                emitter = get_emitter()
                emitter.emit_signals(ts=ts, symbol=sym, features=x, model_out=model_out, decision=decision, cohort={'pros': cohort.pros, 'amateurs': cohort.amateurs, 'mood': cohort.mood})
            except Exception:
                pass

            # Periodic health emission
            try:
                if (bar_count % _health_emit_every) == 0:
                    # compute simple rolling health metrics
                    p_downs = [p[0] for p in _health_preds if isinstance(p, tuple)]
                    p_ups = [p[1] for p in _health_preds if isinstance(p, tuple)]
                    smodels = [v for v in _health_smodels if isinstance(v, (int, float))]
                    # WS freshness
                    try:
                        ws_stale_ms = int(ts - last_ws_msg_ts_ms) if (last_ws_msg_ts_ms and ts) else None
                    except Exception:
                        ws_stale_ms = None
                    health = {
                        'recent_bars': len(_health_preds),
                        'mean_p_down': float(sum(p_downs) / len(p_downs)) if p_downs else None,
                        'mean_p_up': float(sum(p_ups) / len(p_ups)) if p_ups else None,
                        'mean_s_model': float(sum(smodels) / len(smodels)) if smodels else None,
                        'exec_count_recent': int(_health_exec_count),
                        'funding_stale': bool(funding_stale),
                        'equity': float(equity) if 'equity' in locals() and isinstance(equity, (int, float)) else None,
                        'ws_queue_drops': int(ws_queue_drops),
                        'ws_reconnects': int(ws_reconnects),
                        'ws_staleness_ms': ws_stale_ms,
                    }
                    # reset short counters
                    _health_exec_count = 0

                    # Enhanced health metrics
                    try:
                        # Update health monitor
                        if last_close is not None and c is not None:
                            returns = (
                                (c - last_close) / last_close
                                if last_close != 0
                                else 0.0
                            )
                            health_monitor.update_returns(returns, ts)
                            health_monitor.update_position(risk.get_position(), ts)
                            health_monitor.update_pnl(
                                (
                                    equity - starting_equity
                                    if "equity" in locals()
                                    else 0.0
                                ),
                                ts,
                            )

                            # Update predictions
                            if model_out.get("s_model") is not None:
                                health_monitor.update_predictions(
                                    model_out["s_model"], returns, ts
                                )

                        # Get enhanced health metrics
                        enhanced_health = health_monitor.get_health_metrics()
                    except Exception:
                        pass
                    try:
                        # Only proceed if enhanced_health exists
                        if 'enhanced_health' in locals() and enhanced_health:
                            health.update({
                            'Sharpe_roll_1d': enhanced_health.sharpe_roll_1d,
                            'Sharpe_roll_1w': enhanced_health.sharpe_roll_1w,
                            'Sortino_1w': enhanced_health.sortino_1w,
                            'max_dd_to_date': enhanced_health.max_dd_to_date,
                            'time_in_mkt': enhanced_health.time_in_mkt,
                            'hit_rate_w': enhanced_health.hit_rate_w,
                            'turnover_bps_day': enhanced_health.turnover_bps_day,
                            'capacity_participation': enhanced_health.capacity_participation,
                            'ic_drift': enhanced_health.ic_drift,
                            'calibration_drift': enhanced_health.calibration_drift,
                            'leakage_flag': enhanced_health.leakage_flag,
                            'same_bar_roundtrip_flag': enhanced_health.same_bar_roundtrip_flag,
                            'in_band_share': enhanced_health.in_band_share
                            })
                        
                        # Emit health once (enhanced metrics included) via router (config-driven sinks)
                        try:
                            log_router.emit_health(ts=ts, asset=sym, health=health)
                        except Exception:
                            # Fallback to direct emitter to avoid losing health logs if router misconfigured
                            try:
                                emitter = get_emitter()
                                emitter.emit_health(ts=ts, symbol=sym, health=health)
                            except Exception:
                                pass
                        # Also buffer health metrics to Sheets if configured
                        try:
                            health_tab = cfg['sheets']['tabs'].get('health')
                            if health_tab:
                                logger.buffer(
                                    tab=health_tab,
                                    row=[
                                        to_iso(ts), ts,
                                        health.get('recent_bars'),
                                        health.get('mean_p_down'),
                                        health.get('mean_p_up'),
                                        health.get('mean_s_model'),
                                        health.get('exec_count_recent'),
                                        int(health.get('funding_stale')) if isinstance(health.get('funding_stale'), bool) else health.get('funding_stale'),
                                        health.get('equity'),
                                        health.get('ws_queue_drops'),
                                        health.get('ws_reconnects'),
                                        health.get('ws_staleness_ms'),
                                        health.get('Sharpe_roll_1d'),
                                        health.get('Sharpe_roll_1w'),
                                        health.get('Sortino_1w'),
                                        health.get('max_dd_to_date'),
                                        health.get('time_in_mkt'),
                                        health.get('hit_rate_w'),
                                        health.get('turnover_bps_day'),
                                        health.get('capacity_participation'),
                                        health.get('ic_drift'),
                                        health.get('calibration_drift'),
                                        int(health.get('leakage_flag')) if isinstance(health.get('leakage_flag'), bool) else health.get('leakage_flag'),
                                        int(health.get('same_bar_roundtrip_flag')) if isinstance(health.get('same_bar_roundtrip_flag'), bool) else health.get('same_bar_roundtrip_flag'),
                                        health.get('in_band_share')
                                    ]
                                )
                        except Exception:
                            pass
                    except Exception:
                        pass
                    
                    # WS staleness alert (simple threshold: 60s)
                    try:
                        stale_thr_ms = int(cfg.get('health', {}).get('ws_staleness_ms_threshold', 60000))
                        if isinstance(ws_stale_ms, int) and ws_stale_ms > stale_thr_ms:
                            # Emit alert JSONL via router (lightweight)
                            log_router.emit_alert(
                                ts=ts,
                                asset=sym,
                                alert={
                                    'type': 'ws_stale',
                                    'staleness_ms': ws_stale_ms,
                                    'reconnects': int(ws_reconnects),
                                    'queue_drops': int(ws_queue_drops),
                                }
                            )
                            # Buffer alert to Sheets fallback if configured
                            try:
                                alerts_tab = cfg['sheets']['tabs'].get('alerts')
                                if alerts_tab:
                                    logger.buffer(
                                        tab=alerts_tab,
                                        row=[
                                            to_iso(ts), ts,
                                            'ws_stale',
                                            ws_stale_ms,
                                            int(ws_reconnects),
                                            int(ws_queue_drops),
                                            json.dumps({'source': 'hyperliquid_ws'})
                                        ]
                                    )
                            except Exception:
                                pass
                            # Route through alert router using existing data_freshness rule (book_lag_ms)
                            try:
                                router = get_alert_router()
                                router.evaluate_alerts({'book_lag_ms': ws_stale_ms}, context={'source': 'hyperliquid_ws', 'reconnects': ws_reconnects, 'queue_drops': ws_queue_drops})
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # Repro/Config logging
                    try:
                        repro_log = repro_tracker.log_repro_config(ts)
                        emitter.emit_repro(ts=ts, symbol=sym, repro=repro_log)
                    except Exception:
                        pass
                    # Market ingest compact log (for LLM context): include mid, spread proxy, and simple time buckets
                    try:
                        # Use close as mid fallback
                        mid_px = float(c)
                        # Attempt to read spread from last known book ticker (best-effort)
                        try:
                            bt_last = md.get_book_ticker()
                            if bt_last and bt_last.get('bidPrice') and bt_last.get('askPrice'):
                                bid1 = float(bt_last['bidPrice'])
                                ask1 = float(bt_last['askPrice'])
                                spread_bps = 10000.0 * ((ask1 - bid1) / ((ask1 + bid1) / 2.0)) if (ask1 > 0 and bid1 > 0) else None
                            else:
                                spread_bps = None
                        except Exception:
                            spread_bps = None
                        # Intrabar range proxy
                        try:
                            range_bps = 10000.0 * ((float(h) - float(l)) / float(c)) if c else None
                        except Exception:
                            range_bps = None
                        write_jsonl('market_ingest_log', {
                            'asset': sym,
                            'mid': mid_px,
                            'spread_bps': None if spread_bps is None else float(spread_bps),
                            'hour_bucket': hour_bucket(ts),
                            'weekday': weekday_idx(ts),
                            'range_bps': None if range_bps is None else float(range_bps),
                        }, asset=sym)
                    except Exception:
                        pass
                    # Emit KPI scorecard (JSONL + optional Sheets tab)
                    try:
                        # Derive key KPIs and gates
                        sh_1w = health.get('Sharpe_roll_1w')
                        dd = health.get('max_dd_to_date')
                        t_bps = health.get('turnover_bps_day')
                        inband = health.get('in_band_share')
                        # Targets from prompt: Sharpe ≥ 2.5, DD ≤ 20%, costs ≤ 10 bps RT (placeholder), turnover ≤ cap (optional)
                        gate_sharpe = (sh_1w is not None) and (float(sh_1w) >= 2.5)
                        # max_dd_to_date tracked negative; convert to positive percent depth
                        dd_pct = (abs(float(dd)) * 100.0) if dd is not None else None
                        gate_dd = (dd_pct is not None) and (dd_pct <= 20.0)
                        # Cost gate: placeholder None (requires aggregation of fees/slip/impact); mark as None
                        gate_cost = None
                        # Turnover gate: if provided in config; otherwise not enforced
                        to_cap = float(cfg.get('risk', {}).get('turnover_cap_bps_day', 99999.0))
                        gate_turnover = (t_bps is not None) and (float(t_bps) <= to_cap)
                        summary = {
                            'sharpe_pass': gate_sharpe,
                            'dd_pass': gate_dd,
                            'turnover_pass': gate_turnover,
                            'cost_pass': gate_cost,
                        }
                        write_jsonl('kpi_scorecard', {
                            'asset': sym,
                            'event': 'kpi_scorecard',
                            'Sharpe_1w': sh_1w,
                            'max_DD_pct': dd_pct,
                            'turnover_bps_day': t_bps,
                            'in_band_share': inband,
                            'gates': summary,
                        }, asset=sym)
                        # Optional Sheets tab output
                        kpi_tab = cfg['sheets']['tabs'].get('kpi')
                        if kpi_tab:
                            logger.buffer(
                                tab=kpi_tab,
                                row=[
                                    to_iso(ts), ts,
                                    sh_1w, dd_pct, t_bps, inband,
                                    int(gate_sharpe) if isinstance(gate_sharpe, bool) else '',
                                    int(gate_dd) if isinstance(gate_dd, bool) else '',
                                    '' if gate_cost is None else int(bool(gate_cost)),
                                    int(gate_turnover) if isinstance(gate_turnover, bool) else '',
                                    json.dumps(summary)
                                ]
                            )
                    except Exception:
                        pass
            except Exception:
                pass
            # Local mood debug to file (best-effort, non-blocking)
            try:
                out_dir = paper_root()
                os.makedirs(out_dir, exist_ok=True)
                mood_path = os.path.join(out_dir, "mood_debug.csv")
                if not os.path.exists(mood_path):
                    with open(mood_path, "w", encoding="utf-8") as fh:
                        fh.write("ts_iso,ts,public_count,S_mood\n")
                with open(mood_path, "a", encoding="utf-8") as fh:
                    fh.write(f"{to_iso(ts)},{ts},{public_count},{cohort.mood}\n")
            except OSError:
                pass
            # Flush Sheets buffers; do not crash if Sheets is unavailable
            try:
                logger.flush()
            except gspread.exceptions.APIError:
                # Keep running; rows remain buffered for a later retry
                pass

            # Simple pacing per bar
            if one_shot:
                break
            await asyncio.sleep(1)
            bar_count += 1

        # Clean up consumer task on exit (e.g., one-shot mode)
        try:
            if _consumer_task:
                _consumer_task.cancel()
                try:
                    await _consumer_task
                except asyncio.CancelledError:
                    pass
        except NameError:
            pass

    # Graceful close of funding client session
    try:
        await funding_client.close()
    except (AttributeError, RuntimeError):
        pass


if __name__ == "__main__":
    print("Starting live demo...")
    # Allow overriding config path via environment variable (e.g., LIVE_DEMO_CONFIG)
    default_cfg = os.path.join(os.path.dirname(__file__), "config.json")
    env_cfg = os.environ.get("LIVE_DEMO_CONFIG")
    cfg_path = env_cfg if env_cfg else default_cfg
    print(f"Using config from: {cfg_path}")
    # Fallback to default if provided env path doesn't exist
    if not os.path.isabs(cfg_path):
        cfg_path = os.path.join(os.path.dirname(__file__), cfg_path)
    if not os.path.exists(cfg_path):
        cfg_path = default_cfg
    try:
        cfg_main = load_config(cfg_path)
        # Default to dry_run per config (no live orders unless explicitly disabled)
        dry = bool(cfg_main.get("execution", {}).get("dry_run", False))
    except (FileNotFoundError, ValueError, KeyError):
        # As a last resort, run with default config if readable, otherwise abort gracefully
        try:
            cfg_path = default_cfg
            cfg_main = load_config(cfg_path)
            dry = bool(cfg_main.get("execution", {}).get("dry_run", False))
        except Exception as e:
            print(f"Failed to load config at {cfg_path}: {e}")
            raise SystemExit(1)
    # (heartbeat file writing removed)
    try:
        asyncio.run(run_live(cfg_path, dry_run=dry))
    except (
        RuntimeError,
        OSError,
        ValueError,
        KeyError,
        ImportError,
        gspread.exceptions.APIError,
    ) as exc:
        try:
            _pt_root = os.environ.get('PAPER_TRADING_ROOT') or os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'paper_trading_outputs'))
            fatal_err_path = os.path.join(_pt_root, 'live_errors.log')
            os.makedirs(os.path.dirname(fatal_err_path), exist_ok=True)
            import traceback

            with open(fatal_err_path, "a", encoding="utf-8") as fatal_err_fh:
                fatal_err_fh.write("\n===== Uncaught exception =====\n")
                fatal_err_fh.write("Type: " + type(exc).__name__ + "\n")
                fatal_err_fh.write("Message: " + str(exc) + "\n")
                fatal_err_fh.write(traceback.format_exc())
        except OSError:
            pass
