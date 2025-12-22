# MetaStackerBandit - Observability Enhancement Task Breakdown
**Date:** December 20, 2025  
**Based on:** Dec 18-19 Production Audit (58 decisions, 0 trades executed)

---

## 🚨 CONTEXT: Why 0 Trades on Dec 19?

**What Happened:**
- System made 58 trading decisions (models predicted opportunities)
- **ALL 58 rejected** by safety guards (`spread_guard`, `volatility_guard`)
- Market conditions were unsafe (wide spreads, high volatility)

**The Problem:**
- ❌ Can't diagnose rejection patterns (missing `veto_reason_primary`, `guard_details`)
- ❌ Can't track risk budget utilization (missing `daily_risk_remaining_usd`)
- ❌ Can't measure model accuracy drift (missing `prediction_quality` event)
- ❌ Can't link trade entry → exit → PnL (missing `trade_id`, `exit_reason`)

**Impact:** You're flying blind when guards trigger. Need better observability to answer:
- "Why were all trades rejected between 14:00-16:00?"
- "Is the model predicting edge that doesn't exist in live conditions?"
- "How much risk budget did we burn on Dec 18 vs Dec 19?"

---

## 📋 IMMEDIATE WINS (1-2 hours each)

### Task 1: Add Error/Rejection Metrics to Health Event
**What:** Add `error_rate_15m`, `order_reject_rate_1h`, `throttle_events_1h` to `health_snapshot_emit()`

**Why Necessary:**
- You saw 100% rejection on Dec 19 but no summary metric tracking this
- Can't alert "rejection rate >80% for 2 hours" without these fields
- Missing throttle tracking means you can't see if exchange is rate-limiting you

**What to Do:**
```python
# In live_demo/health_monitor.py or wherever health_snapshot_emit() lives
def health_snapshot_emit(self):
    # ... existing fields ...
    
    # NEW: Add rejection rate tracking
    recent_decisions = self.get_decisions_last_60m()  # from order_intent log
    rejected_count = sum(1 for d in recent_decisions if d['decision'] == 'pass')
    
    health_data = {
        # ... existing ...
        "error_rate_15m": self.error_tracker.get_rate(window_min=15),
        "order_reject_rate_1h": rejected_count / len(recent_decisions) if recent_decisions else 0.0,
        "throttle_events_1h": self.throttle_tracker.get_count(window_min=60)
    }
```

**Files to Edit:**
- `live_demo/health_monitor.py` (add fields to HealthSnapshotEmitter)
- `live_demo/state.py` (track rejection counts in bot state)

---

### Task 2: Add Daily Risk Budget Tracking
**What:** Add `daily_risk_remaining_usd`, `daily_loss_usd`, `risk_utilization_pct` to health or sizing_risk_log

**Why Necessary:**
- You have risk budgets but can't see "50% of daily budget burned by 10am"
- Can't compare Dec 18 (normal) vs Dec 19 (high rejection) risk usage
- Missing early warning: "risk budget 80% used with 6 hours left in trading day"

**What to Do:**
```python
# In live_demo/risk_and_exec.py
def emit_sizing_risk_log(self):
    daily_budget_usd = self.config.get("daily_loss_limit_usd", 1000.0)
    daily_loss_so_far = self.get_todays_realized_loss()  # from pnl_equity_log
    
    risk_data = {
        # ... existing ...
        "daily_risk_remaining_usd": max(0, daily_budget_usd - daily_loss_so_far),
        "daily_loss_usd": daily_loss_so_far,
        "risk_utilization_pct": (daily_loss_so_far / daily_budget_usd) * 100 if daily_budget_usd > 0 else 0.0
    }
```

**Files to Edit:**
- `live_demo/risk_and_exec.py` (add to sizing_risk_log emitter)
- `live_demo/pnl_attribution.py` (helper function to sum daily losses)

---

### Task 3: Standardize Veto Reason Fields in order_intent
**What:** Add `veto_reason_primary`, `veto_reason_secondary`, `guard_details` to every order_intent emission

**Why Necessary:**
- **Critical for Dec 19 diagnosis:** All 58 rejections show `decision: pass` but no structured reason
- Can't query "show me all spread_guard rejections grouped by hour"
- Missing values like `{"spread_guard": {"spread_bps": 12.5, "threshold_bps": 8.0}}`

**What to Do:**
```python
# In live_demo/decision.py or risk_and_exec.py where order_intent is emitted
def emit_order_intent(self, symbol, signal, decision, veto_list):
    # Parse veto_list into structured reasons
    primary_veto = veto_list[0] if veto_list else None
    secondary_veto = veto_list[1] if len(veto_list) > 1 else None
    
    # Extract guard details from veto context
    guard_details = {}
    for veto in veto_list:
        if veto['guard'] == 'spread_guard':
            guard_details['spread_guard'] = {
                "spread_bps": veto.get('spread_bps'),
                "threshold_bps": veto.get('threshold_bps')
            }
        elif veto['guard'] == 'volatility_guard':
            guard_details['volatility_guard'] = {
                "vol_5m": veto.get('vol_5m'),
                "threshold": veto.get('threshold')
            }
    
    intent_data = {
        # ... existing ...
        "veto_reason_primary": primary_veto['guard'] if primary_veto else None,
        "veto_reason_secondary": secondary_veto['guard'] if secondary_veto else None,
        "guard_details": guard_details
    }
```

**Files to Edit:**
- `live_demo/decision.py` (add to order_intent emission)
- `live_demo/risk_and_exec.py` (pass guard threshold values into veto_list)

---

### Task 4: Add Trade Lifecycle Fields to Execution Log
**What:** Add `exit_reason`, `trade_id`, `is_entry`, `is_exit`, `position_before`, `position_after` to execution events

**Why Necessary:**
- Can't link entry → exit → PnL (missing `trade_id`)
- Can't answer "why did we exit this trade?" (missing `exit_reason`)
- Can't reconstruct position over time (missing `position_before/after`)

**What to Do:**
```python
# In live_demo/risk_and_exec.py or wherever execution is logged
def emit_execution(self, fill_data, trade_context):
    # Generate trade_id when opening new position
    if trade_context['is_entry']:
        trade_id = f"{fill_data['symbol']}_{int(time.time())}"
    else:
        trade_id = trade_context.get('open_trade_id')  # link to entry
    
    exec_data = {
        # ... existing fill data ...
        "trade_id": trade_id,
        "is_entry": trade_context['is_entry'],
        "is_exit": trade_context['is_exit'],
        "position_before": trade_context['position_before'],
        "position_after": trade_context['position_after'],
        "exit_reason": trade_context.get('exit_reason') if trade_context['is_exit'] else None
        # exit_reason examples: "take_profit", "stop_loss", "signal_reversal", "time_exit", "risk_limit"
    }
```

**Files to Edit:**
- `live_demo/risk_and_exec.py` (add fields to execution log)
- `live_demo/execution_tracker.py` (track open trades with trade_id)
- `live_demo/state.py` (store position_before/after in bot state)

---

### Task 5: Fix ws_staleness_ms and Add Data Freshness Metrics
**What:** Populate `ws_staleness_ms` (currently always 0.0), add `funding_staleness_sec`, `market_data_gap_max_ms_1h`

**Why Necessary:**
- Stale data = bad trades. You can't detect "haven't received funding update in 90 seconds"
- Missing "max gap between orderbook updates" means you don't know if data stream froze
- Critical for Dec 19: Were rejections due to stale/frozen market data?

**What to Do:**
```python
# In live_demo/health_monitor.py
def calculate_data_staleness(self):
    now = time.time()
    
    # Websocket staleness (last orderbook update)
    last_ws_update = self.market_data.last_orderbook_timestamp  # from hyperliquid_listener
    ws_staleness_ms = (now - last_ws_update) * 1000 if last_ws_update else None
    
    # Funding rate staleness
    last_funding_update = self.market_data.last_funding_timestamp
    funding_staleness_sec = now - last_funding_update if last_funding_update else None
    
    # Max gap in last hour (from market_ingest_log)
    gaps = self.get_orderbook_gaps_last_hour()
    market_data_gap_max_ms_1h = max(gaps) if gaps else 0.0
    
    return {
        "ws_staleness_ms": ws_staleness_ms,
        "funding_staleness_sec": funding_staleness_sec,
        "market_data_gap_max_ms_1h": market_data_gap_max_ms_1h
    }
```

**Files to Edit:**
- `live_demo/health_monitor.py` (fix staleness calculation)
- `live_demo/hyperliquid_listener.py` (track `last_orderbook_timestamp`, `last_funding_timestamp`)
- `live_demo/market_data.py` (expose timestamps to health monitor)

---

## 🎯 HIGH-VALUE ENHANCEMENTS (3-6 hours each)

### Task 6: Build trade_summary.jsonl Aggregator
**What:** Script to parse execution + costs logs → produce per-trade summary with PnL, duration, slippage

**Why Necessary:**
- No unified view of "Trade #5: entered at $43,210, exited at $43,450, PnL=$240, duration=47min"
- Can't measure "average holding time" or "win rate by timeframe"
- Can't diagnose "why are 1h trades underperforming 12h trades?"

**What to Do:**
```python
# Create scripts/build_trade_summary.py
import json
from pathlib import Path
from collections import defaultdict

def link_trades(executions, costs):
    """Link entry → exit using trade_id (from Task 4)"""
    trades = defaultdict(dict)
    
    for exec in executions:
        trade_id = exec.get('trade_id')
        if exec['is_entry']:
            trades[trade_id]['entry'] = exec
        elif exec['is_exit']:
            trades[trade_id]['exit'] = exec
    
    # Add costs/fees
    for cost in costs:
        trade_id = cost.get('trade_id')  # need to add this to costs log
        if trade_id in trades:
            trades[trade_id]['fees'] = cost
    
    # Compute summary
    summaries = []
    for trade_id, trade_data in trades.items():
        if 'entry' in trade_data and 'exit' in trade_data:
            entry = trade_data['entry']
            exit = trade_data['exit']
            
            pnl_usd = (exit['fill_price'] - entry['fill_price']) * entry['fill_size'] * (1 if entry['side'] == 'buy' else -1)
            duration_sec = exit['timestamp'] - entry['timestamp']
            
            summaries.append({
                "trade_id": trade_id,
                "symbol": entry['symbol'],
                "timeframe": entry.get('timeframe'),
                "entry_time": entry['timestamp'],
                "entry_price": entry['fill_price'],
                "exit_time": exit['timestamp'],
                "exit_price": exit['fill_price'],
                "exit_reason": exit.get('exit_reason'),
                "size": entry['fill_size'],
                "pnl_usd": pnl_usd,
                "duration_sec": duration_sec,
                "fees_usd": trade_data.get('fees', {}).get('total_fees_usd', 0.0),
                "net_pnl_usd": pnl_usd - trade_data.get('fees', {}).get('total_fees_usd', 0.0)
            })
    
    return summaries

# Run on paper_trading_outputs/*/logs/*.jsonl
# Save to paper_trading_outputs/trade_summary.jsonl
```

**Files to Edit:**
- Create `scripts/build_trade_summary.py` (new aggregator script)
- Modify `live_demo/costs.py` to add `trade_id` field (links to execution)

---

### Task 7: Build session_summary.jsonl with Rejection Breakdown
**What:** Script to parse order_intent logs → produce hourly rejection breakdown by guard type

**Why Necessary:**
- **Answers Dec 19 mystery:** "14:00-16:00 had 30 rejections, 28 were spread_guard, 2 were volatility_guard"
- Can't spot patterns: "rejection rate spikes every Monday 9-11am" without this
- Can't optimize guards: "spread_guard rejects 90% of good signals, tune threshold?"

**What to Do:**
```python
# Create scripts/build_session_summary.py
import json
from datetime import datetime, timedelta
from collections import defaultdict

def hourly_rejection_breakdown(order_intents):
    """Group by hour, count rejections by guard"""
    hourly = defaultdict(lambda: {
        'total_decisions': 0,
        'total_rejections': 0,
        'rejections_by_guard': defaultdict(int)
    })
    
    for intent in order_intents:
        hour = datetime.fromtimestamp(intent['timestamp']).strftime('%Y-%m-%d %H:00')
        
        hourly[hour]['total_decisions'] += 1
        
        if intent['decision'] == 'pass':
            hourly[hour]['total_rejections'] += 1
            primary = intent.get('veto_reason_primary')
            if primary:
                hourly[hour]['rejections_by_guard'][primary] += 1
    
    # Convert to list with rejection_rate
    summaries = []
    for hour, data in sorted(hourly.items()):
        summaries.append({
            "hour": hour,
            "total_decisions": data['total_decisions'],
            "total_rejections": data['total_rejections'],
            "rejection_rate": data['total_rejections'] / data['total_decisions'] if data['total_decisions'] > 0 else 0,
            "rejections_by_guard": dict(data['rejections_by_guard'])
        })
    
    return summaries

# Run on paper_trading_outputs/*/logs/order_intent_*.jsonl
# Save to paper_trading_outputs/session_summary.jsonl
```

**Files to Edit:**
- Create `scripts/build_session_summary.py` (new aggregator script)
- Requires Task 3 (veto_reason_primary) to be completed first

---

### Task 8: Add Backtest-Aligned Prediction Fields to Signals
**What:** Add `cluster_width_bps`, `edge_bps_at_entry`, `regime_confidence` to signal events

**Why Necessary:**
- Backtest uses these fields, but live logs don't emit them → can't compare backtest vs live
- Can't answer "did the model see high confidence on Dec 19 but guards blocked it?"
- Can't validate "live edge_bps matches backtest" → might be data quality issue

**What to Do:**
```python
# In live_demo/overlay_signal_generator.py or cohort_signals.py
def emit_signal(self, symbol, prediction, features):
    # Extract backtest-aligned fields
    cluster_width_bps = features.get('liq_cluster_width_bps', 0.0)
    edge_bps = prediction.get('expected_edge_bps', 0.0)  # from model output
    regime_confidence = self.regime_detector.get_confidence()  # from market regime model
    
    signal_data = {
        # ... existing ...
        "cluster_width_bps": cluster_width_bps,
        "edge_bps_at_entry": edge_bps,
        "regime_confidence": regime_confidence,
        "pred_direction": prediction['direction'],  # already exists
        "pred_magnitude_bps": prediction['magnitude_bps']  # already exists
    }
```

**Files to Edit:**
- `live_demo/overlay_signal_generator.py` (add fields to signal emission)
- `live_demo/features.py` (ensure `liq_cluster_width_bps` is computed)
- `live_demo/cohort_signals.py` (add regime_confidence calculation)

---

### Task 9: Link Calibration Predictions to Execution Outcomes
**What:** Add `pred_cal_bps_at_entry`, `in_band_at_entry`, `calibration_timestamp` to execution log

**Why Necessary:**
- Can't validate "model predicted +8 bps, calibration adjusted to +5 bps, actual PnL was +4 bps"
- Can't measure "are calibrated predictions more accurate than raw predictions?"
- Missing link: signal → calibration → execution → PnL (need to connect all 4)

**What to Do:**
```python
# In live_demo/risk_and_exec.py
def emit_execution(self, fill_data, trade_context):
    # Get calibration data from most recent calibration event (within last 5 seconds)
    cal_data = self.calibration_tracker.get_latest(symbol=fill_data['symbol'], max_age_sec=5)
    
    exec_data = {
        # ... existing ...
        "pred_cal_bps_at_entry": cal_data.get('calibrated_pred_bps') if cal_data else None,
        "in_band_at_entry": cal_data.get('in_band') if cal_data else None,
        "calibration_timestamp": cal_data.get('timestamp') if cal_data else None,
        "raw_pred_bps": trade_context.get('raw_pred_bps')  # from signal
    }
```

**Files to Edit:**
- `live_demo/risk_and_exec.py` (add calibration fields to execution)
- `live_demo/calibration_enhancer.py` (expose latest calibration via tracker)
- `live_demo/state.py` (cache recent calibration events for quick lookup)

---

### Task 10: Implement prediction_quality Event for Model Drift
**What:** New event type that tracks IC (information coefficient), out-of-band rate, prediction bias over rolling windows

**Why Necessary:**
- Can't detect "model IC dropped from 0.35 to 0.05 over last 7 days" (model degradation)
- Can't spot "calibration out-of-band rate went from 20% to 60%" (distribution shift)
- Can't catch "model is biased +2 bps over last 100 predictions" (systemic error)

**What to Do:**
```python
# Create live_demo/prediction_quality_tracker.py
class PredictionQualityTracker:
    def __init__(self):
        self.predictions = []  # Rolling buffer of last 200 predictions
        
    def add_prediction(self, pred_bps, actual_pnl_bps, in_band, timestamp):
        self.predictions.append({
            'pred': pred_bps,
            'actual': actual_pnl_bps,
            'in_band': in_band,
            'timestamp': timestamp
        })
        if len(self.predictions) > 200:
            self.predictions.pop(0)
    
    def compute_quality_metrics(self):
        if len(self.predictions) < 30:
            return None  # Not enough data
        
        # Information Coefficient (correlation between pred and actual)
        preds = [p['pred'] for p in self.predictions]
        actuals = [p['actual'] for p in self.predictions]
        ic = np.corrcoef(preds, actuals)[0, 1]
        
        # Out-of-band rate
        out_of_band_count = sum(1 for p in self.predictions if not p['in_band'])
        out_of_band_rate = out_of_band_count / len(self.predictions)
        
        # Prediction bias (mean error)
        errors = [p['pred'] - p['actual'] for p in self.predictions]
        bias_bps = np.mean(errors)
        
        return {
            "timestamp": time.time(),
            "event_type": "prediction_quality",
            "window_size": len(self.predictions),
            "ic": ic,
            "out_of_band_rate": out_of_band_rate,
            "prediction_bias_bps": bias_bps,
            "rmse_bps": np.sqrt(np.mean([e**2 for e in errors]))
        }

# Emit every 50 executions or hourly
```

**Files to Edit:**
- Create `live_demo/prediction_quality_tracker.py` (new module)
- `live_demo/risk_and_exec.py` (call tracker.add_prediction after each execution)
- `live_demo/main.py` (initialize tracker, emit hourly)

---

## 🏗️ INFRASTRUCTURE UPGRADES (8+ hours each)

### Task 11: Optimize hyperliquid_fills Log Sampling
**What:** Reduce hyperliquid_fills from 692 KB/day to ~350 KB/day by sampling non-critical fills

**Why Necessary:**
- 692 KB/day = 253 MB/year for ONE stream (expensive storage)
- Most fills (90%) are small trades not relevant to your strategy
- Only need full fidelity for liquidations >$100k, your own fills, and anomaly detection

**What to Do:**
```python
# In live_demo/hyperliquid_listener.py
def should_log_fill(self, fill):
    """Sample fills intelligently"""
    # Always log: your own fills, large liquidations, unusual trades
    if fill['user'] == self.my_address:
        return True
    if fill['liquidation'] and fill['size_usd'] > 100_000:
        return True
    if fill.get('is_anomaly'):  # flag from anomaly detector
        return True
    
    # Sample 50% of other fills randomly
    return random.random() < 0.5

def on_fill_received(self, fill_data):
    if self.should_log_fill(fill_data):
        self.emitter.emit_hyperliquid_fill(fill_data)
```

**Files to Edit:**
- `live_demo/hyperliquid_listener.py` (add sampling logic)
- `live_demo/config.json` (add `hyperliquid_fills_sample_rate: 0.5`)

---

### Task 12: Implement 5-Minute Health Snapshot Emitter
**What:** Force explicit health snapshots every 5 minutes (currently only on-change)

**Why Necessary:**
- Real-time dashboards need regular heartbeat (can't rely on "only when health changes")
- Can't build "show me health status every 5 minutes for last 24 hours" without regular snapshots
- Missing data during quiet periods (no events = no health logs)

**What to Do:**
```python
# In live_demo/health_monitor.py or main.py
def start_health_snapshot_timer(self):
    """Emit health snapshot every 5 minutes regardless of changes"""
    def emit_periodic_snapshot():
        while True:
            time.sleep(300)  # 5 minutes
            health_data = self.health_monitor.get_current_health()
            health_data['snapshot_trigger'] = 'periodic_5m'  # vs 'on_change'
            self.emitter.emit_health_snapshot(health_data)
    
    # Run in background thread
    thread = threading.Thread(target=emit_periodic_snapshot, daemon=True)
    thread.start()
```

**Files to Edit:**
- `live_demo/health_monitor.py` (add periodic snapshot timer)
- `live_demo/main.py` (start timer on bot initialization)

---

### Task 13: Add LLM Query API over JSONL Logs (DuckDB)
**What:** Build FastAPI endpoint that lets LLMs query logs with natural language → SQL

**Why Necessary:**
- LLMs can't efficiently parse 89 MB of JSONL (context limit, cost)
- Need "what was rejection rate by hour on Dec 19?" → instant SQL query
- Enables chatbot: "Why were trades rejected?" → query engine → structured answer

**What to Do:**
```python
# Create backend/log_query_api.py
from fastapi import FastAPI
import duckdb

app = FastAPI()

# Load logs into DuckDB (in-memory or persistent)
conn = duckdb.connect('logs.duckdb')
conn.execute("""
    CREATE TABLE order_intents AS 
    SELECT * FROM read_json_auto('paper_trading_outputs/*/logs/order_intent_*.jsonl')
""")

@app.post("/query")
def query_logs(query: str):
    """
    Example queries:
    - "rejection rate by hour on 2025-12-19"
    - "total PnL by timeframe"
    - "average holding time for winning trades"
    """
    # Map natural language → SQL (use GPT-4 or Claude)
    sql = convert_nl_to_sql(query)
    
    result = conn.execute(sql).fetchdf()
    return result.to_dict(orient='records')

def convert_nl_to_sql(natural_query: str) -> str:
    """Use LLM to convert natural language to SQL"""
    prompt = f"""
    Convert this natural language query to DuckDB SQL:
    Query: {natural_query}
    
    Available tables:
    - order_intents (timestamp, symbol, decision, veto_reason_primary, ...)
    - executions (timestamp, symbol, fill_price, pnl_usd, trade_id, ...)
    - signals (timestamp, symbol, pred_direction, edge_bps_at_entry, ...)
    
    Return only the SQL query.
    """
    # Call OpenAI/Claude API
    sql = call_llm(prompt)
    return sql
```

**Files to Edit:**
- Create `backend/log_query_api.py` (new FastAPI app)
- `backend/main.py` (mount log query API as subroute)
- `requirements.txt` (add `duckdb`, `fastapi`)

---

### Task 14: Implement Tiered Log Storage (Hot/Warm/Cold)
**What:** Auto-move logs: hot (last 30d local) → warm (31-90d S3/GCS) → cold (91d+ archive)

**Why Necessary:**
- 89 MB/2 days = 16 GB/year → expensive local storage
- Only need last 30 days instantly accessible for debugging
- Older logs (90d+) rarely accessed, should be in cheap cold storage ($0.004/GB vs $0.10/GB)

**What to Do:**
```python
# Create ops/log_archiver.py
import boto3
from pathlib import Path
from datetime import datetime, timedelta

s3 = boto3.client('s3')
BUCKET = 'metastackerbandit-logs'

def archive_old_logs():
    """Move logs older than 30 days to S3"""
    cutoff_date = datetime.now() - timedelta(days=30)
    
    for log_file in Path('paper_trading_outputs').rglob('*.jsonl*'):
        # Check file modification time
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        
        if mtime < cutoff_date:
            # Upload to S3
            s3_key = f"warm/{log_file.relative_to('paper_trading_outputs')}"
            s3.upload_file(str(log_file), BUCKET, s3_key)
            
            # Delete local copy
            log_file.unlink()
            print(f"Archived {log_file} to s3://{BUCKET}/{s3_key}")

# Run daily via cron or scheduled task
```

**Files to Edit:**
- Create `ops/log_archiver.py` (new archival script)
- `ops/setup_cron.sh` (schedule daily run)
- `.env` (add AWS credentials: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)

---

## 🎯 RECOMMENDED PRIORITY ORDER

### Phase 1: Critical Diagnostics (Start Here)
1. **Task 3** - Veto reason fields (answers "why Dec 19 rejections?")
2. **Task 1** - Error/rejection metrics (alerts when rejection rate spikes)
3. **Task 5** - Data staleness (detects if rejections were due to stale data)

### Phase 2: Risk Visibility
4. **Task 2** - Risk budget tracking (see how much risk you're using)
5. **Task 4** - Trade lifecycle (link entry → exit → PnL)

### Phase 3: Historical Analysis
6. **Task 7** - Session summary (rejection breakdown by hour)
7. **Task 6** - Trade summary (per-trade PnL analysis)

### Phase 4: Model Validation
8. **Task 8** - Backtest-aligned fields (compare live vs backtest)
9. **Task 9** - Calibration linkage (validate calibration accuracy)
10. **Task 10** - Prediction quality (detect model drift)

### Phase 5: Infrastructure (After Above Complete)
11. **Task 12** - 5-min health snapshots (better dashboards)
12. **Task 11** - Log sampling (reduce storage costs)
13. **Task 13** - LLM query API (fast log queries)
14. **Task 14** - Tiered storage (long-term cost optimization)

---

## 🚀 QUICK START: Fix Dec 19 Diagnosis Today

**If you have 2 hours right now, do this:**

1. **Task 3** (Veto reasons) - 1 hour
   - Edit `live_demo/decision.py` lines 150-180 (where order_intent is emitted)
   - Add `veto_reason_primary`, `veto_reason_secondary`, `guard_details`
   - Restart bots, let run for 1 hour
   
2. **Task 7** (Session summary script) - 30 minutes
   - Create `scripts/build_session_summary.py` (copy code from above)
   - Run on Dec 18-19 logs: `python scripts/build_session_summary.py`
   - Open `session_summary.jsonl` → you'll see rejection breakdown by hour
   
3. **Analyze Results** - 30 minutes
   - Query: "Which hour had most rejections?"
   - Query: "Was it spread_guard or volatility_guard?"
   - Query: "What were the guard threshold values vs actual market values?"
   
**You'll immediately know:** "Dec 19, 14:00-16:00, spread_guard rejected 28/30 decisions because spread was 12-15 bps but threshold is 8 bps → market was illiquid during that period"

---

## 📊 EXPECTED IMPACT

After completing all tasks:

**Diagnostic Speed:** 
- Before: "Spend 2 hours parsing 89 MB of logs manually"
- After: "Query `session_summary.jsonl` in 10 seconds"

**Alert Capabilities:**
- Before: "Discover 100% rejection rate 24 hours later"
- After: "Alert fires after 2 hours of >80% rejection rate"

**Model Validation:**
- Before: "Can't tell if model is degrading"
- After: "IC tracker shows model IC dropped from 0.35 to 0.12 over last week → retrain"

**Cost Optimization:**
- Before: "16 GB/year local storage + high S3 costs"
- After: "~2 GB hot + $5/year cold storage"

**LLM Efficiency:**
- Before: "Can't ask 'why were trades rejected?' without manual analysis"
- After: "LLM queries DuckDB, gets structured answer in <1 second"

---

## ✅ COMPLETION CHECKLIST

- [ ] Task 1: Error/rejection metrics in health
- [ ] Task 2: Daily risk budget tracking
- [ ] Task 3: Veto reason fields in order_intent
- [ ] Task 4: Trade lifecycle fields in execution
- [ ] Task 5: Data staleness metrics in health
- [ ] Task 6: Trade summary aggregator script
- [ ] Task 7: Session summary aggregator script
- [ ] Task 8: Backtest-aligned prediction fields
- [ ] Task 9: Calibration → execution linkage
- [ ] Task 10: Prediction quality event
- [ ] Task 11: Hyperliquid fills sampling
- [ ] Task 12: 5-minute health snapshots
- [ ] Task 13: LLM query API (DuckDB)
- [ ] Task 14: Tiered log storage

**Estimated Total Time:** 40-50 hours (spread over 2-3 weeks)
**Estimated Cost Savings:** ~$200/year in storage + faster debugging (worth $1000s in avoided losses)
