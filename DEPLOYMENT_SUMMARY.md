# 🚀 VM Deployment Summary

## ✅ Completed

1. **Old VM Deleted**: Successfully removed old VM and all associated resources
2. **New VM Created**: 
   - Name: `metastacker-vm`
   - Resource Group: `trading-bot-rg`
   - Location: East US
   - Size: Standard_B2s (2 vCPUs, 4 GB RAM)
   - Image: Ubuntu 22.04
3. **Network Configured**:
   - Port 8000 opened for web access
   - Public IP: **172.191.90.145**
4. **CI/CD Updated**: Workflow file updated with new VM IP
5. **Deployment Initiated**: Setup and application start commands executed

## 📋 VM Details

- **Public IP**: `172.191.90.145`
- **SSH User**: `azureuser`
- **Project Directory**: `/home/azureuser/MetaStackerBandit`

## 🌐 Access URLs

Once the application is running:

- **Frontend Dashboard**: http://172.191.90.145:8000
- **Backend API**: http://172.191.90.145:8000/api
- **Health Check**: http://172.191.90.145:8000/api/health
- **File Browser**: http://172.191.90.145:8000/files

## ⏳ Next Steps

### 1. Wait for Setup to Complete (5-10 minutes)

The VM setup is running in the background. It includes:
- System package updates
- Python 3.13 and Node.js installation
- Repository cloning
- Python virtual environment setup
- Dependency installation (Python + Node.js)

### 2. Verify Setup Status

SSH into the VM to check status:

```powershell
ssh azureuser@172.191.90.145
```

Once connected:

```bash
# Check if setup is complete
cd /home/azureuser/MetaStackerBandit
ls -la

# Check Python environment
source venv/bin/activate
python --version
pip list | head -5

# Check Node.js
cd frontend
npm list --depth=0
cd ..
```

### 3. Configure .env File

Create/update the `.env` file with your API keys:

```bash
cd /home/azureuser/MetaStackerBandit
nano .env
```

Add your Hyperliquid API configuration and other settings.

### 4. Start Application (if not already running)

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

# Monitor logs
tail -f logs/start_project.log
```

### 5. Verify Application is Running

```bash
# Check processes
ps aux | grep start_project
ps aux | grep gunicorn

# Check health
curl http://localhost:8000/api/health

# Check if bots are running
ps aux | grep "live_demo"
```

### 6. Check Application Logs

```bash
# Main application log
tail -f /home/azureuser/MetaStackerBandit/logs/start_project.log

# Bot logs (if available)
ls -la /home/azureuser/MetaStackerBandit/paper_trading_outputs/
```

## 🔍 Quick Verification Commands

### From Local Machine (PowerShell)

```powershell
# Get VM status
az vm show -g trading-bot-rg -n metastacker-vm --show-details

# Check if application is running
az vm run-command invoke -g trading-bot-rg -n metastacker-vm --command-id RunShellScript --scripts "ps aux | grep start_project"

# Check health endpoint
az vm run-command invoke -g trading-bot-rg -n metastacker-vm --command-id RunShellScript --scripts "curl -s http://localhost:8000/api/health"

# View recent logs
az vm run-command invoke -g trading-bot-rg -n metastacker-vm --command-id RunShellScript --scripts "tail -20 /home/azureuser/MetaStackerBandit/logs/start_project.log"
```

### From VM (SSH)

```bash
# SSH into VM
ssh azureuser@172.191.90.145

# Quick status check
cd /home/azureuser/MetaStackerBandit
source venv/bin/activate
ps aux | grep -E "(start_project|gunicorn|live_demo)" | grep -v grep

# Check logs
tail -30 logs/start_project.log

# Test health
curl http://localhost:8000/api/health
```

## 🛠️ Troubleshooting

### Application Not Starting

1. Check logs: `tail -f logs/start_project.log`
2. Verify dependencies: `pip list` and `npm list`
3. Check port availability: `netstat -tuln | grep 8000`
4. Verify .env file exists and has correct configuration

### Bots Not Running

1. Check bot processes: `ps aux | grep live_demo`
2. Check bot logs in `paper_trading_outputs/logs/`
3. Verify Hyperliquid API keys in `.env`
4. Check network connectivity: `curl https://api.hyperliquid.xyz/info`

### Port 8000 Not Accessible

1. Verify NSG rule: `az network nsg rule list -g trading-bot-rg --nsg-name metastacker-vmNSG`
2. Check VM firewall: `sudo ufw status`
3. Verify application is listening: `netstat -tuln | grep 8000`

## 📝 Important Notes

1. **SSH Keys**: Auto-generated during VM creation. Check `~/.ssh/` for the key file.
2. **CI/CD**: The workflow file has been updated with the new IP. Future pushes to `main` will auto-deploy.
3. **Data Persistence**: Bot data in `paper_trading_outputs/` and `logs/` will persist across deployments.
4. **.env File**: Must be configured with your API keys before bots can run.

## 🎯 Success Indicators

✅ Application accessible at http://172.191.90.145:8000
✅ Health check returns 200 OK
✅ Bots generating data in `paper_trading_outputs/`
✅ Logs being written to `logs/` directory
✅ Frontend dashboard loads correctly
✅ File browser accessible at `/files` endpoint

---

**Deployment initiated at**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**VM IP**: 172.191.90.145
**Status**: Setup in progress (allow 5-10 minutes for complete setup)

