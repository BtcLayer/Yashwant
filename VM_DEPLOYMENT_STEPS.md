# VM Deployment Steps

## Quick Deployment Commands

Run these commands directly on the VM via SSH:

```bash
# SSH into VM
ssh azureuser@40.88.15.47

# Navigate to project
cd /home/azureuser/MetaStackerBandit

# Step 1: Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv python3-pip nodejs npm build-essential git curl

# Step 2: Create Python virtual environment
python3.13 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Step 3: Install Python dependencies
pip install -r requirements.txt

# Step 4: Install Node.js dependencies (frontend will auto-build with start_project.py)
cd frontend
npm install
cd ..

# Step 5: Create necessary directories
mkdir -p paper_trading_outputs/sheets_fallback
mkdir -p logs

# Step 6: Set up .env file (if needed)
# Copy from .env.example or create manually
# nano .env

# Step 7: Start the application using start_project.py
# This script handles everything: frontend build, backend, and bots
# --gunicorn: Use gunicorn with multiple workers for production
# --daemon: Run in background mode
source venv/bin/activate
python start_project.py --gunicorn --daemon

# Or run in background with nohup:
# nohup python start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &
```

## Access the Application

Once started, access at:

- **Frontend Dashboard**: <http://40.88.15.47:8000>
- **Backend API**: <http://40.88.15.47:8000/api>
- **Health Check**: <http://40.88.15.47:8000/api/health>

## Check Logs

```bash
# Start project log
tail -f logs/start_project.log

# Trading bots log (if started separately)
tail -f logs/trading-bots.log
```

## Stop the Application

```bash
# Find the process
ps aux | grep "start_project.py"

# Kill the process
pkill -f "python.*start_project.py"
pkill -f gunicorn
pkill -f uvicorn
pkill -f run_unified_bots.py
```

## Using start_project.py

The `start_project.py` script is now used for both local development and production deployment:

**Local Development:**
```bash
python start_project.py
```

**Production Deployment:**
```bash
python start_project.py --gunicorn --daemon
```

**Options:**
- `--gunicorn`: Use gunicorn with multiple workers (production)
- `--daemon`: Run in background mode (for production)
- `--no-bots`: Don't auto-start trading bots
- `--no-build`: Skip frontend build (use existing)
- `--port PORT`: Custom port (default: 8000)

The script automatically:
- Checks and builds frontend if source files changed
- Starts backend server
- Optionally starts trading bots
- Handles all environment variables
