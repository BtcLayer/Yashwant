# MetaStackerBandit Observability Audit 1.1 (Dec 20, 2025)

**Audit Date**: 2025-12-22 (Asia/Kolkata UTC+5:30)  
**Scope**: Logs & emitters from December 20, 2025 runs + current code state  
**Focus**: Enumerate current observability, propose improvements for health/risk monitoring and LLM-based PnL analysis

---

## 1. Current Observability Map

### 1.1 Event Streams Overview

Based on **AUDIT_EXTRACT_TEMP** (Dec 20, 2025 logs) and **live_demo/emitters/production_emitter.py**:

| Event Type | Status | File Location | Records (Dec 20) | Primary Sinks |
|------------|--------|---------------|------------------|---------------|
| **signals** | ✅ Active | signals.jsonl | 6 records | ProductionEmitter, LogRouter(emitter+llm) |
| **health** | ✅ Active | health.jsonl | 96 records | ProductionEmitter, LogRouter(emitter), HealthSnapshotEmitter |
| **calibration** | ✅ Active | calibration.jsonl | 6 records | ProductionEmitter |
| **order_intent** | ✅ Active | order_intent.jsonl | 6 records | ProductionEmitter |
| **repro** | ✅ Active | repro.jsonl | 6 records | ProductionEmitter |
| **costs** | ✅ Active | costs.jsonl | 147 records | ProductionEmitter, LogRouter(emitter+llm) |
| **feature_log** | ✅ Active | feature_log.jsonl | 6 records | ProductionEmitter |
| **snapshot** | ✅ Active | snapshot.jsonl | 1 record | HealthSnapshotEmitter (1h/24h buckets) |
| **execution** | ⚠️ Defined | - | 0 records | ProductionEmitter (no executions Dec 20) |
| **ensemble** | ⚠️ Defined | - | 0 records | LogRouter(llm) |
| **market** | ⚠️ Defined | - | 0 records | ProductionEmitter (code present, not emitted) |
| **risk** | ⚠️ Defined | - | 0 records | ProductionEmitter (code present, not emitted) |

---

## 2. Detailed Event Schema Analysis

### 2.1 **signals.jsonl** (Decision Signals)

**Key Fields - Health Monitoring**:
- `ts_ist`: IST timestamp for correlation
- `decision.details.eligible`: Which signal sources were eligible (pros/amateurs/model_meta/model_bma)
- `decision.details.chosen`: Actual chosen source (or null if HOLD)
- `decision.dir`: Direction (-1/0/+1)
- `model_out.p_down`, `p_neutral`, `p_up`: Model probabilities
- `model_out.s_model`: Raw model signal
- `decision.details.overlay.confidence`: Multi-timeframe overlay confidence
- `decision.details.overlay.chosen_timeframes`: Active timeframe signals

**Key Fields - Trading/PnL**:
- `decision.alpha`: Position sizing (0.0 for HOLD)
- `decision.details.pred_bma_bps`: BMA prediction in basis points
- `cohort.pros`, `cohort.amateurs`, `cohort.mood`: Liquidation cluster cohort signals
- `features`: Array of 17 feature values (mom_3, mr_ema20, obi_10, spread_bps, rv_1h, etc.)
- `decision.details.signals.S_top`, `S_bot`, `S_mood`: Cluster signal strengths

**Sinks**:
- JSONL: `paper_trading_outputs/logs/signals/date=YYYY-MM-DD/signals.jsonl.gz`
- Metrics: None currently
- Postgres: If enabled via PostgresEmitter
- LLM Router: Compact version via LogRouter

**Primary Use**: Decision audit trail, signal source attribution, model confidence tracking

**Observations (Dec 20)**:
- All 6 decisions were `dir: 0` (HOLD)
- All showed `eligible: {pros: false, amateurs: false, model_meta: false, model_bma: false}`
- Overlay confidence was 0.0-1.0 range
- Predictions ranged from -2649 to +742 bps but didn't trigger trades

---

### 2.2 **health.jsonl** (System Health Metrics)

**Key Fields - Health Monitoring**:
- `ts_ist`: Emission timestamp
- `metrics.recent_bars`: Bar count in observation window
- `metrics.funding_stale`: Boolean flag for stale funding data
- `metrics.ws_queue_drops`: WebSocket queue drops (connection quality)
- `metrics.ws_reconnects`: WebSocket reconnection count
- `metrics.ws_staleness_ms`: Data staleness in milliseconds
- `metrics.exec_count_recent`: Recent execution count
- `metrics.leakage_flag`: Boolean for data leakage detection
- `metrics.same_bar_roundtrip_flag`: Boolean for same-bar roundtrip trades

**Key Fields - Risk/Trading**:
- `metrics.equity`: Current equity value (constant 10000.0 Dec 20)
- `metrics.max_dd_to_date`: Maximum drawdown
- `metrics.Sharpe_roll_1d`, `Sharpe_roll_1w`: Rolling Sharpe ratios (null if insufficient data)
- `metrics.Sortino_1w`: Weekly Sortino ratio
- `metrics.time_in_mkt`: Market exposure percentage
- `metrics.hit_rate_w`: Weekly hit rate
- `metrics.turnover_bps_day`: Daily turnover in basis points
- `metrics.capacity_participation`: ADV participation
- `metrics.ic_drift`: Information coefficient drift
- `metrics.calibration_drift`: Calibration drift metric
- `metrics.in_band_share`: Proportion of predictions within calibration band

**Key Fields - Model Behavior**:
- `metrics.mean_p_down`, `mean_p_up`, `mean_s_model`: Recent model output averages

**Sinks**:
- JSONL: `paper_trading_outputs/logs/health/date=YYYY-MM-DD/health.jsonl.gz`
- HealthSnapshotEmitter: Time-bucketed snapshots (1h/24h)
- Metrics: None currently
- Postgres: If enabled

**Primary Use**: Runtime health monitoring, data quality checks, model stability tracking

**Observations (Dec 20)**:
- 96 health emissions (high frequency, likely every bar)
- Many null values for performance metrics (Sharpe, Sortino, hit_rate_w) - insufficient trading history
- `funding_stale` toggled between true/false - intermittent funding data issues
- All `ws_queue_drops`, `ws_reconnects` were 0 - good connection health
- All `leakage_flag` and `same_bar_roundtrip_flag` were false - no data quality issues detected

---

### 2.3 **calibration.jsonl** (Prediction Calibration)

**Key Fields - Health Monitoring**:
- `ts_ist`: Calibration check timestamp
- `in_band_flag`: Boolean - was prediction within calibration band?
- `band_bps`: Calibration band width in basis points (15.0)
- `band_hit_rate`: Cumulative band hit rate
- `calibration_score`: Overall calibration quality score
- `prediction_accuracy`: Prediction accuracy metric

**Key Fields - Trading/PnL**:
- `pred_raw_bps`: Raw model prediction in basis points
- `pred_cal_bps`: Calibrated prediction in basis points
- `realized_bps`: Actual realized move in basis points
- `prediction_error`: Absolute prediction error in basis points
- `a`, `b`: Calibration transform parameters (both 0.0 Dec 20 - no calibration applied)

**Sinks**:
- JSONL: `paper_trading_outputs/logs/calibration/date=YYYY-MM-DD/calibration.jsonl.gz`

**Primary Use**: Model calibration monitoring, prediction accuracy tracking

**Observations (Dec 20)**:
- All 6 records showed `in_band_flag: false` - predictions consistently outside band
- Calibration parameters frozen at `a: 0.0, b: 1.0` (identity transform)
- Large prediction errors: 607-2649 bps
- All `realized_bps: 0.0` - no realized moves (HOLD positions)
- Suggests calibration system needs tuning or more data

---

### 2.4 **order_intent.jsonl** (Pre-Execution Intent)

**Key Fields - Health Monitoring**:
- `ts_ist`: Intent generation timestamp
- `reason_codes`: Dict of boolean flags explaining HOLD decision
  - `threshold`: Signal strength threshold check
  - `band`: Calibration band check
  - `spread_guard`: Spread width guard
  - `volatility_ok`: Volatility regime check
  - `liquidity_ok`: Liquidity sufficiency check
  - `risk_ok`: Risk limit check

**Key Fields - Trading/PnL**:
- `side`: Intended side (BUY/SELL/HOLD)
- `intent_qty`: Intended quantity (0.0 for HOLD)
- `intent_notional`: Intended notional value
- `signal_strength`: Aggregated signal strength
- `model_confidence`: Model confidence score
- `risk_score`: Risk assessment score
- `market_conditions`: Dict with spread_bps, volatility, volume, funding_rate

**Sinks**:
- JSONL: `paper_trading_outputs/logs/order_intent/date=YYYY-MM-DD/order_intent.jsonl.gz`

**Primary Use**: Trade decision audit, guard rail effectiveness, market condition correlation

**Observations (Dec 20)**:
- All 6 intents were `side: HOLD`
- Primary guard failures: `spread_guard: true` (spread too wide), `threshold: false`, `band: false`, `volatility_ok: false`
- `liquidity_ok: true` and `risk_ok: true` consistently passed
- `spread_bps` varied widely: 75-949 bps
- Suggests spread guard is the primary blocker for trades

---

### 2.5 **repro.jsonl** (Reproducibility Metadata)

**Key Fields - Health Monitoring**:
- `ts_ist`: Record creation timestamp
- `repro.git_sha`: Git commit SHA for code version
- `repro.model_version`: Model version identifier (null Dec 20)
- `repro.feature_version`: Feature set version ("v3.2.1")
- `repro.seed`: Random seed for reproducibility (42)

**Key Fields - Trading/PnL**:
- `repro.train_start_ist`, `repro.train_end_ist`: Model training period
- `repro.hyperparams_hash`: Hash of hyperparameters ("99914b93")
- `repro.data_hash`: Hash of training data ("708974dd")
- `repro.adv_method`: ADV calculation method ("rolling_20d")

**Sinks**:
- JSONL: `paper_trading_outputs/logs/repro/date=YYYY-MM-DD/repro.jsonl.gz`

**Primary Use**: Version control, reproducibility audits, model lineage tracking

**Observations (Dec 20)**:
- Git SHA evolved: "1462357" → "57ebe1e" → "abb784c" → "19abd8a" (4 code versions)
- Model training period consistent: 2025-07-01 to 2025-09-30
- Feature version stable at v3.2.1
- Hyperparams and data hashes unchanged

---

### 2.6 **costs.jsonl** (Execution Costs)

**Key Fields - Health Monitoring**:
- `ts_ist`: Cost calculation timestamp
- `costs.rejections`: Order rejection count (if present)
- `costs.event_id`: Unique event identifier for traceability

**Key Fields - Trading/PnL**:
- `costs.trade_notional`: Trade notional value
- `costs.fee_bps`, `costs.fee_usd`: Trading fees
- `costs.slip_bps`, `costs.slip_usd`: Slippage costs (often null)
- `costs.impact_bps`, `costs.impact_usd`: Market impact costs
- `costs.cost_bps_total`, `costs.cost_usd`: Total transaction costs
- `costs.impact_k`: Impact model parameter (0.5)
- `costs.adv_ref`: Reference ADV for impact calculation
- `costs.pnl_attrib`: Dict with alpha/timing/fees/impact/total PnL attribution (if present)

**Sinks**:
- JSONL: `paper_trading_outputs/logs/costs/date=YYYY-MM-DD/costs.jsonl.gz`
- LLM Router: Via LogRouter if enabled

**Primary Use**: Transaction cost analysis, PnL attribution, slippage tracking

**Observations (Dec 20)**:
- 147 cost records (suggests repeated calculations or backtesting)
- Dual format: some have `pnl_attrib` structure, others have flat cost breakdown
- Fee consistently 5.0 bps (50 USD per 10k notional)
- Impact 43.9-54.4 bps (significant)
- Total costs 48.9-59.4 bps per trade
- No `slip_bps` values (slippage not measured)
- ADV varied: ~12.9-13.4 trillion (BTC volume estimates)

---

### 2.7 **feature_log.jsonl** (Feature Engineering Log)

**Key Fields - Health Monitoring**:
- `ts_ist`: Feature calculation timestamp
- `volatility_regime`: Categorized volatility state ("low")
- `liquidity_score`: Liquidity assessment (0.5)
- `regime_bucket`: Combined regime classification ("low_vol_high_vol")

**Key Fields - Trading/PnL**:
- `mom_3`: 3-period momentum
- `mr_ema20`: Mean reversion from 20-period EMA
- `obi_10`: Order book imbalance (10-level)
- `spread_bps`: Bid-ask spread in basis points (75-949)
- `rv_1h`: 1-hour realized volatility
- `funding_delta`: Funding rate change
- `adv20`: 20-day average daily volume
- `volume_ratio`: Current vs. average volume ratio
- `price_change_bps`: Bar price change in basis points

**Sinks**:
- JSONL: `paper_trading_outputs/logs/feature_log/date=YYYY-MM-DD/feature_log.jsonl.gz`

**Primary Use**: Feature distribution monitoring, regime classification tracking, feature staleness detection

**Observations (Dec 20)**:
- Most features consistently 0.0 (mom_3, mr_ema20, obi_10, rv_1h, funding_delta, adv20)
- `spread_bps` was the most variable feature (75-949)
- `volume_ratio` always 1.0
- `volatility_regime` always "low"
- Suggests possible data quality issues or inactive markets during test period

---

### 2.8 **snapshot.jsonl** (Time-Bucketed Health Summary)

**Key Fields - Health Monitoring**:
- `ts_ist`: Snapshot timestamp
- `equity_value`: Current equity (null in sample)
- `drawdown_current`: Current drawdown (null)
- `error_counts`: Cumulative error count (null)
- `risk_breaches`: Risk limit breach count (null)

**Key Fields - Trading/PnL**:
- `daily_pnl`: Daily PnL (null)
- `rolling_sharpe`: Rolling Sharpe ratio (null)
- `trade_count`: Number of trades (null)
- `win_rate`: Win rate percentage (null)
- `turnover`: Portfolio turnover (null)

**Sinks**:
- JSONL: `paper_trading_outputs/logs/{1h,24h}/health_snapshot/snapshot.jsonl`

**Primary Use**: Periodic summary for LLM consumption, time-series analysis

**Observations (Dec 20)**:
- Only 1 record with all null values
- Emitted by HealthSnapshotEmitter when hour/day boundaries cross
- Schema is well-defined but not populated (likely awaiting trading activity)

---

## 3. Event Types Defined But Not Emitted (Dec 20)

### 3.1 **execution** (Trade Fills)
**Expected Fields**:
- `decision_time_ist`, `exec_time_ist`: Timing breakdown
- `bar_id_exec`: Bar identifier
- `side`, `order_type`: Order details
- `limit_px`, `fill_px`, `fill_qty`: Execution prices/quantities
- `slip_bps`: Realized slippage
- `router`: Exchange router (BINANCE/HYPERLIQUID)
- `rejections`, `ioc_ms`: Execution quality metrics

**Reason Not Emitted**: No trades executed Dec 20 (all HOLD decisions)

---

### 3.2 **ensemble** (Model Ensemble Predictions)
**Expected Fields**:
- `pred_stack_bps`: Ensemble prediction in basis points
- `manifest`: Model weights/configuration
- `event_id`: Traceability

**Reason Not Emitted**: LogRouter topic mapping may not include "llm" sink for ensemble

---

### 3.3 **market** (Market Data)
**Expected Fields**:
- Market microstructure data (bid/ask, volume, funding)
- ProductionEmitter has `emit_market_data` method defined

**Reason Not Emitted**: Not called from main.py in current code

---

### 3.4 **risk** (Risk State)
**Expected Fields**:
- Position sizes, utilization, exposure metrics
- ProductionEmitter has `emit_risk` method defined

**Reason Not Emitted**: Risk state logged within execution records instead of separate stream

---

## 4. Emitter Infrastructure

### 4.1 **ProductionLogEmitter** (Primary)
**Location**: `live_demo/emitters/production_emitter.py`

**Features**:
- ✅ Async batch writing with background threads
- ✅ GZIP compression (.jsonl.gz)
- ✅ Date-partitioned directories (date=YYYY-MM-DD)
- ✅ File rotation (100MB size limit, keep last 10 files)
- ✅ Retry logic with exponential backoff (3 attempts)
- ✅ Error logging to separate error files
- ✅ Sampling support (configurable rate, default 1.0)
- ✅ Metadata injection (ts_ist, log_type, emitter_version, sampled flag)

**Configuration**:
```python
EmitterConfig(
    base_dir="paper_trading_outputs/logs",
    max_file_size_mb=100,
    max_files=10,
    compression=True,
    sampling_rate=1.0,
    retry_attempts=3,
    retry_delay=1.0,
    batch_size=100,
    flush_interval=5.0,
    enable_async=True
)
```

**Supported Topics**:
- market, signals, ensemble, risk, execution, costs, health, repro, order_intent, feature_log, calibration

---

### 4.2 **HealthSnapshotEmitter** (Periodic Summaries)
**Location**: `live_demo/emitters/health_snapshot_emitter.py`

**Features**:
- ✅ Time-bucketed snapshots (1h and 24h periods)
- ✅ Only emits when period boundary crossed (avoids duplication)
- ✅ Fixed field order for consistency
- ✅ Type coercion (floats/ints/nulls)
- ✅ Deterministic file paths

**Key Behavior**:
- Maintains `_last_period_keys` dict to track last emission per period
- Writes to separate directories: `logs/1h/health_snapshot/`, `logs/24h/health_snapshot/`

---

### 4.3 **LogRouter** (Multi-Sink Router)
**Location**: `live_demo_24h/ops/log_router.py`, `live_demo_1h/ops/log_router.py`

**Features**:
- ✅ Topic-based sink routing (emitter, llm)
- ✅ Event ID generation for traceability (hash-based)
- ✅ Sanitization before emission
- ✅ Best-effort error handling (doesn't crash bot)

**Topics with LLM Sink** (compact for LLM consumption):
- `ensemble_log`, `execution_log`, `costs_log`, `pnl_equity_log`, `overlay_status`, `alerts`

**Topics with Emitter Sink**:
- `signals`, `executions`, `costs`, `health`

---

### 4.4 **LogEmitter** (Legacy/Simple)
**Location**: `live_demo_24h/ops/log_emitter.py`

**Features**:
- ✅ Simple JSONL append
- ✅ Date partitioning
- ✅ Sanitization (redact sensitive keys, hash identifiers)
- ✅ IST timestamp conversion

**Supported Topics**:
- signals, ensemble, executions, costs, health, hyperliquid

---

## 5. Metrics & External Sinks

### 5.1 Current State
- ❌ **No Prometheus/Metrics Emitter**: Code references exist but not wired up
- ❌ **No PostgreSQL Emitter**: Mentioned in older code but not active
- ❌ **No Slack Alerts**: LogRouter has alert methods but no Slack integration wired
- ⚠️ **CSV/Sheets Logger**: Present in `live_demo/sheets_logger.py` but usage unclear
- ⚠️ **LLM Summary Emitter**: Concept present but not fully implemented

---

## 6. Log Management Strategy

### 6.1 Current Rotation/Retention
**ProductionLogEmitter**:
- Rotation trigger: 100MB file size
- Retention: Last 10 rotated files per topic per day
- Compression: GZIP enabled (reduces size 5-10x)
- Date partitioning: Yes (date=YYYY-MM-DD)

**Example File Path**:
```
paper_trading_outputs/logs/signals/date=2025-12-20/signals.jsonl.gz
paper_trading_outputs/logs/signals/date=2025-12-20/signals_20251220_173045.jsonl.gz
```

### 6.2 Log File Sizes (Dec 20)
```
signals.jsonl       : 0.01 MB (6 records)
health.jsonl        : 0.06 MB (96 records)
calibration.jsonl   : <0.01 MB (6 records)
order_intent.jsonl  : <0.01 MB (6 records)
repro.jsonl         : <0.01 MB (6 records)
costs.jsonl         : 0.05 MB (147 records)
feature_log.jsonl   : <0.01 MB (6 records)
snapshot.jsonl      : <0.01 MB (1 record)
```

**Total for Dec 20**: ~0.13 MB uncompressed, ~0.02 MB compressed (est.)

**Projected Monthly Volume** (assuming 24/7 operation):
- Health (96/day): ~2.9K records/month → ~1.8 MB/month
- Costs (147/day): ~4.4K records/month → ~1.5 MB/month
- Signals (6/day): ~180 records/month → ~0.3 MB/month
- **Total**: ~4 MB/month uncompressed, **<1 MB compressed**

### 6.3 LLM Processability
Current logs are **highly LLM-friendly**:
- ✅ JSONL format (easy streaming)
- ✅ Small monthly volume (<1 MB compressed)
- ✅ Date-partitioned (easy to scope queries)
- ✅ Consistent schemas with `strategy_id`, `schema_version`
- ✅ Event IDs for traceability
- ⚠️ Some redundancy (health emitted every bar)
- ⚠️ Null-heavy records (snapshot.jsonl)

---

## 7. Gaps & Improvement Opportunities

### 7.1 Health & Risk Monitoring Gaps

#### **Critical Gaps**:
1. **No real-time metrics** - No Prometheus/StatsD integration for dashboarding
2. **No alerting** - Slack/email alerts not wired despite LogRouter methods
3. **No connection timeout tracking** - WebSocket staleness logged but no timeouts
4. **No order rejection details** - Rejections counted but reasons not logged
5. **No model latency tracking** - Feature/prediction generation times not recorded
6. **No memory/CPU metrics** - No system resource monitoring
7. **No position age tracking** - No tracking of how long positions held

#### **Minor Gaps**:
8. **Health emitted too frequently** - Every bar (96 times Dec 20) is excessive
9. **Calibration always fails** - `in_band_flag: false` for all 6 records, no alerts
10. **No feature staleness timestamps** - Can't detect which features are stale
11. **No correlation with external events** - No logging of funding rate changes, liquidations
12. **No trade reason codes** - When trades DO happen, no structured reason logging

---

### 7.2 PnL & Strategy Analysis Gaps

#### **Critical Gaps**:
1. **No trade lifecycle tracking** - Entry/exit/duration not linked across events
2. **No realized PnL by source** - Can't attribute PnL to pros/amateurs/model signals
3. **No slippage measurement** - `slip_bps` always null
4. **No intraday PnL curve** - Only equity snapshots at period boundaries
5. **No signal decay analysis** - Can't track how signal strength degrades over time
6. **No alternative cost tracking** - No counterfactual PnL (what if we used different signal?)

#### **Minor Gaps**:
7. **Cohort signals not linked to fills** - Pros/amateurs values not correlated with trade outcomes
8. **Model probabilities not calibrated** - `p_down/p_neutral/p_up` not post-processed
9. **No regime transition events** - Regime changes (low_vol → high_vol) not explicitly logged
10. **No funding arbitrage tracking** - Funding costs not tied to positions
11. **Overlay confidence not explained** - Multi-timeframe overlay decision process opaque
12. **No feature importance tracking** - Can't determine which features drive decisions

---

## 8. Proposed Improvements (Priority Order)

### 8.1 **HIGH PRIORITY** (Implement in 1.1)

#### **H1. Add Real-Time Metrics Emitter**
**What**: Integrate Prometheus/StatsD metrics for dashboarding
**Why**: Enable real-time monitoring without parsing logs
**Fields to Emit**:
- `bot.health.equity_value` (gauge)
- `bot.health.drawdown_current` (gauge)
- `bot.health.ws_staleness_ms` (gauge)
- `bot.health.ws_reconnects` (counter)
- `bot.trades.total` (counter)
- `bot.trades.by_source` (counter, labels: pros/amateurs/model)
- `bot.execution.latency_ms` (histogram)
- `bot.costs.total_bps` (histogram)
- `bot.signals.strength` (histogram, labels: source)
- `bot.calibration.in_band_rate` (gauge)

**Implementation**:
```python
from prometheus_client import Gauge, Counter, Histogram, start_http_server

# In main.py initialization:
EQUITY = Gauge('bot_equity_value', 'Current equity value')
DRAWDOWN = Gauge('bot_drawdown_current', 'Current drawdown')
WS_STALENESS = Gauge('bot_ws_staleness_ms', 'WebSocket data staleness')
TRADE_COUNT = Counter('bot_trades_total', 'Total trades', ['source'])
EXEC_LATENCY = Histogram('bot_execution_latency_ms', 'Execution latency')

start_http_server(8000)  # Expose metrics on :8000/metrics
```

---

#### **H2. Add Slack/Email Alerting**
**What**: Wire up existing LogRouter alert methods to Slack webhook
**Why**: Immediate notification of critical issues
**Triggers**:
- `equity < 9500` (5% drawdown)
- `ws_staleness_ms > 30000` (30s data lag)
- `calibration_drift > 0.1` (calibration degraded)
- `funding_stale: true` for >1 hour
- `same_bar_roundtrip_flag: true` (leakage detection)
- Order rejection count >3 in 1 hour
- Health check missed (no emission in 2x expected interval)

**Implementation**:
```python
import requests

def send_slack_alert(level: str, message: str, fields: dict):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    
    payload = {
        "text": f"[{level}] {message}",
        "attachments": [{
            "color": "danger" if level == "CRITICAL" else "warning",
            "fields": [{"title": k, "value": str(v), "short": True} for k, v in fields.items()]
        }]
    }
    requests.post(webhook_url, json=payload, timeout=5)

# In main.py health check:
if health['metrics']['funding_stale'] and (time.time() - last_funding_ts > 3600):
    send_slack_alert("CRITICAL", "Funding data stale for >1 hour", 
                     {"symbol": sym, "staleness_hours": (time.time() - last_funding_ts)/3600})
```

---

#### **H3. Add Trade Lifecycle Tracking**
**What**: Create `trade_lifecycle.jsonl` event stream linking entry/exit/PnL
**Why**: Enable per-trade analysis and signal attribution
**Fields**:
- `trade_id`: UUID for this trade
- `entry_ts_ist`, `entry_bar_id`, `entry_px`, `entry_qty`
- `entry_signal_source`: Which signal triggered (pros/amateurs/model)
- `entry_cohort`: Cohort values at entry
- `entry_pred_bps`: Prediction at entry
- `exit_ts_ist`, `exit_bar_id`, `exit_px`, `exit_qty`
- `exit_reason`: Why exited (stop_loss/take_profit/signal_flip/time_limit)
- `duration_bars`, `duration_seconds`
- `realized_pnl_usd`, `realized_pnl_bps`
- `costs_total_usd`, `costs_total_bps`
- `net_pnl_usd`, `net_pnl_bps`
- `slippage_entry_bps`, `slippage_exit_bps`
- `prediction_error_bps`: Actual vs predicted
- `signal_decay`: Signal strength at entry vs exit

**Implementation**: Requires state tracking in main.py execution logic

---

#### **H4. Reduce Health Emission Frequency**
**What**: Change from "every bar" to "every N bars" or "on change"
**Why**: Reduce log volume by 10-20x without losing information
**Current**: 96 health emissions/day (every bar assumed)
**Proposed**:
- Emit on startup/shutdown
- Emit on equity change >0.1%
- Emit on funding_stale toggle
- Emit on ws_reconnects increment
- Emit on calibration_drift change >0.01
- Emit every 60 bars (1 hour if 5m bars) as heartbeat

**Implementation**:
```python
_health_emit_every = 60  # Already exists in config
last_equity = None
last_funding_stale = None

# In main loop:
should_emit_health = (
    (bar_count % _health_emit_every) == 0 or
    (last_equity and abs(equity - last_equity) / last_equity > 0.001) or
    (last_funding_stale != health['funding_stale'])
)

if should_emit_health:
    emitter.emit_health(...)
    last_equity = equity
    last_funding_stale = health['funding_stale']
```

---

#### **H5. Add Order Rejection Detail Logging**
**What**: When orders rejected, log reason codes and market state
**Why**: Debug trade execution issues
**Fields to Add to execution.jsonl**:
- `rejection_reason`: Exchange rejection code
- `rejection_message`: Human-readable message
- `market_at_rejection`: {bid, ask, spread_bps, volume}
- `retry_attempt`: Which retry attempt failed

**Implementation**:
```python
# In risk_and_exec.py execution logic:
if exec_resp.get('status') == 'rejected':
    exec_resp['rejection_details'] = {
        'reason': exchange_error_code,
        'message': exchange_error_msg,
        'market_state': {
            'bid': current_bid,
            'ask': current_ask,
            'spread_bps': spread_bps,
            'volume_1m': recent_volume
        },
        'retry_attempt': attempt_num
    }
```

---

### 8.2 **MEDIUM PRIORITY** (Implement in 1.2)

#### **M1. Add Model Latency Tracking**
**What**: Measure and log time for each pipeline stage
**Fields**:
- `feature_calc_ms`: Time to compute features
- `model_inference_ms`: Time for model forward pass
- `decision_logic_ms`: Time for decision/overlay logic
- `risk_check_ms`: Time for risk checks
- `execution_ms`: Time for order submission
- `total_latency_ms`: End-to-end latency

**Emit as**: `latency.jsonl` or add to existing `signals.jsonl`

---

#### **M2. Add Slippage Measurement**
**What**: Calculate realized slippage vs. decision-time prices
**Fields**:
- `decision_px`: Price at decision time
- `order_px`: Limit price submitted
- `fill_px`: Actual fill price
- `slip_vs_decision_bps`: (fill_px - decision_px) / decision_px * 10000
- `slip_vs_limit_bps`: (fill_px - order_px) / order_px * 10000

**Implementation**: Requires storing decision_px in order context

---

#### **M3. Add Intraday PnL Curve**
**What**: Emit equity at finer granularity (every trade, every hour)
**Why**: Enable PnL curve analysis, detect intraday patterns
**Fields**:
- `ts_ist`, `equity_value`, `realized_pnl`, `unrealized_pnl`, `position_qty`

**Emit as**: `equity_curve.jsonl` (separate from snapshot.jsonl)

---

#### **M4. Add Regime Transition Events**
**What**: Emit event when volatility/liquidity regime changes
**Why**: Correlate regime shifts with performance
**Fields**:
- `old_regime`, `new_regime`: {low_vol, high_vol, low_liq, high_liq}
- `transition_reason`: {vol_breakout, vol_collapse, liq_dry_up, liq_return}
- `market_state`: {spread_bps, volume, rv_1h}

**Emit as**: `regime_transition.jsonl`

---

#### **M5. Add Feature Staleness Tracking**
**What**: Add last_update_ts for each feature in feature_log.jsonl
**Why**: Detect which features are stale/unreliable
**Fields to Add**:
- `feature_timestamps`: Dict mapping feature name to last update timestamp
- `stale_features`: List of features >5 minutes old

---

#### **M6. Add Counterfactual PnL Logging**
**What**: Log what PnL would have been with alternative signals
**Why**: Evaluate signal source quality
**Fields**:
- `actual_pnl_bps`: Realized PnL from chosen signal
- `counterfactual_pnl_bps`: Dict {pros, amateurs, model_meta, model_bma} → hypothetical PnL

**Emit as**: Add to `costs.jsonl` or create `attribution.jsonl`

---

### 8.3 **LOW PRIORITY** (Consider for 2.0)

#### **L1. Add Memory/CPU Metrics**
**What**: Log system resource usage
**Fields**: `cpu_percent`, `memory_mb`, `memory_percent`, `open_files`

---

#### **L2. Add External Event Correlation**
**What**: Log funding rate changes, major liquidations from exchange APIs
**Fields**: `funding_rate_change_bps`, `liquidation_volume_1m`

---

#### **L3. Add Model Explainability**
**What**: Log feature importances or SHAP values per decision
**Fields**: `feature_contributions`: Dict {feature_name → impact_on_prediction}

---

#### **L4. Add A/B Testing Framework**
**What**: Support multiple strategy versions running simultaneously
**Fields**: `strategy_variant`, `experiment_id`, `cohort_assignment`

---

## 9. Log Schema Versioning Strategy

### 9.1 Current Versioning
All events include:
- `strategy_id`: "ensemble_1_0"
- `schema_version`: "v1"

### 9.2 Recommended Versioning Strategy
**For Breaking Changes** (field removed, type changed):
- Increment `schema_version`: v1 → v2
- Write to separate file: `signals_v2.jsonl`
- Maintain backward compatibility for 30 days
- Add migration script: `migrate_v1_to_v2.py`

**For Additive Changes** (new fields):
- Keep `schema_version` unchanged
- Add optional fields with defaults
- Document in schema changelog

**For Deprecations**:
- Mark field as `deprecated: true` for 30 days
- Log warning when deprecated field accessed
- Remove after deprecation period

---

## 10. Recommended Monitoring Dashboards

### 10.1 **Health Dashboard** (Grafana + Prometheus)
**Panels**:
1. Equity & Drawdown (time series)
2. WebSocket Staleness (gauge, alert >30s)
3. Reconnect Rate (counter)
4. Health Check Frequency (gauge)
5. Funding Data Staleness (boolean, alert if true)
6. Calibration In-Band Rate (gauge, alert <50%)
7. Error Count (counter)

---

### 10.2 **Trading Dashboard**
**Panels**:
1. Trade Count by Source (pie chart: pros/amateurs/model)
2. Signal Strength Distribution (histogram)
3. Win Rate by Source (bar chart)
4. Average PnL per Trade (bar chart)
5. Cost Breakdown (stacked area: fees/impact/slippage)
6. Order Rejection Rate (gauge, alert >10%)
7. Execution Latency (histogram, p50/p95/p99)

---

### 10.3 **Model Performance Dashboard**
**Panels**:
1. Prediction Error Distribution (histogram)
2. Calibration Drift Over Time (line chart)
3. Model Confidence vs. Outcome (scatter)
4. Feature Staleness (heatmap)
5. Regime Distribution (stacked area)
6. Overlay Confidence (line chart)

---

## 11. Action Items Summary

| Priority | Item | Effort | Impact | Owner |
|----------|------|--------|--------|-------|
| H1 | Add Prometheus metrics | 2 days | High | Backend |
| H2 | Add Slack alerting | 1 day | High | DevOps |
| H3 | Add trade lifecycle tracking | 3 days | High | Strategy |
| H4 | Reduce health emission frequency | 0.5 days | Medium | Backend |
| H5 | Add rejection detail logging | 1 day | Medium | Execution |
| M1 | Add latency tracking | 1 day | Medium | Backend |
| M2 | Add slippage measurement | 2 days | Medium | Execution |
| M3 | Add intraday PnL curve | 1 day | Medium | Analytics |
| M4 | Add regime transition events | 1 day | Low | Strategy |
| M5 | Add feature staleness tracking | 1 day | Low | Features |
| M6 | Add counterfactual PnL | 2 days | Low | Analytics |

**Total Effort (High Priority)**: 7.5 days  
**Total Effort (All)**: 15.5 days

---

## 12. Conclusion

**Current State**: The observability system as of December 20, 2025 is **functional but incomplete**. Logs are well-structured, date-partitioned, and LLM-friendly. The ProductionLogEmitter provides solid infrastructure with rotation, compression, and retry logic.

**Key Strengths**:
- ✅ Comprehensive event schemas
- ✅ JSONL format ideal for LLM processing
- ✅ Good error handling (best-effort, no bot crashes)
- ✅ Event IDs for traceability
- ✅ Reproducibility metadata (git SHA, model version)

**Critical Gaps**:
- ❌ No real-time metrics (Prometheus/StatsD)
- ❌ No alerting (Slack/email)
- ❌ No trade lifecycle linking
- ❌ No slippage measurement
- ❌ Excessive health emission frequency

**Recommendation**: Prioritize H1-H5 (Prometheus metrics, Slack alerts, trade lifecycle, health frequency, rejection logging) for the 1.1 release. These provide maximum ROI for health monitoring and PnL analysis with minimal implementation effort (7.5 days).

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-22T12:00:00+05:30  
**Next Review**: 2025-12-29 (post-1.1 implementation)
