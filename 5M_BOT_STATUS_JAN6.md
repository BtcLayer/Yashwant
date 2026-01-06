# 5M Bot Status Report
**Generated:** 2026-01-06 11:40 IST

## ✅ Bot Status
- **Status:** RUNNING (just started)
- **Virtual Environment:** ✓ Activated (.venv)
- **Process ID:** Running in background
- **Config File:** live_demo/config.json

## 📊 Current Performance Metrics

### Trade Balance (CRITICAL ISSUE)
```
Total Trades: 5
├─ BUY:     5 (100.0%) ⚠️
├─ SELL:    0 (  0.0%) ❌
└─ NEUTRAL: 0 (  0.0%)
```

**⚠️ CRITICAL: NO SELL TRADES DETECTED!**
- The bot is only executing BUY trades
- This indicates a potential issue with:
  - Signal generation (model only predicting UP)
  - Decision logic (filtering out SELL signals)
  - Consensus requirements (blocking SELL trades)

### Profitability Metrics
```
Win Rate:       0.0% (0/5 trades profitable)
Total PnL:      $-3.70
Current Equity: $9,999.20
Initial Equity: $9,999.19
Total Return:   0.00%
```

### Configuration Settings
```
Timeframe:         5m
Symbol:            BTCUSDT
Dry Run:           true (paper trading)
CONF_MIN:          0.60
ALPHA_MIN:         0.020
Require Consensus: false ✓ (disabled as per previous fix)
Base Notional:     $25,000
Cost BPS:          5.0
```

### Signal Generation
```
Total Signals: 1,800
Last Signal:   (check signals.csv for latest)
```

## 🔍 Key Issues to Monitor

### 1. BUY/SELL Balance ❌
**Status:** CRITICAL - Only BUY trades
**Expected:** Roughly 40-60% split between BUY and SELL
**Actual:** 100% BUY, 0% SELL

**Possible Causes:**
- Model bias (only predicting positive returns)
- Signal thresholds too restrictive for SELL
- Mood/sentiment always bullish
- Feature engineering issue

### 2. Win Rate ⚠️
**Status:** WARNING - 0% win rate
**Expected:** >40% for profitable system
**Actual:** 0% (but only 5 trades, small sample)

### 3. Profitability ⚠️
**Status:** WARNING - Negative PnL
**Expected:** Positive net edge after costs
**Actual:** -$3.70 (mostly from fees/costs)

### 4. Confidence & Alpha ℹ️
**Status:** Need to check recent signals
**Expected:** 
- Confidence > 0.60
- Alpha > 2 bps net of costs

## 📋 Monitoring Checklist

### Immediate (Next 30 minutes)
- [ ] Monitor for new trades (BUY vs SELL)
- [ ] Check signal generation (pred_stack values)
- [ ] Verify model predictions are balanced
- [ ] Check mood/sentiment indicators

### Short-term (Next 2-4 hours)
- [ ] Analyze trade direction distribution
- [ ] Calculate confidence and BPS metrics
- [ ] Monitor win rate evolution
- [ ] Check for SELL signal generation
- [ ] Verify UP/DOWN/NEUTRAL balance in predictions

### Configuration Verification
- [x] Consensus requirement disabled
- [x] Dry run enabled (paper trading)
- [x] Thresholds set (CONF_MIN: 0.60, ALPHA_MIN: 0.020)
- [ ] Model flip settings (flip_mood: true, flip_model: true)
- [ ] Dynamic abstain settings

## 🛠️ Available Monitoring Tools

### Real-time Dashboard
```bash
.\.venv\Scripts\python.exe monitor_5m_realtime_dashboard.py
```
- Updates every 10 seconds
- Shows live trade balance
- Displays profitability metrics
- Alerts on imbalances

### Quick Status Check
```bash
.\.venv\Scripts\python.exe quick_5m_status.py
```
- One-time snapshot
- Shows recent trades
- Summary statistics

### Comprehensive Analysis
```bash
.\.venv\Scripts\python.exe monitor_5m_comprehensive.py
```
- Detailed metrics
- Configuration review
- Model performance analysis

## 🎯 Success Criteria

For the bot to be considered healthy:

1. **Trade Balance:** 30-70% split between BUY/SELL (not 100/0)
2. **Win Rate:** >40% over 50+ trades
3. **Profitability:** Positive total PnL after fees
4. **Confidence:** Average >0.60 on executed trades
5. **Net Edge:** Alpha BPS > Cost BPS (>5 bps net)
6. **Signal Quality:** Regular signal generation (not stale)

## 📈 Next Steps

1. **Continue monitoring** the bot for the next 1-2 hours
2. **Watch for SELL trades** - if none appear, investigate:
   - Model predictions (check signals.csv for pred_stack values)
   - Decision logic (check decision.py for filtering)
   - Mood indicators (check mood_debug.csv)
3. **Analyze signal distribution** to understand UP/DOWN/NEUTRAL balance
4. **Review model performance** if imbalance persists

## 🔗 Key Files to Monitor

- `paper_trading_outputs/5m/sheets_fallback/executions_paper.csv` - Trade executions
- `paper_trading_outputs/5m/sheets_fallback/signals.csv` - Signal generation
- `paper_trading_outputs/5m/sheets_fallback/equity.csv` - Equity curve
- `paper_trading_outputs/5m/mood_debug.csv` - Mood/sentiment indicators
- `paper_trading_outputs/5m/logs/` - Detailed logs

---

**Status:** Bot is RUNNING, monitoring in progress. Critical issue: NO SELL TRADES.
