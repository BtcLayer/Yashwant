#!/bin/bash
# Deployment script for MetaStackerBandit on VM
set -e

echo "=========================================="
echo "🚀 MetaStackerBandit VM Deployment"
echo "=========================================="
echo ""

PROJECT_DIR="/home/azureuser/MetaStackerBandit"
cd "$PROJECT_DIR"

echo "📦 Step 1: Installing system dependencies..."
sudo apt-get update

# Check if nodejs is already installed (from NodeSource)
if command -v nodejs &> /dev/null; then
    echo "✅ Node.js already installed: $(nodejs --version)"
    # npm comes bundled with NodeSource nodejs, check if it exists
    if ! command -v npm &> /dev/null; then
        echo "⚠️  npm not found, installing npm separately..."
        sudo apt-get install -y npm
    else
        echo "✅ npm already available: $(npm --version)"
    fi
    # Install other dependencies
    sudo apt-get install -y python3.13 python3.13-venv python3-pip build-essential git curl
else
    # Install everything including nodejs
    sudo apt-get install -y python3.13 python3.13-venv python3-pip nodejs npm build-essential git curl
fi

# Verify installations
echo "✅ Python version: $(python3.13 --version)"
echo "✅ Node.js version: $(nodejs --version)"
echo "✅ npm version: $(npm --version)"
echo ""

echo "📦 Step 2: Setting up Python virtual environment..."
python3.13 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

echo "📦 Step 3: Installing Python dependencies..."
pip install -r requirements.txt
echo "✅ Python dependencies installed"
echo ""

echo "📦 Step 4: Installing Node.js dependencies..."
cd frontend
npm install
echo "✅ Node.js dependencies installed"
echo ""

echo "📦 Step 5: Building React frontend..."
# Copy root .env to frontend/.env for React Create App to read
# React Create App reads .env from frontend/ directory
cp .env frontend/.env
# Source .env to export variables, then build
set -a
source .env
set +a
npm run build
cd ..
echo "✅ Frontend built successfully"
echo ""

echo "📦 Step 6: Creating necessary directories..."
mkdir -p paper_trading_outputs/sheets_fallback
mkdir -p logs
echo "✅ Directories created"
echo ""

echo "📦 Step 7: Setting up environment variables..."
export PYTHONPATH="$PROJECT_DIR"
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMPY_MKL=1

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚠️  .env file not found, creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
        echo "⚠️  Please update .env with your actual credentials"
    else
        echo "⚠️  .env.example not found, creating basic .env..."
        cat > .env << EOF
# Trading Bot Configuration
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
DASHBOARD_PASSWORD=metastacker2024
EOF
    fi
fi
echo ""

echo "📦 Step 8: Using start_project.py for startup..."
echo "✅ start_project.py will be used for production deployment"
echo "   Usage: python start_project.py --gunicorn --daemon"
echo ""

echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "📋 Next Steps:"
echo "   1. Update .env file with your credentials:"
echo "      nano $PROJECT_DIR/.env"
echo ""
echo "   2. Start the application:"
echo "      cd $PROJECT_DIR"
echo "      source venv/bin/activate"
echo "      python start_project.py --gunicorn --daemon"
echo ""
echo "   3. Or run in background with nohup:"
echo "      nohup python start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &"
echo ""
echo "   4. Access the application:"
echo "      http://40.88.15.47:8000"
echo ""
echo "   5. Check logs:"
echo "      tail -f logs/trading-bots.log"
echo "      tail -f logs/app.log"
echo ""
echo "=========================================="

