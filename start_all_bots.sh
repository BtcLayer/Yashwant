#!/bin/bash
# Script to start all timeframe bots on the VM

cd /home/ec2-user/MetaStackerBandit
source .venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p logs

# Get current date for log files
DATE=$(date +%Y%m%d)

echo "Starting all timeframe bots..."
echo "================================"

# Start 1h bot
nohup python -m live_demo.main --timeframe 1h > logs/1h_bot_${DATE}.log 2>&1 &
PID_1H=$!
echo "✅ Started 1h bot with PID: $PID_1H"

# Start 12h bot
nohup python -m live_demo.main --timeframe 12h > logs/12h_bot_${DATE}.log 2>&1 &
PID_12H=$!
echo "✅ Started 12h bot with PID: $PID_12H"

# Start 24h bot
nohup python -m live_demo.main --timeframe 24h > logs/24h_bot_${DATE}.log 2>&1 &
PID_24H=$!
echo "✅ Started 24h bot with PID: $PID_24H"

echo "================================"
echo "All bots started successfully!"
echo ""
echo "Process IDs:"
echo "  5m:  1696068 (already running)"
echo "  1h:  $PID_1H"
echo "  12h: $PID_12H"
echo "  24h: $PID_24H"
echo ""
echo "To check status: ps aux | grep live_demo.main"
echo "To view logs: tail -f logs/*_bot_${DATE}.log"
