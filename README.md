# MetaStackerBandit

**Production-ready Trading Bot with 24/7 Azure VM deployment**

[![Azure](https://img.shields.io/badge/Azure-VM-blue.svg)](https://azure.microsoft.com)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](CONTRIBUTING.md)

## Overview

This repository contains a **production-ready trading bot** with multi-timeframe analysis (5-minute, 1-hour, 12-hour, 24-hour) and direct Azure VM deployment via GitHub Actions CI/CD.

### Features

- **Multi-Timeframe Trading:** Concurrent 5min, 1h, 12h, and 24h strategies
- **Automated CI/CD:** GitHub Actions automatically deploys to Azure VM
- **VM Deployment:** Direct deployment to Azure Virtual Machine
- **Security First:** GitHub Secrets integration, no secrets in code
- **24/7 Monitoring:** Health checks, logging, and alerting
- **One Command:** Single command runs all versions simultaneously
- **React Dashboard:** Real-time monitoring and analytics

### Architecture

- **Direct Python Deployment:** Runs Python directly on Azure VM
- **Concurrent Execution:** All timeframes run in parallel as background processes
- **Azure VM:** Single VM deployment for complete trading system
- **FastAPI Backend:** Serves API and static frontend files
- **Google Sheets:** Centralized logging and monitoring
- **GitHub Actions CI/CD:** Automated deployment on every push

## Quick Start

### Easiest Way - Single Script Startup

```bash
# Clone and setup
git clone https://github.com/anythingai/MetaStackerBandit.git
cd MetaStackerBandit

# Install dependencies
pip install -r requirements.txt

# ONE COMMAND - Start everything (backend + frontend + bots)
python start_project.py

# Recommended production flags (matches CI/CD deployment)
# Backend served by gunicorn, nginx reverse proxy, bots auto-start
python start_project.py --gunicorn --daemon

# Access everything on ONE port:
# • Frontend: http://localhost:8000/
# • API: http://localhost:8000/api/
# • API Docs: http://localhost:8000/docs
```

**Options:**
```bash
python start_project.py --port 8000      # Custom port
python start_project.py --no-bots        # Don't auto-start trading bots
python start_project.py --no-build       # Skip frontend build
python start_project.py --dev            # Dev mode (no build, use existing)
```

### Alternative - Manual Startup

```bash
# Run all trading bot versions simultaneously
python run_unified_bots.py

# Start backend (serves frontend if built)
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Or use the single startup script (recommended)
python start_project.py

# Monitor in real-time
python monitor_bots.py --watch
```

### Azure VM Deployment

```bash
# Automatic deployment via GitHub Actions (recommended)
# Just push to main branch - deployment happens automatically!

# Manual deployment (if needed)
# See VM_DEPLOYMENT_STEPS.md for detailed instructions
```

### Local Development

```bash
# Run all versions concurrently
python run_unified_bots.py

# Or run individual versions
python -m live_demo.main        # 5-minute version
python -m live_demo_1h.main     # 1-hour version
python -m live_demo_12h.main    # 12-hour version
python -m live_demo_24h.main    # 24-hour version
```

## Project Structure

- **`live_demo/`** - 5-minute trading version
- **`live_demo_1h/`** - 1-hour trading version
- **`live_demo_12h/`** - 12-hour trading version
- **`live_demo_24h/`** - 24-hour trading version
- **`backend/`** - FastAPI backend (serves API and frontend)
- **`frontend/`** - React dashboard
- **`deploy_vm.sh`** - VM deployment script
- **`run_unified_bots.py`** - Unified runner script (runs all versions)
- **`.github/workflows/ci-cd-vm.yml`** - GitHub Actions VM deployment workflow

## Technologies

- **Azure VM** - Direct Python deployment on Virtual Machine
- **GitHub Secrets** - Secure credential management
- **FastAPI** - Backend API and static file serving
- **React** - Frontend dashboard
- **Python Asyncio** - Concurrent execution of all trading strategies

## Quick Start

### 1. Test Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run all versions simultaneously
python run_unified_bots.py

# Or run individual versions
python -m live_demo.main        # 5-minute version
python -m live_demo_1h.main     # 1-hour version
python -m live_demo_12h.main    # 12-hour version
python -m live_demo_24h.main    # 24-hour version

# Monitor in real-time
python monitor_bots.py --watch
```

### 2. Deploy to Azure

#### Automatic Deployment (Recommended)

The application automatically deploys to Azure VM when you push to the `main` branch:

1. **Push to GitHub** - GitHub Actions handles everything
2. **Frontend builds** - React app is built automatically
3. **Deploy to VM** - Direct Python deployment to Azure VM
4. **Trading bots start** - All versions run in background

See `GITHUB_CI_CD_SETUP.md` for complete CI/CD setup documentation.

#### Manual Deployment

```bash
# Deploy to VM manually
ssh azureuser@40.88.15.47
cd /home/azureuser/MetaStackerBandit
./deploy_vm.sh
```

The direct deployment approach runs all timeframes simultaneously as background processes. See `VM_DEPLOYMENT_STEPS.md` for complete deployment instructions.

**Benefits of direct deployment:**

- All timeframes running simultaneously as background processes
- Simplified deployment and management
- Single VM for all versions
- Unified logging and monitoring
- Reduced resource overhead

## 24/7 Continuous Operation

### Production Ready Configuration

**Your trading bots are configured for 24/7 operation with:**

#### Azure VM Configuration (24/7 Ready)

- Systemd service or nohup - Keeps application running
- Automatic restart on failure - Process managers handle restarts
- Health checks via `/api/health` - Continuous monitoring
- Resource limits - VM size determines resources
- Proper logging setup - Continuous operation tracking
- Concurrent execution - All versions run simultaneously as background processes
- GitHub Actions CI/CD - Automatic deployments on push
- Gunicorn with multiple workers - Handles traffic efficiently
- Log rotation and monitoring - Continuous operation tracking

#### Trading Bot Resilience

- Automatic reconnection to Binance/Hyperliquid APIs
- Graceful handling of network timeouts and API rate limits
- Error recovery and retry mechanisms built-in
- Continuous position monitoring and risk management

### 24/7 Monitoring Tools

#### Local Monitoring (Development)

```bash
# Continuous monitoring of all versions
python monitor_bots.py --watch

# Or check status once
python monitor_bots.py

# Monitor all versions
python monitor_bots.py --watch            # All versions
python monitor_bots.py                    # Status check
```

#### Azure Monitoring (Production)

```bash
# Check application status
./monitor_cicd.sh status

# Monitor the application (contains all versions)
ssh azureuser@40.88.15.47 "tail -f logs/trading-bots.log"

# Check application status
curl http://40.88.15.47:8000/api/health

# Monitor with Windows script
monitor_cicd.bat status
```

#### Log Management

```bash
# View all logs in real-time
tail -f logs/trading-bot-*.log    # Linux/Mac
type logs\trading-bot-*.log       # Windows

# Check for errors across all versions
grep -i error logs/trading-bot-*.log    # Linux/Mac
find logs -name "*.log" -exec grep -l "error" {} \;  # Windows
```

## Monitoring Concurrent Execution

### Local Monitoring

When running multiple versions locally:

```bash
# View all logs in real-time
tail -f logs/trading-bot-*.log    # Linux/Mac
type logs\trading-bot-*.log       # Windows (open logs folder)

# Monitor specific version
tail -f logs/trading-bot-1h.log   # 1-hour version only
tail -f logs/trading-bot-12h.log  # 12-hour version only
```

### Local Monitoring

```bash
# Monitor all versions (local development)
python monitor_bots.py --watch              # All versions in one stream
python monitor_bots.py                     # Status check

# Check if all versions are running
ps aux | grep "run_unified_bots.py"        # Linux/Mac
Get-Process | Where-Object {$_.ProcessName -like "*python*"}  # Windows
```

### Azure VM Monitoring

```bash
# Monitor the application (contains all versions)
ssh azureuser@40.88.15.47 "tail -f logs/trading-bots.log"

# Check 24/7 status
curl http://40.88.15.47:8000/api/health

# Monitor uptime and health
curl http://40.88.15.47:8000/api/dashboard/summary

# Check application status via SSH
ssh azureuser@40.88.15.47 "ps aux | grep gunicorn"
```

## Authentication Setup

### Google Sheets Credentials

- **Development:** Credentials stored in `.env` file (separate for each version)
- **Production:** Credentials stored in `.env` file on VM, accessed via `GOOGLE_SHEETS_CREDENTIALS_JSON`
- **Multi-version Support:** Each version (5min, 1h, 12h, 24h) has its own credentials handling

### API Keys

- **Development:** Set in `azure.env.example`
- **Production:** Stored in Azure Key Vault with Managed Identity access

## Project Structure

```
 start_project.py            # Main startup script (backend, frontend, bots)
 deploy_vm.sh                # VM deployment script
 .github/workflows/           # CI/CD workflows (VM deployment)
 .env                        # Environment variables (root)
 requirements.txt            # Python dependencies
 run_unified_bots.py         # Unified runner script
```

## Features

### Performance Optimizations

- **BLAS/LAPACK libraries** for faster numpy/scipy operations
- **Thread control** prevents CPU oversubscription
- **Memory optimization** for machine learning workloads

### Security

- **Non-root user** execution
- **Azure Key Vault** integration for secrets
- **Managed Identity** for secure Azure access
- **Minimal attack surface** with slim base images

### Monitoring

- **Health checks** via `/api/health` endpoint
- **Structured logging** to log files
- **Real-time dashboard** for monitoring

## Development Workflow

1. **Local Testing:** Use `python run_unified_bots.py` for development
2. **Production Deployment:** Push to `main` branch - automatic deployment via GitHub Actions
3. **VM Deployment:** Use `deploy_vm.sh` for manual VM deployment
4. **Monitoring:** Use dashboard at `http://40.88.15.47:8000` or check logs

## Supported Versions

All versions configured and ready:

- **5-minute trading** (`python -m live_demo.main`)
- **1-hour trading** (`python -m live_demo_1h.main`)
- **12-hour trading** (`python -m live_demo_12h.main`)

## Troubleshooting

### Common Issues

1. **Authentication errors:** Check Key Vault permissions and secret values
2. **Module import errors:** Verify PYTHONPATH=/app is set
3. **Memory issues:** Increase VM size or optimize resource usage
4. **Network connectivity:** Verify Azure networking configuration

### Verification

Check that the application is running:

```bash
# Health check
curl http://40.88.15.47:8000/api/health

# Dashboard summary
curl http://40.88.15.47:8000/api/dashboard/summary
```

## Documentation

- **[GITHUB_CI_CD_SETUP.md](GITHUB_CI_CD_SETUP.md)** - GitHub CI/CD setup guide
- **[VM_DEPLOYMENT_STEPS.md](VM_DEPLOYMENT_STEPS.md)** - Manual VM deployment guide

## Contributing

1. Test locally with `python run_unified_bots.py`
2. Verify deployment with health check endpoint
3. Update documentation for any changes
4. Follow Azure security best practices

---

## Repository

**GitHub:** <https://github.com/anythingai/MetaStackerBandit.git>

**Ready for production deployment!**

## Ensemble 1.1 observability (heartbeat & emitter smoke checks)

For the Ensemble 1.1 release we added lightweight observability helpers and small CI smoke checks:

- A `heartbeat.json` file is written under paper_trading_outputs/logs/<bot>/heartbeat/heartbeat.json � used for simple liveness checks.
- Small unit tests for heartbeat and emitter metadata are in `tests/test_heartbeat_and_emitters.py`.
- A hermetic smoke helper is available at `scripts/check_heartbeat.py` which returns 0 if it finds heartbeat.json files under a logs root.

How to run locally (quick):

1) Run the local tests for these features:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_heartbeat_and_emitters.py tests/test_check_heartbeat_script.py
```

2) Run the smoke helper against your logs root:

```powershell
.venv\Scripts\python.exe scripts/check_heartbeat.py paper_trading_outputs/logs
```

See `docs/ENHANCEMENTS-ensemble1.1.md` for more details on the minimal, low-risk changes included in v1.1.
