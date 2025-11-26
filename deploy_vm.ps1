# MetaStackerBandit VM Deployment Script
# This script creates a VM and deploys the project

Write-Host "🚀 MetaStackerBandit VM Deployment" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create VM
Write-Host "📦 Step 1: Creating Azure VM..." -ForegroundColor Yellow
$vmResult = az vm create `
    --resource-group trading-bot-rg `
    --name metastacker-vm `
    --image Ubuntu2204 `
    --size Standard_B2s `
    --admin-username azureuser `
    --generate-ssh-keys `
    --public-ip-address-dns-name "metastacker-bot-$(Get-Random -Maximum 99999)" `
    --location eastus `
    --output json | ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ VM creation failed!" -ForegroundColor Red
    exit 1
}

$vmIp = $vmResult.publicIpAddress
Write-Host "✅ VM created successfully!" -ForegroundColor Green
Write-Host "   Public IP: $vmIp" -ForegroundColor Cyan
Write-Host ""

# Step 2: Open port 8000
Write-Host "🔓 Step 2: Opening port 8000..." -ForegroundColor Yellow
az vm open-port -g trading-bot-rg -n metastacker-vm --port 8000 --priority 1100
Write-Host "✅ Port 8000 opened" -ForegroundColor Green
Write-Host ""

# Step 3: Wait for VM to be ready
Write-Host "⏳ Step 3: Waiting for VM to be ready (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Step 4: Setup script
Write-Host "📦 Step 4: Setting up VM (this may take 5-10 minutes)..." -ForegroundColor Yellow
$setupScript = @"
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
echo "📁 Setting up project directory: `$PROJECT_DIR"
mkdir -p "`$PROJECT_DIR"
cd "`$PROJECT_DIR"

# Clone repository
echo "📥 Cloning repository..."
git clone https://github.com/anythingai/MetaStackerBandit.git .

# Create Python virtual environment
echo "🐍 Setting up Python virtual environment..."
python3.13 -m venv venv
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
    echo "⚠️  .env file not found. Creating basic .env file..."
    touch .env
    echo "   Please update .env with your API keys and configuration"
fi

echo "✅ VM setup complete!"
"@

$setupResult = az vm run-command invoke `
    -g trading-bot-rg `
    -n metastacker-vm `
    --command-id RunShellScript `
    --scripts $setupScript `
    --output json | ConvertFrom-Json

if ($setupResult.value[0].code -ne "ProvisioningState/succeeded") {
    Write-Host "⚠️  Setup may have issues. Check output:" -ForegroundColor Yellow
    Write-Host $setupResult.value[0].message
} else {
    Write-Host "✅ VM setup complete!" -ForegroundColor Green
}
Write-Host ""

# Step 5: Start application
Write-Host "🚀 Step 5: Starting application..." -ForegroundColor Yellow
$startScript = @"
#!/bin/bash
set -e

cd /home/azureuser/MetaStackerBandit
source venv/bin/activate

# Stop any existing processes
pkill -f "python.*start_project.py" || true
pkill -f gunicorn || true
pkill -f uvicorn || true
sleep 2

# Start application
echo "🚀 Starting application..."
nohup python start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &

echo "✅ Application started!"
echo "   Check logs: tail -f logs/start_project.log"
echo "   Health check: curl http://localhost:8000/api/health"
"@

$startResult = az vm run-command invoke `
    -g trading-bot-rg `
    -n metastacker-vm `
    --command-id RunShellScript `
    --scripts $startScript `
    --output json | ConvertFrom-Json

Write-Host "✅ Application deployment initiated!" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🌐 VM Public IP: $vmIp" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Access Points:" -ForegroundColor Yellow
Write-Host "   - Frontend Dashboard: http://$vmIp:8000" -ForegroundColor White
Write-Host "   - Backend API:        http://$vmIp:8000/api" -ForegroundColor White
Write-Host "   - Health Check:       http://$vmIp:8000/api/health" -ForegroundColor White
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Update .env file on VM with your API keys" -ForegroundColor White
Write-Host "   2. Update CI/CD workflow with new IP: $vmIp" -ForegroundColor White
Write-Host "   3. Check application logs: ssh azureuser@$vmIp 'tail -f /home/azureuser/MetaStackerBandit/logs/start_project.log'" -ForegroundColor White
Write-Host ""

