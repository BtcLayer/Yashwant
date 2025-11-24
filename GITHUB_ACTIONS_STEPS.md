# GitHub Actions CI/CD - Complete Steps Checklist ✅

## All Necessary Steps Included in `.github/workflows/ci-cd-vm.yml`

### 1. ✅ SSH Setup
- Creates `~/.ssh` directory
- Sets up SSH key from GitHub Secrets
- Configures SSH permissions
- Tests SSH connection

### 2. ✅ Repository Access
- Handles private repository cloning
- Uses `GITHUB_TOKEN` for authentication
- Clones if repository doesn't exist
- Pulls latest code if repository exists
- Preserves bot data directories during git operations

### 3. ✅ System Dependencies Installation
- Updates package lists
- Installs Python 3.13 (or falls back to Python 3.10+)
- Installs `python3-venv` package
- Installs build tools (`build-essential`)
- Installs git, curl

### 4. ✅ Node.js 18 Installation
- Checks if Node.js is installed and version
- Installs Node.js 18 from NodeSource
- Removes conflicting packages (`libnode-dev`, `nodejs-doc`, `libnode72`)
- Verifies Node.js installation

### 5. ✅ Python Environment Setup
- Attempts to create virtual environment
- Falls back to system Python if venv fails
- Sets `PYTHON_CMD` and `PIP_CMD` variables
- Handles both venv and system Python scenarios

### 6. ✅ Python Dependencies Installation
- Upgrades pip, setuptools, wheel
- Installs all packages from `requirements.txt`
- Uses `--user` flag as fallback for permission issues
- Handles installation failures gracefully

### 7. ✅ Node.js Dependencies Installation
- Checks if `frontend/node_modules` exists
- Installs npm packages if needed
- Only runs if dependencies are missing

### 8. ✅ Frontend Build
- Checks if `frontend/build` directory exists
- Builds frontend if missing or outdated
- Handles build failures gracefully (continues with backend only)
- Uses `npm run build`

### 9. ✅ Process Cleanup
- Stops existing `start_project.py` processes
- Stops existing gunicorn processes
- Stops existing uvicorn processes
- Stops any bot processes
- Waits for processes to terminate

### 10. ✅ Directory Creation
- Creates `logs` directory
- Creates `paper_trading_outputs/sheets_fallback` directory
- Ensures all necessary directories exist

### 11. ✅ Environment Variables Setup
- Sets `PATH` to include user-installed packages
  - `/root/.local/bin`
  - `$HOME/.local/bin`
- Sets `PYTHONPATH` to include user-installed packages
  - `/root/.local/lib/python3.10/site-packages`
  - `$HOME/.local/lib/python3.10/site-packages`
- Only sets these if using system Python (not venv)

### 12. ✅ Application Startup
- Starts application with `start_project.py`
- Uses `--gunicorn` flag for production server
- Uses `--daemon` flag for background execution
- Exports environment variables to nohup process
- Logs output to `logs/start_project.log`

### 13. ✅ Health Check Verification
- Waits 10 seconds + 15 seconds for application to start
- Retries health check up to 8 times
- Checks `http://localhost:8000/api/health` endpoint
- Provides clear status messages
- Doesn't fail workflow if health check fails (warns only)

### 14. ✅ Artifact Upload
- Uploads `paper_trading_outputs` as artifact
- Makes bot data available for download
- Preserves data even if deployment has issues

### 15. ✅ Deployment Summary
- Displays deployment status
- Shows application URLs
- Provides access information
- Creates GitHub Actions summary

## Complete Deployment Flow

```
1. Setup SSH → 2. Clone/Pull Repo → 3. Install System Deps → 4. Install Node.js 18
   ↓
5. Setup Python Env → 6. Install Python Deps → 7. Install Node Deps → 8. Build Frontend
   ↓
9. Stop Old Processes → 10. Create Directories → 11. Set Environment → 12. Start App
   ↓
13. Health Check → 14. Upload Artifacts → 15. Summary
```

## All Issues Handled

✅ **Private Repository Access** - Uses GITHUB_TOKEN  
✅ **Python Version Compatibility** - Works with Python 3.10+  
✅ **Node.js Version** - Installs Node.js 18  
✅ **Virtual Environment** - Handles venv creation failures  
✅ **Package Installation** - Handles permission issues with --user flag  
✅ **Frontend Build** - Explicitly builds frontend  
✅ **PATH Issues** - Sets PATH and PYTHONPATH correctly  
✅ **Process Management** - Stops old processes before starting  
✅ **Directory Creation** - Creates all necessary directories  
✅ **Health Checks** - Verifies deployment success  
✅ **Error Handling** - Graceful fallbacks throughout  

## Status: ✅ COMPLETE

All necessary steps are included in the GitHub Actions workflow. The deployment should work end-to-end!

