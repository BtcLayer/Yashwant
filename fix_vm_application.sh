#!/bin/bash
set -e

cd /home/azureuser/MetaStackerBandit
export HOME=/home/azureuser
export PATH=/home/azureuser/.local/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONPATH=/home/azureuser/.local/lib/python3.10/site-packages:$PYTHONPATH

echo "=== Fixing Git Config ==="
git config --global --add safe.directory /home/azureuser/MetaStackerBandit

echo "=== Pulling Latest Code ==="
git pull origin main || echo "Git pull failed, continuing..."

echo "=== Installing Node.js 18 ==="
if ! command -v node &> /dev/null || [ "$(node --version | cut -d'v' -f2 | cut -d'.' -f1)" -lt 14 ]; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get remove -y libnode-dev nodejs-doc libnode72 2>/dev/null || true
    sudo apt-get install -y nodejs
fi
echo "Node.js version: $(node --version)"

echo "=== Installing Python Dependencies ==="
pip3 install --user --upgrade pip setuptools wheel
pip3 install --user fastapi uvicorn gunicorn numpy==1.26.4 pandas==2.1.4 joblib gspread google-auth python-binance aiohttp scikit-learn scipy requests prometheus_client psutil schedule

echo "=== Building Frontend ==="
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
cd ..

echo "=== Stopping Old Processes ==="
pkill -f start_project.py || true
pkill -f gunicorn || true
pkill -f uvicorn || true
sleep 3

echo "=== Creating Directories ==="
mkdir -p logs
mkdir -p paper_trading_outputs/sheets_fallback

echo "=== Starting Application ==="
nohup python3 start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &

sleep 15

echo "=== Checking Status ==="
ps aux | grep start_project | grep -v grep || echo "Process not found"

echo ""
echo "=== Port Check ==="
ss -tuln | grep 8000 || netstat -tuln | grep 8000 || echo "Port check failed"

echo ""
echo "=== Health Check ==="
curl -s http://localhost:8000/api/health || echo "Health check failed"

echo ""
echo "=== Recent Logs ==="
tail -30 logs/start_project.log 2>/dev/null || echo "No logs found"

