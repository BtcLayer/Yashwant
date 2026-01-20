#!/bin/bash
set -e

echo "🚀 Starting VM setup for MetaStackerBandit..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3.13 python3.13-venv python3-pip build-essential git curl nodejs npm

# Verify installations
echo "✅ Verifying installations..."
python3.13 --version
node --version
npm --version

# Create project directory
PROJECT_DIR="/home/azureuser/MetaStackerBandit"
echo "📁 Setting up project directory: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Clone repository
echo "📥 Cloning repository..."
if [ -d ".git" ]; then
    echo "   Repository already exists, pulling latest..."
    git fetch origin
    git reset --hard origin/main
else
    git clone https://github.com/anythingai/MetaStackerBandit.git .
fi

# Create Python virtual environment
echo "🐍 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3.13 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p paper_trading_outputs/sheets_fallback
mkdir -p logs

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example if available..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "   Please update .env with your API keys and configuration"
    else
        echo "   Creating basic .env file..."
        touch .env
    fi
fi

echo "✅ VM setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Update .env file with your API keys"
echo "   2. Start the application: cd $PROJECT_DIR && source venv/bin/activate && python start_project.py --gunicorn --daemon"
echo ""

