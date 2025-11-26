# VM Deployment Status

## ✅ Completed Steps

1. **VM Deleted**: Old VM and associated resources were successfully deleted
2. **VM Created**: New Azure VM `metastacker-vm` has been created in resource group `trading-bot-rg`
3. **Port Opened**: Port 8000 has been opened for web access
4. **Setup Scripts Created**: 
   - `vm_setup.sh` - Bash script for VM setup
   - `deploy_vm.ps1` - PowerShell deployment script

## 🔄 In Progress / Next Steps

### Step 1: Get VM IP Address

Run this command to get your VM's public IP:

```powershell
az vm list-ip-addresses -g trading-bot-rg -n metastacker-vm --output table
```

Or:

```powershell
az vm show -d -g trading-bot-rg -n metastacker-vm --query publicIps -o tsv
```

### Step 2: Verify VM Setup

SSH into the VM and verify setup:

```powershell
# Get the IP first
$vmIp = az vm show -d -g trading-bot-rg -n metastacker-vm --query publicIps -o tsv
ssh azureuser@$vmIp
```

Once connected, check:

```bash
# Check if repository is cloned
cd /home/azureuser/MetaStackerBandit
ls -la

# Check if Python venv exists
ls -la venv/

# Check if dependencies are installed
source venv/bin/activate
python --version
pip list | head -10
```

### Step 3: Complete Setup (if needed)

If the setup didn't complete, run this on the VM:

```bash
cd /home/azureuser/MetaStackerBandit

# If repo not cloned
git clone https://github.com/anythingai/MetaStackerBandit.git .

# Setup Python environment
python3.13 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Setup Node.js
cd frontend
npm install
cd ..

# Create directories
mkdir -p paper_trading_outputs/sheets_fallback
mkdir -p logs
```

### Step 4: Configure .env File

Create/update the `.env` file on the VM with your API keys:

```bash
cd /home/azureuser/MetaStackerBandit
nano .env
```

Add your Hyperliquid API keys and other configuration.

### Step 5: Start the Application

```bash
cd /home/azureuser/MetaStackerBandit
source venv/bin/activate

# Stop any existing processes
pkill -f "python.*start_project.py" || true
pkill -f gunicorn || true
pkill -f uvicorn || true
sleep 2

# Start application
nohup python start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &

# Check logs
tail -f logs/start_project.log
```

### Step 6: Verify Deployment

```bash
# Check if application is running
ps aux | grep start_project

# Check health
curl http://localhost:8000/api/health

# Check if bots are running
ps aux | grep "live_demo"
```

### Step 7: Update CI/CD Workflow

Once you have the VM IP, update `.github/workflows/ci-cd-vm.yml`:

```yaml
env:
  VM_HOST: YOUR_NEW_VM_IP_HERE  # Update this line
```

### Step 8: Access the Application

Once running, access at:
- **Frontend Dashboard**: `http://YOUR_VM_IP:8000`
- **Backend API**: `http://YOUR_VM_IP:8000/api`
- **Health Check**: `http://YOUR_VM_IP:8000/api/health`
- **File Browser**: `http://YOUR_VM_IP:8000/files`

## 🔍 Troubleshooting

### Check VM Status

```powershell
az vm show -g trading-bot-rg -n metastacker-vm --show-details
```

### Check Application Logs

```bash
ssh azureuser@YOUR_VM_IP
tail -f /home/azureuser/MetaStackerBandit/logs/start_project.log
```

### Restart Application

```bash
ssh azureuser@YOUR_VM_IP
cd /home/azureuser/MetaStackerBandit
source venv/bin/activate
pkill -f "python.*start_project.py"
pkill -f gunicorn
sleep 2
nohup python start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &
```

### Check Port 8000

```powershell
az vm run-command invoke -g trading-bot-rg -n metastacker-vm --command-id RunShellScript --scripts "netstat -tuln | grep 8000"
```

## 📝 Notes

- The VM was created with Ubuntu 22.04
- Size: Standard_B2s (2 vCPUs, 4 GB RAM)
- Location: East US
- SSH keys were auto-generated during VM creation
- Port 8000 is open for web traffic

## 🚀 Quick Commands Reference

```powershell
# Get VM IP
az vm show -d -g trading-bot-rg -n metastacker-vm --query publicIps -o tsv

# SSH into VM
ssh azureuser@$(az vm show -d -g trading-bot-rg -n metastacker-vm --query publicIps -o tsv)

# Execute command on VM
az vm run-command invoke -g trading-bot-rg -n metastacker-vm --command-id RunShellScript --scripts "YOUR_COMMAND"

# Check VM status
az vm get-instance-view -g trading-bot-rg -n metastacker-vm --query instanceView.statuses
```

