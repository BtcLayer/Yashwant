#!/bin/bash
cd /home/azureuser/MetaStackerBandit

# Add root's local bin to PATH
export PATH=/root/.local/bin:$PATH
export PYTHONPATH=/root/.local/lib/python3.10/site-packages:$PYTHONPATH

# Stop old processes
pkill -f start_project.py || true
pkill -f gunicorn || true
pkill -f uvicorn || true
sleep 2

# Create directories
mkdir -p logs
mkdir -p paper_trading_outputs/sheets_fallback

# Start application with proper PATH
PATH=/root/.local/bin:$PATH PYTHONPATH=/root/.local/lib/python3.10/site-packages:$PYTHONPATH nohup python3 start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &

sleep 10

# Check status
echo "=== Process Status ==="
ps aux | grep start_project | grep -v grep || echo "Process not found"

echo ""
echo "=== Port Status ==="
netstat -tuln | grep 8000 || echo "Port 8000 not listening"

echo ""
echo "=== Health Check ==="
curl -s http://localhost:8000/api/health || echo "Health check failed"

echo ""
echo "=== Recent Logs ==="
tail -30 logs/start_project.log 2>/dev/null || echo "No logs found"

