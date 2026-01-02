# MetaStackerBandit Source Code Archive

**Archive Name:** MetaStackerBandit_source_2026-01-02_135659.zip  
**Size:** ~38 MB  
**Created:** January 2, 2026 at 13:56:59

## Contents

This archive contains **only the source code** of the MetaStackerBandit project, excluding all dependencies, data files, logs, and other unnecessary files.

### Included Files & Directories

#### Root Level Files
- **Python Scripts:** All `.py` files including:
  - Bot runners (`run_5m_debug.py`, `run_1h.py`, `run_12h.py`, `run_24h.py`)
  - Analysis scripts (`analyze_*.py`)
  - Training scripts (`retrain_*.py`, `train_model.py`)
  - Monitoring scripts (`monitor_*.py`)
  - Verification scripts (`verify_*.py`)
  - Testing scripts (`test_*.py`)
  - Diagnostic scripts (`check_*.py`, `diagnose_*.py`)
  
- **Shell Scripts:** `.sh`, `.bat`, `.ps1` files for deployment and automation
- **Documentation:** All `.md` files including:
  - README.md
  - Status reports
  - Implementation guides
  - Deployment instructions
  
- **Configuration:**
  - `requirements.txt` - Python dependencies list
  - `.env.example` - Environment variables template
  - `.gitignore` - Git ignore patterns
  - `nginx.conf` - Nginx configuration
  - Important JSON configs (`vm_ip.json`, etc.)

#### Source Code Directories

1. **`live_demo/`** - Main 5-minute timeframe trading bot
   - Core trading logic (`main.py`, `bandit.py`, `decision.py`)
   - Feature engineering (`features.py`, `overlay_features.py`)
   - Risk management (`risk_and_exec.py`)
   - Model runtime (`model_runtime.py`, `custom_models.py`)
   - Market data handling (`market_data.py`, `hyperliquid_listener.py`)
   - Execution tracking (`execution_tracker.py`, `order_intent_tracker.py`)
   - Configuration files (`config.json`, `config_overlay.json`)
   - Models directory (trained model files)
   - Scripts, tools, and utilities

2. **`live_demo_1h/`** - 1-hour timeframe trading bot
   - Similar structure to live_demo but for 1h timeframe

3. **`live_demo_12h/`** - 12-hour timeframe trading bot
   - Similar structure to live_demo but for 12h timeframe

4. **`live_demo_24h/`** - 24-hour timeframe trading bot
   - Similar structure to live_demo but for 24h timeframe

5. **`backend/`** - FastAPI backend server
   - `main.py` - API endpoints and server logic
   - Startup scripts

6. **`frontend/`** - React frontend application
   - Source code (`src/` directory)
   - Components, pages, services
   - Configuration files (`package.json`, etc.)
   - Build output (compiled JavaScript/CSS)

7. **`core/`** - Shared core utilities
   - `config.py` - Configuration management

8. **`scripts/`** - Utility scripts
   - Deployment scripts
   - Data processing scripts
   - Maintenance utilities

9. **`tools/`** - Development and analysis tools
   - Performance analysis
   - Data validation
   - Debugging utilities

10. **`ops/`** - Operations and DevOps
    - Deployment configurations
    - Infrastructure scripts

11. **`notebooks/`** - Jupyter notebooks
    - Model training notebooks
    - Analysis notebooks
    - Research and experimentation

12. **`tests/`** - Test files
    - Unit tests
    - Integration tests

13. **`docs/`** - Additional documentation

14. **`plans/`** - Implementation plans and roadmaps

15. **`.github/`** - GitHub Actions CI/CD workflows

### Excluded Files & Directories

The following were **intentionally excluded** to keep the archive clean and small:

- ❌ **Dependencies:**
  - `.venv/`, `.venv_old/` - Python virtual environments
  - `node_modules/` - Node.js dependencies
  - `__pycache__/` - Python bytecode cache
  - `.pytest_cache/` - Pytest cache

- ❌ **Large Data Files:**
  - `*.csv` - Historical trading data (can be regenerated)
  - `*.rar` - Archived files
  - `*.bundle` - Git bundles
  - `BotV2-LSTM/` - Old bot version

- ❌ **Logs & Outputs:**
  - `*.log` - Log files
  - `*.jsonl`, `*.jsonl.gz` - Trading logs
  - `logs/` - Log directory
  - `paper_trading_outputs/` - Trading outputs
  - `emitters/` - Emitted data files

- ❌ **Version Control:**
  - `.git/` - Git repository history

- ❌ **Previous Archives:**
  - `*.zip` - Old zip files

- ❌ **Temporary Files:**
  - `temp_*` - Temporary directories
  - `AUDIT_EXTRACT_TEMP/` - Temporary extraction folder

- ❌ **Sensitive Files:**
  - `*.pem` - Private keys
  - `.env` - Environment variables (only `.env.example` included)

- ❌ **Model Backups:**
  - `models_backup_*/` - Old model backups
  - `models_new/` - Temporary model storage
  - `live_core/` - Core backup

## How to Use This Archive

### 1. Extract the Archive
```bash
# On Windows
Expand-Archive -Path MetaStackerBandit_source_2026-01-02_135659.zip -DestinationPath ./MetaStackerBandit

# On Linux/Mac
unzip MetaStackerBandit_source_2026-01-02_135659.zip -d ./MetaStackerBandit
```

### 2. Set Up Python Environment
```bash
cd MetaStackerBandit
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual credentials and settings
```

### 4. Set Up Frontend (if needed)
```bash
cd frontend
npm install
npm run build
```

### 5. Run the Bots
```bash
# Run 5-minute bot
python run_5m_debug.py

# Run other timeframes
python run_1h.py
python run_12h.py
python run_24h.py
```

## Project Structure Overview

```
MetaStackerBandit/
├── live_demo/              # 5m trading bot
├── live_demo_1h/           # 1h trading bot
├── live_demo_12h/          # 12h trading bot
├── live_demo_24h/          # 24h trading bot
├── backend/                # API server
├── frontend/               # Web dashboard
├── core/                   # Shared utilities
├── scripts/                # Utility scripts
├── tools/                  # Development tools
├── ops/                    # DevOps configs
├── notebooks/              # Jupyter notebooks
├── tests/                  # Test files
├── docs/                   # Documentation
├── plans/                  # Implementation plans
├── .github/                # CI/CD workflows
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
└── README.md               # Main documentation
```

## Key Features

- **Multi-Timeframe Trading:** Supports 5m, 1h, 12h, and 24h timeframes
- **Machine Learning Models:** LSTM-based prediction models
- **Risk Management:** Sophisticated position sizing and risk controls
- **Real-time Data:** Hyperliquid WebSocket integration
- **Paper Trading:** Safe testing environment
- **Web Dashboard:** React-based monitoring interface
- **Comprehensive Logging:** Detailed execution tracking
- **CI/CD Ready:** GitHub Actions workflows included

## Notes

- This archive contains the **latest stable version** as of January 2, 2026
- All model files are included in their respective `models/` directories
- Configuration files use placeholder values - update with your credentials
- Historical data files are excluded but can be regenerated using the included scripts
- The project is ready to deploy after setting up dependencies and configuration

## Support

For questions or issues, refer to:
- `README.md` - Main project documentation
- `docs/` - Additional documentation
- Status reports and implementation guides in root directory
