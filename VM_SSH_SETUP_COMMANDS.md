# VM Setup Commands (Run on VM)

You're now SSH'd into the VM. Run these commands to complete the setup:

## Step 1: Check Current Status

```bash
# Check if repository exists
ls -la /home/azureuser/MetaStackerBandit

# Check if Python 3.13 is installed
python3.13 --version

# Check if Node.js is installed
node --version
npm --version
```

## Step 2: Complete Setup (if needed)

```bash
# Navigate to project directory
cd /home/azureuser/MetaStackerBandit

# If repository doesn't exist, clone it
if [ ! -d ".git" ]; then
    echo "Cloning repository..."
    git clone https://github.com/anythingai/MetaStackerBandit.git .
fi

# Update system packages
sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv python3-pip build-essential git curl nodejs npm

# Create Python virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3.13 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "Installing Python dependencies (this may take a few minutes)..."
pip install -r requirements.txt

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Create necessary directories
mkdir -p paper_trading_outputs/sheets_fallback
mkdir -p logs
```

## Step 3: Configure .env File

```bash
cd /home/azureuser/MetaStackerBandit

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    touch .env
    echo "Please edit .env with your API keys:"
    echo "nano .env"
else
    echo ".env file exists"
    echo "To edit: nano .env"
fi
```

## Step 4: Start the Application

```bash
cd /home/azureuser/MetaStackerBandit
source venv/bin/activate

# Stop any existing processes
pkill -f "python.*start_project.py" || true
pkill -f gunicorn || true
pkill -f uvicorn || true
sleep 2

# Start application in background
echo "Starting application..."
nohup python start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &

# Wait a moment
sleep 3

# Check if it's running
ps aux | grep start_project | grep -v grep

# View logs
tail -20 logs/start_project.log
```

## Step 5: Verify Everything is Working

```bash
# Check application health
curl http://localhost:8000/api/health

# Check if bots are running
ps aux | grep live_demo | grep -v grep

# Check if gunicorn is running
ps aux | grep gunicorn | grep -v grep

# Check port 8000
netstat -tuln | grep 8000
```

## Quick Status Check

```bash
# One-liner to check everything
cd /home/azureuser/MetaStackerBandit && \
echo "=== Repository ===" && ls -la .git 2>/dev/null && echo "✅ Repo exists" || echo "❌ Repo missing" && \
echo "=== Python ===" && source venv/bin/activate && python --version && echo "✅ Python OK" && \
echo "=== Application ===" && ps aux | grep start_project | grep -v grep && echo "✅ App running" || echo "❌ App not running" && \
echo "=== Health ===" && curl -s http://localhost:8000/api/health && echo "✅ Health OK" || echo "❌ Health check failed"
```

## View Logs

```bash
# Application log
tail -f /home/azureuser/MetaStackerBandit/logs/start_project.log

# Bot logs (if available)
ls -la /home/azureuser/MetaStackerBandit/paper_trading_outputs/
```

## Restart Application

```bash
cd /home/azureuser/MetaStackerBandit
source venv/bin/activate

# Stop
pkill -f "python.*start_project.py"
pkill -f gunicorn
sleep 2

# Start
nohup python start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &
tail -f logs/start_project.log
```

