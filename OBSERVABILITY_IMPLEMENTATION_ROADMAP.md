# Observability Implementation Roadmap
**Created**: 2025-12-22 (Asia/Kolkata UTC+5:30)  
**Based on**: OBSERVABILITY_AUDIT_DEC20_2025.md  
**Status**: Ready for Implementation

---

## Quick Wins (0.5-1 day each) 🚀

### QW1. Reduce Health Emission Frequency
**Effort**: 0.5 days | **Impact**: HIGH | **Type**: Performance Fix

**What it improves**:
- Reduces log volume by ~85% (96 → 12 emissions/day)
- Lowers storage costs
- Makes logs easier to parse for LLMs
- Reduces I/O overhead

**Why needed**:
- Current: Emitting health every bar is excessive when 90% of bars are identical
- Only meaningful changes should trigger emissions (equity moves, staleness toggles, errors)
- Heartbeat every 60 bars is sufficient for monitoring

**Implementation**:
```python
# In main.py around line 513
_health_emit_every = 60  # Already in config
last_equity = None
last_funding_stale = None
last_ws_reconnects = 0

# In main loop around line 1773-1854
should_emit_health = (
    (bar_count % _health_emit_every) == 0 or  # Heartbeat
    (last_equity and abs(equity - last_equity) / last_equity > 0.001) or  # 0.1% equity change
    (last_funding_stale != health.get('funding_stale')) or  # Staleness toggle
    (health.get('ws_reconnects', 0) > last_ws_reconnects) or  # New reconnection
    (health.get('calibration_drift', 0) > 0.05)  # Calibration degraded
)

if should_emit_health:
    log_router.emit_health(ts=ts, asset=sym, health=health)
    emitter.emit_health(ts=ts, symbol=sym, health=health)
    last_equity = equity
    last_funding_stale = health.get('funding_stale')
    last_ws_reconnects = health.get('ws_reconnects', 0)
```

**Verification**:
- Check health.jsonl has ~12 records/day instead of ~96
- Confirm no information loss during equity swings or errors

---

### QW2. Add Order Rejection Detail Logging
**Effort**: 1 day | **Impact**: HIGH | **Type**: Debug Enhancement

**What it improves**:
- Immediate visibility into why orders fail
- Captures market state at rejection time
- Tracks retry attempts
- Enables failure pattern analysis

**Why needed**:
- Current: `rejections` counter exists but no details on why/when/what
- Dec 20 logs show 0 trades - need visibility when trades ARE attempted
- Exchange-specific error codes help debug integration issues
- Market state helps distinguish between our bug vs. exchange issue

**Implementation**:
```python
# In live_demo/risk_and_exec.py execution logic
def execute_order(self, side, qty, symbol, order_type='MARKET', limit_px=None):
    for attempt in range(max_retries):
        try:
            resp = self._exchange.place_order(...)
            if resp.get('status') == 'rejected':
                # Capture rejection details
                market_state = self._get_current_market_state(symbol)
                rejection_log = {
                    'ts_ist': datetime.now(IST).isoformat(),
                    'symbol': symbol,
                    'side': side,
                    'qty': qty,
                    'order_type': order_type,
                    'limit_px': limit_px,
                    'rejection_reason': resp.get('error_code'),
                    'rejection_message': resp.get('error_message'),
                    'market_state': {
                        'bid': market_state.get('bid'),
                        'ask': market_state.get('ask'),
                        'spread_bps': market_state.get('spread_bps'),
                        'volume_1m': market_state.get('volume_1m'),
                    },
                    'retry_attempt': attempt + 1,
                    'max_retries': max_retries,
                }
                # Emit to new rejection stream
                emitter.emit_rejection(rejection_log)
                
            return resp
        except Exception as e:
            # Also log exceptions
            ...
```

**New Event Stream**: `rejections.jsonl`

**Verification**:
- Trigger rejection by submitting order with unrealistic limit price
- Check rejections.jsonl has market state and reason code
- Verify retry_attempt increments correctly

---

### QW3. Add Slack Alert Wiring (Critical Triggers Only)
**Effort**: 1 day | **Impact**: HIGH | **Type**: Operations Alert

**What it improves**:
- Real-time notification of critical issues
- Reduces need to monitor logs continuously
- Enables faster incident response
- Phone notifications for after-hours issues

**Why needed**:
- Current: LogRouter has alert methods but they write to logs, not Slack
- Nobody monitors logs in real-time during off-hours
- Critical issues (equity crash, data staleness) need immediate attention
- Prevents silent failures

**Implementation**:
```python
# In live_demo/alerts/ (create new module)
import os
import requests
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

class SlackAlerter:
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url)
        self.alert_cooldowns = {}  # Prevent alert spam
        self.cooldown_seconds = 3600  # 1 hour
    
    def should_alert(self, alert_key: str) -> bool:
        last_alert = self.alert_cooldowns.get(alert_key)
        if last_alert and (datetime.now().timestamp() - last_alert < self.cooldown_seconds):
            return False
        return True
    
    def send(self, level: str, title: str, message: str, fields: dict = None):
        if not self.enabled:
            return
        
        alert_key = f"{level}:{title}"
        if not self.should_alert(alert_key):
            return
        
        color_map = {
            'CRITICAL': 'danger',
            'WARNING': 'warning',
            'INFO': 'good'
        }
        
        attachments = [{
            'color': color_map.get(level, 'warning'),
            'title': title,
            'text': message,
            'fields': [
                {'title': k, 'value': str(v), 'short': True}
                for k, v in (fields or {}).items()
            ],
            'footer': 'MetaStackerBandit',
            'ts': int(datetime.now(IST).timestamp())
        }]
        
        payload = {
            'text': f"[{level}] {title}",
            'attachments': attachments
        }
        
        try:
            requests.post(self.webhook_url, json=payload, timeout=5)
            self.alert_cooldowns[alert_key] = datetime.now().timestamp()
        except Exception:
            pass  # Don't crash bot if Slack fails

# In main.py around line 1849 (health check)
slack = SlackAlerter()

# Critical triggers only:
if equity < 9500:  # 5% drawdown
    slack.send('CRITICAL', 'Equity Drawdown Alert',
               f'Equity dropped to ${equity:.2f}',
               {'Target': '$10,000', 'Current': f'${equity:.2f}', 'Loss': f'{(10000-equity)/100:.2f}%'})

if health.get('ws_staleness_ms', 0) > 30000:  # 30s stale
    slack.send('CRITICAL', 'Data Staleness Alert',
               f'WebSocket data {health["ws_staleness_ms"]/1000:.1f}s stale',
               {'Symbol': sym, 'Staleness': f'{health["ws_staleness_ms"]/1000:.1f}s'})

if health.get('funding_stale') and (time.time() - last_funding_ts > 3600):
    slack.send('WARNING', 'Funding Data Stale',
               'No funding data update for >1 hour',
               {'Symbol': sym, 'Hours_Stale': f'{(time.time() - last_funding_ts)/3600:.1f}'})

if health.get('same_bar_roundtrip_flag'):
    slack.send('CRITICAL', 'Leakage Detection',
               'Same-bar roundtrip detected - possible data leakage!',
               {'Symbol': sym, 'Bar_ID': bar_count})
```

**Environment Variable**: Add `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL` to `.env`

**Verification**:
- Manually trigger equity drop to 9500 and verify Slack message received
- Test cooldown by triggering same alert twice within 1 hour
- Verify alert includes all fields and formatted correctly

---

### QW4. Add Snapshot.jsonl Population
**Effort**: 0.5 days | **Impact**: MEDIUM | **Type**: Data Completeness

**What it improves**:
- Enables time-series analysis of health metrics
- Provides clean hourly/daily summaries for LLMs
- Supports trend analysis (equity curve, Sharpe evolution)

**Why needed**:
- Current: HealthSnapshotEmitter exists but emits all-null records
- Dec 20: Only 1 snapshot with zero meaningful data
- Schema is well-defined but not being populated from health metrics
- LLM summaries need these bucketed snapshots

**Implementation**:
```python
# In main.py around line 1854 (after health emission)
from live_demo.emitters.health_snapshot_emitter import HealthSnapshot, HealthSnapshotEmitter

snapshot_emitter = HealthSnapshotEmitter(base_logs_dir="paper_trading_outputs/logs")

# Populate snapshot with actual values
snapshot = HealthSnapshot(
    equity_value=float(equity) if equity else None,
    drawdown_current=health.get('max_dd_to_date'),
    daily_pnl=float(realized) if realized else None,
    rolling_sharpe=health.get('Sharpe_roll_1d'),
    trade_count=health.get('exec_count_recent'),
    win_rate=health.get('hit_rate_w'),
    turnover=health.get('turnover_bps_day'),
    error_counts=0,  # Track separately
    risk_breaches=0,  # Track separately
)

snapshot_emitter.maybe_emit(snapshot, now=datetime.now(IST))
```

**Verification**:
- Check `logs/1h/health_snapshot/snapshot.jsonl` has populated records
- Check `logs/24h/health_snapshot/snapshot.jsonl` has daily summaries
- Verify only one emission per period boundary

---

## Short-Term Implementations (1-2 days each) 📊

### ST1. Add Prometheus Metrics Emitter
**Effort**: 2 days | **Impact**: CRITICAL | **Type**: Real-Time Monitoring

**What it improves**:
- Real-time dashboards in Grafana
- Instant visibility into bot health
- Historical metric queries (PromQL)
- Alerting via Alertmanager
- Integration with monitoring stack

**Why needed**:
- Current: Zero real-time metrics - must parse logs to see anything
- Logs are batch-processed, metrics are real-time
- Industry standard for microservice monitoring
- Essential for production operations

**Metrics to Implement**:
```python
# Create live_demo/metrics/prometheus_metrics.py
from prometheus_client import Gauge, Counter, Histogram, Summary, start_http_server

# Health Metrics
EQUITY = Gauge('bot_equity_value', 'Current equity value', ['symbol', 'bot_version'])
DRAWDOWN = Gauge('bot_drawdown_current', 'Current drawdown', ['symbol'])
WS_STALENESS = Gauge('bot_ws_staleness_ms', 'WebSocket staleness', ['symbol'])
WS_RECONNECTS = Counter('bot_ws_reconnects_total', 'Total reconnections', ['symbol'])
FUNDING_STALE = Gauge('bot_funding_stale', 'Funding data stale flag', ['symbol'])

# Trading Metrics
TRADE_COUNT = Counter('bot_trades_total', 'Total trades', ['symbol', 'source', 'side'])
TRADE_PNL = Histogram('bot_trade_pnl_bps', 'Trade PnL in bps', ['symbol', 'source'])
POSITION_SIZE = Gauge('bot_position_size', 'Current position size', ['symbol'])
SIGNAL_STRENGTH = Histogram('bot_signal_strength', 'Signal strength', ['symbol', 'source'])

# Execution Metrics
EXEC_LATENCY = Histogram('bot_execution_latency_ms', 'Execution latency', ['symbol', 'order_type'])
ORDER_REJECTIONS = Counter('bot_order_rejections_total', 'Order rejections', ['symbol', 'reason'])
SLIPPAGE = Histogram('bot_slippage_bps', 'Slippage in bps', ['symbol', 'side'])

# Cost Metrics
COST_TOTAL = Histogram('bot_cost_total_bps', 'Total cost in bps', ['symbol'])
COST_FEES = Histogram('bot_cost_fees_bps', 'Fee cost in bps', ['symbol'])
COST_IMPACT = Histogram('bot_cost_impact_bps', 'Impact cost in bps', ['symbol'])

# Model Metrics
PREDICTION_ERROR = Histogram('bot_prediction_error_bps', 'Prediction error', ['symbol'])
CALIBRATION_IN_BAND = Gauge('bot_calibration_in_band_rate', 'In-band rate', ['symbol'])
MODEL_CONFIDENCE = Histogram('bot_model_confidence', 'Model confidence', ['symbol'])

def start_metrics_server(port=8000):
    start_http_server(port)
    print(f"Prometheus metrics exposed at :8000/metrics")

# In main.py initialization
from live_demo.metrics.prometheus_metrics import *
start_metrics_server(port=8000)

# In main loop - update metrics
EQUITY.labels(symbol=sym, bot_version=bot_version).set(equity)
DRAWDOWN.labels(symbol=sym).set(health.get('max_dd_to_date', 0))
WS_STALENESS.labels(symbol=sym).set(health.get('ws_staleness_ms', 0))

if exec_resp.get('status') == 'filled':
    TRADE_COUNT.labels(symbol=sym, source=signal_source, side=exec_resp['side']).inc()
    EXEC_LATENCY.labels(symbol=sym, order_type=exec_resp['order_type']).observe(latency_ms)
```

**Docker Compose Addition**:
```yaml
# Add to monitoring stack
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

**Prometheus Config** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'metastackerbandit'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
```

**Verification**:
- Curl `http://localhost:8000/metrics` and see Prometheus text format
- Open Prometheus UI at `http://localhost:9090` and query `bot_equity_value`
- Create Grafana dashboard importing metrics

---

### ST2. Add Trade Lifecycle Tracking
**Effort**: 2 days | **Impact**: CRITICAL | **Type**: Analytics Enhancement

**What it improves**:
- End-to-end trade analysis
- Signal source attribution
- Duration and timing analysis
- Slippage measurement
- Signal decay tracking
- Win/loss categorization

**Why needed**:
- Current: Can't link entry → exit → PnL across events
- No way to attribute PnL to specific signal sources
- Can't analyze how long signals remain profitable
- No systematic slippage tracking
- Essential for strategy evaluation

**Implementation**:
```python
# Create live_demo/tracking/trade_lifecycle.py
import uuid
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

@dataclass
class TradeLifecycle:
    trade_id: str
    symbol: str
    
    # Entry
    entry_ts_ist: str
    entry_bar_id: int
    entry_px: float
    entry_qty: float
    entry_side: str  # BUY/SELL
    entry_signal_source: str  # pros/amateurs/model_meta/model_bma
    entry_cohort_pros: float
    entry_cohort_amateurs: float
    entry_cohort_mood: float
    entry_pred_bps: float
    entry_decision_px: float  # Price at decision time
    
    # Exit
    exit_ts_ist: Optional[str] = None
    exit_bar_id: Optional[int] = None
    exit_px: Optional[float] = None
    exit_qty: Optional[float] = None
    exit_side: Optional[str] = None
    exit_reason: Optional[str] = None  # stop_loss/take_profit/signal_flip/time_limit/risk_limit
    exit_signal_source: Optional[str] = None
    
    # Metrics
    duration_bars: Optional[int] = None
    duration_seconds: Optional[float] = None
    realized_pnl_usd: Optional[float] = None
    realized_pnl_bps: Optional[float] = None
    costs_total_usd: Optional[float] = None
    costs_total_bps: Optional[float] = None
    net_pnl_usd: Optional[float] = None
    net_pnl_bps: Optional[float] = None
    
    # Slippage
    slippage_entry_bps: Optional[float] = None  # (fill_px - decision_px) / decision_px * 10000
    slippage_exit_bps: Optional[float] = None
    
    # Analysis
    prediction_error_bps: Optional[float] = None  # Actual move vs predicted
    signal_strength_entry: Optional[float] = None
    signal_strength_exit: Optional[float] = None
    signal_decay: Optional[float] = None  # strength_exit / strength_entry
    
    # Metadata
    strategy_id: str = "ensemble_1_0"
    schema_version: str = "v1"


class TradeTracker:
    def __init__(self, emitter):
        self.emitter = emitter
        self.active_trades: Dict[str, TradeLifecycle] = {}  # symbol -> trade
    
    def open_trade(self, symbol: str, entry_data: Dict[str, Any]) -> str:
        trade_id = str(uuid.uuid4())
        
        trade = TradeLifecycle(
            trade_id=trade_id,
            symbol=symbol,
            entry_ts_ist=datetime.now(IST).isoformat(),
            entry_bar_id=entry_data['bar_id'],
            entry_px=entry_data['fill_px'],
            entry_qty=entry_data['qty'],
            entry_side=entry_data['side'],
            entry_signal_source=entry_data['signal_source'],
            entry_cohort_pros=entry_data['cohort']['pros'],
            entry_cohort_amateurs=entry_data['cohort']['amateurs'],
            entry_cohort_mood=entry_data['cohort']['mood'],
            entry_pred_bps=entry_data['pred_bps'],
            entry_decision_px=entry_data['decision_px'],
            slippage_entry_bps=(entry_data['fill_px'] - entry_data['decision_px']) / entry_data['decision_px'] * 10000,
            signal_strength_entry=entry_data.get('signal_strength', 0.0),
        )
        
        self.active_trades[symbol] = trade
        return trade_id
    
    def close_trade(self, symbol: str, exit_data: Dict[str, Any]):
        trade = self.active_trades.get(symbol)
        if not trade:
            return
        
        entry_ts = datetime.fromisoformat(trade.entry_ts_ist)
        exit_ts = datetime.now(IST)
        
        trade.exit_ts_ist = exit_ts.isoformat()
        trade.exit_bar_id = exit_data['bar_id']
        trade.exit_px = exit_data['fill_px']
        trade.exit_qty = exit_data['qty']
        trade.exit_side = exit_data['side']
        trade.exit_reason = exit_data['reason']
        trade.exit_signal_source = exit_data.get('signal_source')
        
        trade.duration_bars = exit_data['bar_id'] - trade.entry_bar_id
        trade.duration_seconds = (exit_ts - entry_ts).total_seconds()
        
        # Calculate PnL
        direction = 1 if trade.entry_side == 'BUY' else -1
        price_move = (trade.exit_px - trade.entry_px) / trade.entry_px
        trade.realized_pnl_bps = direction * price_move * 10000
        trade.realized_pnl_usd = direction * price_move * (trade.entry_px * trade.entry_qty)
        
        trade.costs_total_usd = exit_data.get('costs_usd', 0.0)
        trade.costs_total_bps = exit_data.get('costs_bps', 0.0)
        trade.net_pnl_usd = trade.realized_pnl_usd - trade.costs_total_usd
        trade.net_pnl_bps = trade.realized_pnl_bps - trade.costs_total_bps
        
        # Slippage
        trade.slippage_exit_bps = (exit_data['fill_px'] - exit_data['decision_px']) / exit_data['decision_px'] * 10000
        
        # Signal analysis
        trade.prediction_error_bps = trade.realized_pnl_bps - trade.entry_pred_bps
        trade.signal_strength_exit = exit_data.get('signal_strength', 0.0)
        trade.signal_decay = trade.signal_strength_exit / trade.signal_strength_entry if trade.signal_strength_entry else None
        
        # Emit to logs
        self.emitter.emit_trade_lifecycle(asdict(trade))
        
        # Remove from active
        del self.active_trades[symbol]

# In main.py execution logic
from live_demo.tracking.trade_lifecycle import TradeTracker

tracker = TradeTracker(emitter)

# On entry fill
if exec_resp.get('status') == 'filled' and position_was_flat:
    tracker.open_trade(sym, {
        'bar_id': bar_count,
        'fill_px': exec_resp['price'],
        'qty': exec_resp['qty'],
        'side': exec_resp['side'],
        'signal_source': decision['details']['chosen'],
        'cohort': cohort,
        'pred_bps': decision['details']['pred_bma_bps'],
        'decision_px': current_market_price,
        'signal_strength': decision['alpha'],
    })

# On exit fill
if exec_resp.get('status') == 'filled' and position_now_flat:
    tracker.close_trade(sym, {
        'bar_id': bar_count,
        'fill_px': exec_resp['price'],
        'qty': exec_resp['qty'],
        'side': exec_resp['side'],
        'reason': exit_reason,  # from decision logic
        'signal_source': decision['details']['chosen'],
        'costs_usd': costs_payload['cost_usd'],
        'costs_bps': costs_payload['cost_bps_total'],
        'decision_px': current_market_price,
        'signal_strength': decision['alpha'],
    })
```

**New Event Stream**: `trade_lifecycle.jsonl`

**Verification**:
- Execute round-trip trade (buy then sell)
- Check trade_lifecycle.jsonl has complete entry+exit record
- Verify PnL, duration, slippage calculations correct
- Check signal_decay shows degradation over time

---

### ST3. Add Model Latency Tracking
**Effort**: 1 day | **Impact**: MEDIUM | **Type**: Performance Monitoring

**What it improves**:
- Identifies performance bottlenecks
- Tracks model inference speed
- Detects degradation over time
- Supports capacity planning

**Why needed**:
- Current: No visibility into pipeline timing
- Can't tell if slowness is in features, model, or decision logic
- Important for low-latency trading
- Helps optimize critical path

**Implementation**:
```python
# In main.py around signal generation
import time

latency_profile = {}

# Feature calculation
t0 = time.perf_counter()
x = compute_features(...)
latency_profile['feature_calc_ms'] = (time.perf_counter() - t0) * 1000

# Model inference
t0 = time.perf_counter()
model_out = model.predict(x)
latency_profile['model_inference_ms'] = (time.perf_counter() - t0) * 1000

# Decision logic
t0 = time.perf_counter()
decision = make_decision(model_out, cohort, overlay)
latency_profile['decision_logic_ms'] = (time.perf_counter() - t0) * 1000

# Risk check
t0 = time.perf_counter()
risk_ok = risk.check_limits(decision)
latency_profile['risk_check_ms'] = (time.perf_counter() - t0) * 1000

# Execution
if decision['dir'] != 0:
    t0 = time.perf_counter()
    exec_resp = risk.execute(...)
    latency_profile['execution_ms'] = (time.perf_counter() - t0) * 1000

latency_profile['total_latency_ms'] = sum(latency_profile.values())

# Add to signals.jsonl
emitter.emit_signals(ts=ts, symbol=sym, features=x, model_out=model_out, 
                     decision=decision, cohort=cohort, latency=latency_profile)

# Also emit to Prometheus
if 'model_inference_ms' in latency_profile:
    MODEL_INFERENCE_LATENCY.labels(symbol=sym).observe(latency_profile['model_inference_ms'])
```

**Verification**:
- Check signals.jsonl has latency dict
- Verify sum of components equals total_latency_ms
- Query Prometheus for p99 model inference latency
- Identify slowest component

---

## Medium-Term Implementations (2-3 days each) 🔧

### MT1. Add Slippage Measurement System
**Effort**: 2 days | **Impact**: HIGH | **Type**: Execution Quality

**What it improves**:
- Quantifies execution quality
- Separates slippage from fees/impact
- Identifies problematic order types
- Supports broker comparison

**Why needed**:
- Current: `slip_bps` always null in costs.jsonl
- Can't distinguish between model error and execution error
- Essential for execution analysis
- Helps optimize order routing

**Implementation**:
```python
# In risk_and_exec.py
class SlippageTracker:
    def __init__(self):
        self.decision_prices = {}  # order_id -> decision_px
    
    def record_decision(self, order_id: str, decision_px: float):
        self.decision_prices[order_id] = decision_px
    
    def calculate_slippage(self, order_id: str, fill_px: float, side: str) -> dict:
        decision_px = self.decision_prices.get(order_id)
        if not decision_px:
            return {'slip_bps': None, 'slip_usd': None}
        
        # Positive slippage = worse than expected
        if side == 'BUY':
            slip_bps = (fill_px - decision_px) / decision_px * 10000
        else:  # SELL
            slip_bps = (decision_px - fill_px) / decision_px * 10000
        
        return {
            'decision_px': decision_px,
            'fill_px': fill_px,
            'slip_bps': slip_bps,
            'slip_usd': slip_bps / 10000 * fill_px * qty,
        }

slippage_tracker = SlippageTracker()

# At decision time
order_id = generate_order_id()
slippage_tracker.record_decision(order_id, current_market_price)

# At fill time
slippage = slippage_tracker.calculate_slippage(order_id, exec_resp['price'], exec_resp['side'])
exec_resp.update(slippage)

# Emit with execution log
log_router.emit_execution(ts=ts, asset=sym, exec_resp=exec_resp, risk_state=risk_state)
```

**Verification**:
- Execute trades with limit orders slightly away from mid
- Check execution.jsonl has non-null slip_bps
- Verify positive slippage for buys above mid, sells below mid
- Calculate average slippage across order types

---

### MT2. Add Intraday PnL Curve
**Effort**: 1 day | **Impact**: MEDIUM | **Type**: Analytics

**What it improves**:
- High-frequency equity tracking
- Intraday pattern detection
- Drawdown timing analysis
- Strategy debugging

**Why needed**:
- Current: Only snapshots at 1h/24h boundaries
- Can't see intraday equity swings
- Miss important intraday patterns
- Need for curve-fitting strategies

**Implementation**:
```python
# Create new emitter method
def emit_equity_curve(self, record: Dict[str, Any]):
    """Emit equity at every trade and hourly"""
    record = self._add_metadata(record, "equity_curve")
    if self.config.enable_async:
        self._queues["equity_curve"].put(record)
    else:
        self._write_single_with_retry("equity_curve", record)

# In main.py - emit on every equity change
last_equity_emission = None

if (abs(equity - (last_equity_emission or equity)) > 0.01 or  # $0.01 change
    (time.time() - last_equity_emission_ts > 3600)):  # Hourly heartbeat
    
    emitter.emit_equity_curve({
        'ts_ist': datetime.now(IST).isoformat(),
        'symbol': sym,
        'bar_id': bar_count,
        'equity_value': equity,
        'realized_pnl': realized,
        'unrealized_pnl': unrealized,
        'position_qty': risk.get_position(),
        'position_value': risk.get_position() * current_px,
    })
    
    last_equity_emission = equity
    last_equity_emission_ts = time.time()
```

**New Event Stream**: `equity_curve.jsonl`

**Verification**:
- Execute multiple trades and check equity_curve.jsonl
- Plot equity over time and verify curve is smooth
- Check hourly heartbeats present even with no trading

---

### MT3. Add Feature Staleness Tracking
**Effort**: 1 day | **Impact**: MEDIUM | **Type**: Data Quality

**What it improves**:
- Detects stale/frozen features
- Prevents decisions on old data
- Supports data quality monitoring
- Identifies feed issues

**Why needed**:
- Current: No per-feature timestamps
- Dec 20 logs showed many features at 0.0 - are they stale or truly zero?
- Can't distinguish between calm market and broken feed
- Critical for data quality

**Implementation**:
```python
# In features.py
from datetime import datetime, timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")

class FeatureTracker:
    def __init__(self, staleness_threshold_seconds=300):
        self.last_updates = {}  # feature_name -> timestamp
        self.threshold = staleness_threshold_seconds
    
    def update(self, feature_name: str, value: Any):
        if value != 0.0 and value is not None:  # Only update if non-zero
            self.last_updates[feature_name] = datetime.now(IST)
    
    def get_stale_features(self) -> list:
        now = datetime.now(IST)
        stale = []
        for name, last_update in self.last_updates.items():
            age = (now - last_update).total_seconds()
            if age > self.threshold:
                stale.append({'name': name, 'age_seconds': age})
        return stale
    
    def get_timestamps(self) -> dict:
        return {
            name: ts.isoformat()
            for name, ts in self.last_updates.items()
        }

feature_tracker = FeatureTracker(staleness_threshold_seconds=300)

# In feature calculation
for feature_name, value in features.items():
    feature_tracker.update(feature_name, value)

# In feature_log emission
stale_features = feature_tracker.get_stale_features()
feature_log = {
    'ts_ist': datetime.now(IST).isoformat(),
    'bar_id': bar_count,
    'asset': sym,
    **features,
    'feature_timestamps': feature_tracker.get_timestamps(),
    'stale_features': stale_features,
    'staleness_alert': len(stale_features) > 5,  # Alert if >5 stale
}

emitter.emit_feature_log(feature_log)

# Alert if critical
if len(stale_features) > 5:
    slack.send('WARNING', 'Stale Features Detected',
               f'{len(stale_features)} features have not updated in >5 minutes',
               {'Symbol': sym, 'Stale_Count': len(stale_features)})
```

**Verification**:
- Kill feature feed and watch staleness_alert trigger
- Check feature_timestamps shows last update times
- Verify stale_features list includes expected features

---

## Long-Term Enhancements (3+ days each) 🚀

### LT1. Add Regime Transition Event System
**Effort**: 2 days | **Impact**: MEDIUM | **Type**: Market Analysis

**What it improves**:
- Explicit regime change tracking
- Correlates performance with regimes
- Supports regime-dependent strategies
- Identifies regime shift opportunities

**Why needed**:
- Current: Regime in feature_log but transitions not explicit
- Can't easily query "what happened after regime changes"
- Important for understanding strategy behavior
- Enables regime-switching strategies

**Implementation**: Create `regime_transition.jsonl` with transition detection logic

---

### LT2. Add Counterfactual PnL Analysis
**Effort**: 3 days | **Impact**: HIGH | **Type**: Strategy Evaluation

**What it improves**:
- Signal source quality comparison
- Attribution of PnL to signal choices
- Alternative strategy evaluation
- Optimal signal selection

**Why needed**:
- Current: Can't compare "what if we used different signal"
- Don't know if we're choosing the best signal source
- Important for strategy improvement
- Supports model selection

**Implementation**: Calculate hypothetical PnL for each signal source at every decision

---

### LT3. Add Model Explainability (SHAP/Feature Importance)
**Effort**: 4 days | **Impact**: MEDIUM | **Type**: Model Transparency

**What it improves**:
- Understanding why model makes predictions
- Feature importance tracking
- Debugging model behavior
- Regulatory compliance

**Why needed**:
- Current: Black box model decisions
- Can't explain predictions to stakeholders
- Hard to debug model issues
- Required for some regulatory environments

**Implementation**: Integrate SHAP library, compute feature contributions per prediction

---

## Missing Critical Components 🚨

### MC1. **Connection Timeout/Retry Logic**
**Gap**: WebSocket staleness logged but no timeout handling
**Risk**: Bot continues with stale data indefinitely
**Fix**: Add connection timeout (30s), auto-restart on timeout

### MC2. **Position Age Tracking**
**Gap**: No tracking of how long positions are held
**Risk**: Can't detect stuck positions or holding period optimization
**Fix**: Add position_opened_ts to risk state, track duration

### MC3. **Funding Rate Cost Tracking**
**Gap**: Funding costs not tied to positions
**Risk**: Underestimate total trading costs
**Fix**: Add funding_cost_usd to costs.jsonl when positions cross funding windows

### MC4. **Kill Switch / Circuit Breaker**
**Gap**: No automatic shutdown on critical errors
**Risk**: Runaway losses, data corruption
**Fix**: Add kill switch triggered by: equity <9000, 10 rejections in 10 minutes, same_bar_roundtrip

### MC5. **Calibration Auto-Tuning**
**Gap**: Calibration parameters frozen at a=0, b=1
**Risk**: Predictions uncalibrated, poor decisions
**Fix**: Implement online calibration with Bayesian updating

### MC6. **Order Book Depth Logging**
**Gap**: No visibility into liquidity beyond top-of-book
**Risk**: Can't analyze market impact, liquidity issues
**Fix**: Log L2 orderbook snapshots at decision time

### MC7. **Correlation with BTC Price Events**
**Gap**: No external price event logging (e.g., $100k break)
**Risk**: Can't correlate strategy performance with market regimes
**Fix**: Log major price level breaks, volatility spikes

### MC8. **Backup/Recovery System**
**Gap**: No automated log backup or disaster recovery
**Risk**: Data loss on system failure
**Fix**: Add S3/cloud backup, log replication

---

## Implementation Priority Summary

### Week 1 (Quick Wins + Critical)
1. ✅ QW1: Reduce health emission (0.5d)
2. ✅ QW2: Add rejection logging (1d)
3. ✅ QW3: Add Slack alerts (1d)
4. ✅ QW4: Populate snapshots (0.5d)
5. ✅ ST1: Prometheus metrics (2d)
**Total**: 5 days

### Week 2 (Short-Term High Impact)
1. ✅ ST2: Trade lifecycle (2d)
2. ✅ ST3: Latency tracking (1d)
3. ✅ MT1: Slippage measurement (2d)
**Total**: 5 days

### Week 3 (Medium-Term + Missing Critical)
1. ✅ MT2: Intraday PnL curve (1d)
2. ✅ MT3: Feature staleness (1d)
3. ✅ MC1: Connection timeout (1d)
4. ✅ MC4: Kill switch (1d)
5. ✅ MC5: Calibration tuning (1d)
**Total**: 5 days

### Week 4+ (Long-Term Enhancements)
1. LT1: Regime transitions (2d)
2. LT2: Counterfactual PnL (3d)
3. MC6: Order book logging (2d)
4. MC8: Backup system (2d)
**Total**: 9 days

---

## Success Metrics

**After Week 1**:
- ✅ Health log volume reduced by 85%
- ✅ Real-time dashboard showing equity/drawdown/latency
- ✅ Slack alerts for critical issues (no silent failures)
- ✅ Zero null values in snapshot.jsonl

**After Week 2**:
- ✅ Every trade has complete lifecycle record
- ✅ Slippage measured on all executions
- ✅ Latency bottlenecks identified

**After Week 3**:
- ✅ No trades on stale data (staleness detection)
- ✅ Calibration improving over time
- ✅ Kill switch tested and verified
- ✅ Automated connection recovery

**Production Ready**: End of Week 3 ✨
