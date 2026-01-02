# MetaStackerBandit - Project Handoff Documentation

**Last Updated:** January 2, 2026  
**Project Status:** Active Development & Production Deployment  
**Current Phase:** Model Optimization & Performance Monitoring

---

## 📋 TABLE OF CONTENTS

1. [Project Overview](#project-overview)
2. [What We're Building](#what-were-building)
3. [Current Status](#current-status)
4. [Project Structure](#project-structure)
5. [Technical Architecture](#technical-architecture)
6. [What's Working](#whats-working)
7. [What's Missing](#whats-missing)
8. [Short-Term Goals (Next 2-4 Weeks)](#short-term-goals)
9. [Long-Term Vision](#long-term-vision)
10. [Timeline & Milestones](#timeline--milestones)
11. [How to Get Started](#how-to-get-started)
12. [Key Files & Directories](#key-files--directories)

---

## 🎯 PROJECT OVERVIEW

### What is MetaStackerBandit?

**MetaStackerBandit** is an **AI-powered cryptocurrency trading bot** that uses machine learning (LSTM neural networks) to predict Bitcoin price movements and execute automated trades on the **Hyperliquid** exchange.

### Core Concept

The system operates on a **multi-timeframe strategy**:
- **5-minute (5m)** - High-frequency scalping
- **1-hour (1h)** - Medium-term swing trading  
- **12-hour (12h)** - Position trading
- **24-hour (24h)** - Long-term trend following

Each timeframe has its own **independent ML model** that generates BUY/SELL signals based on technical indicators and market data.

### Key Innovation

We use a **"Bandit" approach** (multi-armed bandit algorithm) that:
1. Trains separate models for each timeframe
2. Combines signals using ensemble methods
3. Adapts position sizing based on model confidence
4. Implements risk management and consensus gating

---

## 🏗️ WHAT WE'RE BUILDING

### Primary Goal
Create a **profitable, fully-automated trading system** that:
- Generates consistent returns in crypto markets
- Manages risk intelligently
- Operates 24/7 without human intervention
- Adapts to changing market conditions

### Technical Goals
1. **High-Accuracy Models** (60%+ win rate per timeframe)
2. **Real-Time Execution** (sub-second latency)
3. **Robust Risk Management** (position sizing, stop-loss, take-profit)
4. **Comprehensive Monitoring** (dashboards, alerts, logging)
5. **Automated Retraining** (models stay fresh with new data)

### Business Goals
- Achieve **positive P&L** across all timeframes
- Scale to multiple cryptocurrencies (currently BTC only)
- Build a production-grade trading infrastructure
- Create a reusable framework for algorithmic trading

---

## 📊 CURRENT STATUS

### Overall Project Health: 🟢 **GOOD**

### What's Live in Production
✅ **5m Trading Bot** - Running on AWS EC2 VM  
✅ **1h Trading Bot** - Running on AWS EC2 VM  
✅ **12h Trading Bot** - Running on AWS EC2 VM  
✅ **24h Trading Bot** - Running on AWS EC2 VM  
✅ **Real-time WebSocket Data Feed** (Hyperliquid)  
✅ **Paper Trading Mode** (testing without real money)  
✅ **Google Sheets Logging** (trade tracking)  
✅ **Health Monitoring System**

### Model Performance Status

| Timeframe | Status | Accuracy | Age | Training Samples | Priority |
|-----------|--------|----------|-----|------------------|----------|
| **5m** | 🟢 Excellent | 66.07% | 0 days (NEW!) | 41,432 | ✅ Monitor |
| **1h** | 🟢 Good | 82.00% | 2 days | ~4,000 | ✅ Monitor |
| **12h** | 🟡 Weak | 62.84% | 73 days | 218 (LOW!) | 🔄 Retrain Soon |
| **24h** | 🔴 Weak | 43.05% | 76 days | Unknown | 🔄 Retrain Urgent |

### Recent Major Achievements (Last 7 Days)
1. ✅ **Fixed Critical Bug** - SELL signals were being blocked (Dec 29)
2. ✅ **Retrained 5m Model** - Brand new model with 41k samples (Jan 2)
3. ✅ **Deployed to Production** - All bots running on EC2 VM
4. ✅ **Improved Accuracy** - 5m model now at 66% (up from ~50%)

### Current Issues Being Monitored
1. 🟡 **12h Model** - Only 218 training samples (need 1,000+)
2. 🔴 **24h Model** - Very low accuracy (43%), needs complete retraining
3. ⏳ **5m Performance** - Monitoring for 48 hours to verify profitability
4. ⚠️ **Win Rate** - Need to track if models are actually profitable in live trading

---

## 📁 PROJECT STRUCTURE

### Core Directories

```
MetaStackerBandit/
├── live_demo/              # Main production code (5m timeframe)
│   ├── main.py            # Primary trading bot entry point
│   ├── decision.py        # Signal generation & consensus logic
│   ├── risk_and_exec.py   # Order execution & risk management
│   ├── features.py        # Technical indicator calculations
│   ├── models/            # Trained ML models (.keras files)
│   └── emitters/          # Data logging & output
│
├── live_demo_1h/          # 1-hour timeframe bot
├── live_demo_12h/         # 12-hour timeframe bot
├── live_demo_24h/         # 24-hour timeframe bot
│
├── notebooks/             # Jupyter notebooks for training
│   └── BanditV3.ipynb    # Latest training methodology
│
├── tools/                 # Utility scripts
├── scripts/               # Automation scripts
├── ops/                   # Operations & deployment
│
├── *.csv                  # Historical market data
├── *.py                   # Analysis & monitoring scripts
└── *.md                   # Documentation & reports
```

### Key Configuration Files
- `live_demo/config.json` - Trading parameters (position size, risk limits)
- `.env` - API keys & secrets (Hyperliquid, Google Sheets)
- `requirements.txt` - Python dependencies

---

## 🔧 TECHNICAL ARCHITECTURE

### Technology Stack
- **Language:** Python 3.11+
- **ML Framework:** TensorFlow/Keras (LSTM models)
- **Exchange:** Hyperliquid (WebSocket API)
- **Deployment:** AWS EC2 (Ubuntu VM)
- **Logging:** Google Sheets API
- **Data Storage:** CSV files + in-memory state

### Data Flow
```
1. Market Data (Hyperliquid WebSocket)
   ↓
2. Feature Engineering (technical indicators)
   ↓
3. ML Model Prediction (LSTM)
   ↓
4. Signal Generation (BUY/SELL/HOLD)
   ↓
5. Consensus Gating (multi-timeframe agreement)
   ↓
6. Risk Management (position sizing, limits)
   ↓
7. Order Execution (Hyperliquid API)
   ↓
8. Logging & Monitoring (Google Sheets, logs)
```

### ML Model Architecture
- **Type:** LSTM (Long Short-Term Memory) Neural Network
- **Input Features:** 17 technical indicators
  - RSI, MACD, Bollinger Bands, Volume, ATR, etc.
- **Output:** Binary classification (BUY=1, SELL=0)
- **Training:** Supervised learning on historical OHLC data
- **Retraining Frequency:** Every 60-90 days (or when accuracy drops)

### Trading Logic
1. **Signal Generation:** Each timeframe model predicts BUY/SELL
2. **Consensus Check:** Require agreement from multiple timeframes (optional)
3. **Position Sizing:** Dynamic based on model confidence
4. **Risk Limits:** Max position size, daily loss limits
5. **Execution:** Market orders via Hyperliquid API

---

## ✅ WHAT'S WORKING

### Production Systems
- ✅ 4 independent trading bots (5m, 1h, 12h, 24h) running 24/7
- ✅ Real-time market data ingestion via WebSocket
- ✅ ML model inference (predictions in <100ms)
- ✅ Order execution on Hyperliquid exchange
- ✅ Paper trading mode (safe testing)
- ✅ Google Sheets logging (trade history)
- ✅ Health monitoring & alerting

### Development Workflow
- ✅ Jupyter notebooks for model training
- ✅ Automated retraining scripts
- ✅ Model versioning & backups
- ✅ Performance analysis tools
- ✅ CI/CD pipeline (GitHub Actions)

### Recent Fixes
- ✅ **SELL Signal Bug** - Fixed consensus logic blocking SELL trades
- ✅ **5m Model Retraining** - Successfully retrained with 41k samples
- ✅ **Data Pipeline** - Fetching complete historical data
- ✅ **Deployment** - Stable production deployment on EC2

---

## ❌ WHAT'S MISSING

### Critical Gaps
1. 🔴 **Profitability Verification**
   - We don't yet have 48+ hours of live trading data for new 5m model
   - Need to confirm models are actually making money (not just accurate predictions)

2. 🔴 **12h & 24h Model Quality**
   - 12h: Only 218 training samples (need 1,000+)
   - 24h: 43% accuracy (barely better than random)
   - Both models are 70+ days old (stale)

3. 🟡 **Automated Retraining**
   - Currently manual process via Jupyter notebooks
   - Need scheduled retraining pipeline

4. 🟡 **Advanced Risk Management**
   - No dynamic stop-loss based on volatility
   - No portfolio-level risk limits (across all timeframes)
   - No drawdown protection

### Nice-to-Have Features
- 📊 **Real-time Dashboard** (web UI for monitoring)
- 📈 **Backtesting Framework** (test strategies on historical data)
- 🔔 **Advanced Alerting** (Telegram/Discord notifications)
- 🌐 **Multi-Asset Support** (ETH, SOL, other cryptos)
- 🧪 **A/B Testing** (compare model versions)

---

## 🎯 SHORT-TERM GOALS (Next 2-4 Weeks)

### Week 1 (Jan 2-8, 2026) - **CURRENT WEEK**
**Priority: Monitor & Validate 5m Model**

- [ ] Monitor 5m bot for 48 hours minimum
- [ ] Verify positive P&L on 5m timeframe
- [ ] Track win rate, trade frequency, execution quality
- [ ] Document 5m model performance metrics
- [ ] **Decision Point:** Keep or rollback 5m model

**Success Criteria:**
- 5m model shows positive P&L over 48 hours
- Win rate ≥ 55%
- No execution errors or crashes

---

### Week 2 (Jan 9-15, 2026)
**Priority: Retrain 12h Model**

- [ ] Fetch 6+ months of 12h historical data
- [ ] Retrain 12h model using BanditV3 approach
- [ ] Target: 1,000+ training samples
- [ ] Target: 65%+ accuracy
- [ ] Deploy new 12h model to production
- [ ] Monitor 12h performance for 48 hours

**Success Criteria:**
- 12h model trained with 1,000+ samples
- Accuracy ≥ 65%
- Positive P&L in first 48 hours

---

### Week 3-4 (Jan 16-29, 2026)
**Priority: Retrain 24h Model**

- [ ] Fetch fresh 24h historical data
- [ ] Completely retrain 24h model
- [ ] Target: 60%+ accuracy
- [ ] Deploy new 24h model to production
- [ ] Monitor 24h performance for 7 days

**Success Criteria:**
- 24h model accuracy ≥ 60%
- Positive P&L over 7 days
- All 4 timeframes profitable

---

## 🚀 LONG-TERM VISION (3-6 Months)

### Phase 1: Stability & Profitability (Month 1-2)
**Goal: All timeframes consistently profitable**

- Achieve 60%+ win rate on all timeframes
- Positive P&L for 30 consecutive days
- Zero critical bugs or downtime
- Automated daily performance reports

### Phase 2: Optimization (Month 2-3)
**Goal: Maximize returns & minimize risk**

- Implement dynamic position sizing
- Add volatility-based stop-loss
- Optimize consensus logic
- Improve signal quality (feature engineering)
- Reduce false signals

### Phase 3: Scaling (Month 3-4)
**Goal: Multi-asset & higher capital**

- Add ETH, SOL, other major cryptos
- Increase position sizes (scale capital)
- Portfolio-level risk management
- Cross-asset correlation analysis

### Phase 4: Automation (Month 4-5)
**Goal: Fully autonomous system**

- Automated model retraining (weekly)
- Self-healing infrastructure
- Anomaly detection & auto-rollback
- Zero manual intervention required

### Phase 5: Production-Grade (Month 5-6)
**Goal: Enterprise-level reliability**

- Real-time web dashboard
- Advanced analytics & reporting
- Multi-user support
- API for external integrations
- Comprehensive documentation

---

## 📅 TIMELINE & MILESTONES

### Completed Milestones ✅
- **Nov 2025:** Initial bot development & paper trading
- **Dec 2025:** Deployed to production (EC2 VM)
- **Dec 23, 2025:** Fixed Binance data issues
- **Dec 29, 2025:** Fixed SELL signal bug (consensus logic)
- **Dec 30, 2025:** Retrained 1h model (82% accuracy)
- **Jan 2, 2026:** Retrained 5m model (66% accuracy, 41k samples)

### Current Milestone 🔄
**Jan 2-8, 2026:** Validate 5m model profitability

### Upcoming Milestones 📅
- **Jan 9-15, 2026:** Retrain 12h model
- **Jan 16-29, 2026:** Retrain 24h model
- **Feb 2026:** All timeframes profitable for 30 days
- **Mar 2026:** Implement automated retraining
- **Apr 2026:** Add multi-asset support
- **May 2026:** Launch real-time dashboard

---

## 🚀 HOW TO GET STARTED

### For Development (Local)

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd MetaStackerBandit
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Add your Hyperliquid API keys
   - Add Google Sheets credentials

4. **Run a bot locally (paper trading)**
   ```bash
   python run_5m_debug.py
   ```

### For Production (EC2 VM)

1. **SSH into VM**
   ```bash
   ssh -i yashw-key.pem ubuntu@<VM_IP>
   ```

2. **Check bot status**
   ```bash
   cd MetaStackerBandit
   python check_vm_bots.py
   ```

3. **View logs**
   ```bash
   tail -f live_demo/emitters/main.log
   ```

### For Model Training

1. **Open Jupyter notebook**
   ```bash
   jupyter notebook notebooks/BanditV3.ipynb
   ```

2. **Follow training steps in notebook**
   - Load historical data
   - Engineer features
   - Train LSTM model
   - Evaluate accuracy
   - Save model to `live_demo/models/`

---

## 📂 KEY FILES & DIRECTORIES

### Critical Production Files
| File | Purpose | Location |
|------|---------|----------|
| `main.py` | Main trading bot logic | `live_demo/main.py` |
| `decision.py` | Signal generation & consensus | `live_demo/decision.py` |
| `risk_and_exec.py` | Order execution & risk | `live_demo/risk_and_exec.py` |
| `features.py` | Technical indicators | `live_demo/features.py` |
| `config.json` | Trading parameters | `live_demo/config.json` |
| `.env` | API keys & secrets | `.env` |

### ML Models
| Model | Timeframe | Location | Status |
|-------|-----------|----------|--------|
| `bandit_5m.keras` | 5 minutes | `live_demo/models/` | 🟢 Excellent |
| `bandit_1h.keras` | 1 hour | `live_demo_1h/models/` | 🟢 Good |
| `bandit_12h.keras` | 12 hours | `live_demo_12h/models/` | 🟡 Weak |
| `bandit_24h.keras` | 24 hours | `live_demo_24h/models/` | 🔴 Weak |

### Training & Analysis
| File | Purpose |
|------|---------|
| `notebooks/BanditV3.ipynb` | Latest model training methodology |
| `retrain_5m_banditv3.py` | Automated 5m retraining script |
| `analyze_all_timeframes.py` | Model performance analysis |
| `monitor_bots.py` | Live bot monitoring |

### Historical Data
| File | Description | Rows |
|------|-------------|------|
| `ohlc_btc_5m.csv` | 5-minute OHLC data | ~300k |
| `ohlc_btc_1h.csv` | 1-hour OHLC data | ~5k |
| `ohlc_btc_24h.csv` | 24-hour OHLC data | ~800 |
| `funding_btc.csv` | Funding rate data | ~3k |
| `historical_trades_btc.csv` | Trade history | ~4M |

### Documentation
| File | Purpose |
|------|---------|
| `README.md` | Project overview |
| `ALL_TIMEFRAMES_STATUS.md` | Current model status (this doc) |
| `5M_RETRAINING_GUIDE.md` | How to retrain 5m model |
| `VM_DEPLOYMENT_INSTRUCTIONS.md` | Production deployment guide |
| `QUICK_REFERENCE.md` | Common commands & workflows |

### Monitoring & Logs
| Location | Purpose |
|----------|---------|
| `live_demo/emitters/main.log` | 5m bot logs |
| `live_demo/emitters/executions_paper.csv` | Trade history |
| `5m_debug.log` | Debug output |
| Google Sheets | Live trade tracking |

---

## 🎓 UNDERSTANDING THE CODEBASE

### Entry Points by Timeframe
- **5m:** `python run_5m_debug.py` → `live_demo/main.py`
- **1h:** `python run_1h.py` → `live_demo_1h/main.py`
- **12h:** `python run_12h.py` → `live_demo_12h/main.py`
- **24h:** `python run_24h.py` → `live_demo_24h/main.py`

### Key Code Modules

**1. Data Ingestion** (`hyperliquid_listener.py`)
- Connects to Hyperliquid WebSocket
- Receives real-time OHLC candles
- Buffers data for feature calculation

**2. Feature Engineering** (`features.py`)
- Calculates 17 technical indicators
- RSI, MACD, Bollinger Bands, ATR, Volume, etc.
- Normalizes features for ML model

**3. Model Inference** (`model_runtime.py`)
- Loads trained LSTM model
- Runs predictions on new data
- Returns BUY/SELL probability

**4. Signal Generation** (`decision.py`)
- Converts model output to trading signals
- Applies consensus logic (multi-timeframe)
- Filters low-confidence signals

**5. Risk Management** (`risk_and_exec.py`)
- Calculates position size
- Enforces risk limits
- Executes orders via Hyperliquid API

**6. Logging** (`emitters.py`, `sheets_logger.py`)
- Writes trades to CSV
- Uploads to Google Sheets
- Tracks P&L and performance

---

## 📞 NEXT STEPS FOR COLLABORATION

### Immediate Actions (Today)
1. **Read this document** - Understand project context
2. **Review `ALL_TIMEFRAMES_STATUS.md`** - Current model status
3. **Check running bot** - `python check_vm_bots.py`
4. **Review recent logs** - See what's happening in production

### This Week
1. **Monitor 5m bot together** - Track performance metrics
2. **Discuss 12h retraining plan** - Align on approach
3. **Review codebase** - Walk through key modules
4. **Set up development environment** - Get local setup working

### Questions to Discuss
- What's your background/experience with ML & trading?
- What aspects of the project interest you most?
- What should we prioritize first?
- Any concerns or questions about the current approach?

---

## 📊 SUCCESS METRICS

### Model Performance
- **Accuracy:** 60%+ per timeframe
- **Win Rate:** 55%+ in live trading
- **Sharpe Ratio:** 1.5+ (risk-adjusted returns)

### System Reliability
- **Uptime:** 99%+ (minimal downtime)
- **Latency:** <500ms from signal to execution
- **Error Rate:** <1% of trades

### Business Metrics
- **P&L:** Positive over 30-day rolling window
- **Max Drawdown:** <10% of capital
- **ROI:** Target 5-10% monthly

---

## 🔗 IMPORTANT LINKS

- **Production VM:** AWS EC2 (IP in `vm_ip.json`)
- **Google Sheets:** Trade logs (link in `.env`)
- **Hyperliquid:** https://app.hyperliquid.xyz/
- **GitHub Repo:** (add your repo URL)

---

## 📝 FINAL NOTES

### Project Philosophy
- **Data-Driven:** All decisions backed by metrics
- **Iterative:** Continuous improvement over perfection
- **Risk-Aware:** Capital preservation is priority #1
- **Automated:** Minimize manual intervention

### Current Focus
We're at a **critical validation phase**. The 5m model was just retrained and deployed. The next 48 hours will determine if our approach is working. If successful, we'll replicate the process for 12h and 24h.

### Your Role
You'll be joining at a pivotal moment. We need help with:
1. Monitoring & validating current models
2. Retraining 12h and 24h models
3. Improving risk management
4. Building automation & tooling
5. Scaling to multi-asset trading

### Communication
- **Daily:** Quick status updates on bot performance
- **Weekly:** Deeper analysis & planning sessions
- **Ad-hoc:** Urgent issues or opportunities

---

**Welcome to the team! Let's build something amazing together.** 🚀

---

*Document created: January 2, 2026*  
*Last updated: January 2, 2026*  
*Next review: January 9, 2026*
