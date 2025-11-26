# CI/CD Deployment Checklist

## ✅ Verified Components

### 1. SSH Connection
- ✅ **SSH Key**: `VM_SSH_PRIVATE_KEY` secret in GitHub
- ✅ **VM Access**: Key added to VM's `~/.ssh/authorized_keys`
- ✅ **VM IP**: `172.191.90.145` configured in workflow
- ✅ **VM User**: `azureuser` configured

### 2. Repository Access
- ✅ **Private Repo**: Using `GITHUB_TOKEN` for authentication
- ✅ **Clone Logic**: Checks if repo exists, clones if not
- ✅ **Pull Logic**: Updates remote URL to use token, then pulls

### 3. System Dependencies
- ✅ **Python**: Installs `python3.13` or falls back to `python3`
- ✅ **Venv Package**: Installs `python3.13-venv` or `python3-venv`
- ✅ **Build Tools**: Installs `build-essential`
- ✅ **Node.js**: Installs `nodejs` and `npm`
- ✅ **Other Tools**: Installs `git`, `curl`

### 4. Virtual Environment
- ✅ **Check**: Verifies if `venv` directory exists
- ✅ **Create**: Creates venv if missing (tries python3.13, falls back to python3)
- ✅ **Activate**: Activates venv before installing dependencies

### 5. Python Dependencies
- ✅ **Upgrade pip**: Upgrades pip, setuptools, wheel
- ✅ **Install**: Installs from `requirements.txt`

### 6. Node.js Dependencies
- ✅ **Check**: Verifies if `frontend/node_modules` exists
- ✅ **Install**: Installs npm packages if missing

### 7. Data Preservation
- ✅ **Backup**: Backs up `paper_trading_outputs` and `logs` before git reset
- ✅ **Restore**: Restores data directories after code update
- ✅ **Preserve**: `.env` file is excluded from git clean

### 8. Application Startup
- ✅ **Stop Services**: Kills existing processes (start_project.py, gunicorn, uvicorn, bots)
- ✅ **Create Directories**: Ensures `logs` and `paper_trading_outputs` exist
- ✅ **Start Command**: `python start_project.py --gunicorn --daemon`
- ✅ **Logging**: Outputs to `logs/start_project.log`

### 9. Health Check
- ✅ **Wait Time**: 10s initial wait + 15s before first check
- ✅ **Retries**: 8 attempts with 10s intervals (total ~90s wait time)
- ✅ **Endpoint**: Checks `http://localhost:8000/api/health`
- ✅ **Graceful Failure**: Warns but doesn't fail if health check times out

### 10. Network
- ✅ **Port 8000**: Opened in Azure NSG
- ✅ **Public IP**: `172.191.90.145` accessible

## ⚠️ Potential Issues & Solutions

### Issue 1: Python 3.13 Not Available
**Status**: ✅ **HANDLED**
- Workflow tries `python3.13`, falls back to `python3`
- Installs appropriate venv package

### Issue 2: Missing .env File
**Status**: ⚠️ **MANUAL SETUP REQUIRED**
- `.env` file is preserved during deployment
- But if it doesn't exist, bots won't have API keys
- **Action**: User needs to create `.env` on VM with API keys

### Issue 3: First Deployment Takes Long
**Status**: ✅ **EXPECTED**
- First run installs all system packages (5-10 min)
- Creates venv and installs dependencies (5-10 min)
- Builds frontend (2-5 min)
- **Total**: 15-25 minutes for first deployment

### Issue 4: Health Check May Fail Initially
**Status**: ✅ **HANDLED**
- Workflow waits up to 90 seconds
- Gives time for frontend build and service startup
- Doesn't fail workflow if health check times out (just warns)

### Issue 5: Frontend Build Time
**Status**: ✅ **HANDLED**
- `start_project.py` auto-builds frontend if needed
- Health check waits long enough for build to complete

### Issue 6: Port Already in Use
**Status**: ✅ **HANDLED**
- `start_project.py` kills processes on port 8000
- Workflow also kills existing services before starting

## 🔍 Verification Steps

After deployment, verify:

1. **SSH into VM**:
   ```bash
   ssh azureuser@172.191.90.145
   ```

2. **Check Application**:
   ```bash
   ps aux | grep start_project
   ps aux | grep gunicorn
   ```

3. **Check Logs**:
   ```bash
   tail -f /home/azureuser/MetaStackerBandit/logs/start_project.log
   ```

4. **Test Health**:
   ```bash
   curl http://localhost:8000/api/health
   ```

5. **Access Application**:
   - Frontend: http://172.191.90.145:8000
   - API: http://172.191.90.145:8000/api
   - Health: http://172.191.90.145:8000/api/health

## 📋 Pre-Deployment Checklist

Before pushing to trigger deployment:

- [x] VM created and accessible
- [x] SSH key added to VM
- [x] SSH key in GitHub Secrets
- [x] Workflow file updated with correct VM IP
- [ ] `.env` file created on VM (if not exists)
- [x] Port 8000 opened in Azure NSG
- [x] Repository is accessible (private repo token configured)

## ✅ Overall Status

**READY FOR DEPLOYMENT** ✅

All critical components are configured. The workflow should work end-to-end. The first deployment will take longer due to initial setup, but subsequent deployments will be faster.

