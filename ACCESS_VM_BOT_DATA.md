# Accessing Bot Data

## Access Information

### VM (Production)
- **Host**: `40.88.15.47`
- **User**: `azureuser`
- **Project Directory**: `/home/azureuser/MetaStackerBandit`
- **Frontend Dashboard**: http://40.88.15.47:8000
- **Backend API**: http://40.88.15.47:8000/api
- **File Browser**: http://40.88.15.47:8000/files

### Local Development
- **Frontend Dashboard**: http://localhost:8000
- **Backend API**: http://localhost:8000/api
- **File Browser**: http://localhost:8000/files

**Note:** The file browser works the same way locally and on VM - just use the appropriate URL!

## Data Storage Locations

Bot data is stored in these directories on the VM:

- **`paper_trading_outputs/`** - Trading logs, signals, executions, JSONL files
  - `5m/` - 5-minute bot data
  - `1h/` - 1-hour bot data
  - `12h/` - 12-hour bot data
  - `24h/` - 24-hour bot data
  - `logs/` - Bot-specific logs
  - `models/` - Model weights and artifacts

- **`logs/`** - Application logs, startup logs, error logs

## Access Methods

### 1. Via Web File Browser (Easiest - NEW!)

**Access the file browser:**

**On VM:**
```
http://40.88.15.47:8000/files
```

**Locally (when running `python start_project.py`):**
```
http://localhost:8000/files
```

**Features:**
- Browse all bot data files via web interface
- Download files directly from browser
- Navigate directories like FTP
- View file sizes and modification dates
- Switch between `paper_trading_outputs` and `logs` directories

**Usage:**
- Navigate: Click on directories to browse
- Download: Click "Download" link next to files
- Switch base: Use dropdown to switch between directories
- Breadcrumb: Click breadcrumb links to go back

**Example URLs (VM):**
```
http://40.88.15.47:8000/files                                    # Root of paper_trading_outputs
http://40.88.15.47:8000/files?base=logs                        # Root of logs directory
http://40.88.15.47:8000/files?path=5m/logs&base=paper_trading_outputs  # Specific path
```

**Example URLs (Local):**
```
http://localhost:8000/files                                      # Root of paper_trading_outputs
http://localhost:8000/files?base=logs                          # Root of logs directory
http://localhost:8000/files?path=5m/logs&base=paper_trading_outputs  # Specific path
```

### 2. Via Frontend Dashboard

**Access the web dashboard:**
```
http://40.88.15.47:8000
```

**Features:**
- View real-time bot status
- View trading signals and equity
- View logs and emitters per bot
- Export logs as CSV/JSON
- Filter by date, bot version, log type

**Navigation:**
- Click on bot tabs (5m, 1h, 12h, 24h) to see per-bot data
- Click "Logs & Emitters" tab for system-wide logs
- Use date filters and export buttons

### 3. Via Backend API

**Health Check:**
```bash
curl http://40.88.15.47:8000/api/health
```

**Dashboard Summary:**
```bash
curl http://40.88.15.47:8000/api/dashboard/summary
```

**Get Log Types:**
```bash
curl http://40.88.15.47:8000/api/logs/types
```

**Get Logs for Specific Type:**
```bash
# Get signals logs
curl "http://40.88.15.47:8000/api/logs/signals?bot_version=5m&limit=100"

# Get execution logs
curl "http://40.88.15.47:8000/api/logs/execution?bot_version=1h&date=2025-11-22"

# Get health logs
curl "http://40.88.15.47:8000/api/logs/health?bot_version=12h"
```

**API Documentation:**
```
http://40.88.15.47:8000/docs
```

**File Browser API:**
```bash
# List files in a directory
curl "http://40.88.15.47:8000/api/files?path=5m/logs&base=paper_trading_outputs"

# Download a file
curl "http://40.88.15.47:8000/api/files/download/5m/logs/signals/date=2025-11-22/asset=BTCUSDT/signals.jsonl.gz?base=paper_trading_outputs" -o signals.jsonl.gz
```

### 4. Via SSH (Direct File Access)

**Connect to VM:**
```bash
ssh azureuser@40.88.15.47
```

**Navigate to project:**
```bash
cd /home/azureuser/MetaStackerBandit
```

**View data directories:**
```bash
# List all bot data
ls -lh paper_trading_outputs/

# List by timeframe
ls -lh paper_trading_outputs/5m/
ls -lh paper_trading_outputs/1h/
ls -lh paper_trading_outputs/12h/
ls -lh paper_trading_outputs/24h/

# View logs
ls -lh logs/
```

**View recent logs:**
```bash
# Start project log
tail -f logs/start_project.log

# Unified runner logs
tail -f paper_trading_outputs/unified_runner_5m.log
tail -f paper_trading_outputs/unified_runner_1h.log
tail -f paper_trading_outputs/unified_runner_12h.log
tail -f paper_trading_outputs/unified_runner_24h.log

# Error logs
tail -f paper_trading_outputs/5m/live_errors.log
```

**View JSONL log files:**
```bash
# List log files
find paper_trading_outputs -name "*.jsonl*" -type f | head -20

# View a specific log file
zcat paper_trading_outputs/5m/logs/signals/date=2025-11-22/asset=BTCUSDT/signals.jsonl.gz | head -10

# Count log entries
zcat paper_trading_outputs/5m/logs/signals/date=2025-11-22/asset=BTCUSDT/signals.jsonl.gz | wc -l
```

**Check data size:**
```bash
# Total size
du -sh paper_trading_outputs/

# Size by timeframe
du -sh paper_trading_outputs/5m/
du -sh paper_trading_outputs/1h/
du -sh paper_trading_outputs/12h/
du -sh paper_trading_outputs/24h/

# File counts
find paper_trading_outputs -type f | wc -l
find paper_trading_outputs/5m -type f | wc -l
```

### 5. Download Data to Local Machine

**Using SCP (Secure Copy):**

```bash
# Download entire paper_trading_outputs directory
scp -r azureuser@40.88.15.47:/home/azureuser/MetaStackerBandit/paper_trading_outputs ./

# Download specific timeframe
scp -r azureuser@40.88.15.47:/home/azureuser/MetaStackerBandit/paper_trading_outputs/5m ./paper_trading_outputs_5m

# Download logs directory
scp -r azureuser@40.88.15.47:/home/azureuser/MetaStackerBandit/logs ./
```

**Using rsync (More efficient for large files):**

```bash
# Sync entire directory (excludes already downloaded files)
rsync -avz azureuser@40.88.15.47:/home/azureuser/MetaStackerBandit/paper_trading_outputs/ ./paper_trading_outputs/

# Sync specific timeframe
rsync -avz azureuser@40.88.15.47:/home/azureuser/MetaStackerBandit/paper_trading_outputs/5m/ ./paper_trading_outputs/5m/
```

**Using tar over SSH (Best for large directories):**

```bash
# Create compressed archive and download
ssh azureuser@40.88.15.47 "cd /home/azureuser/MetaStackerBandit && tar -czf - paper_trading_outputs" | tar -xzf - -C ./

# Download specific timeframe
ssh azureuser@40.88.15.47 "cd /home/azureuser/MetaStackerBandit && tar -czf - paper_trading_outputs/5m" | tar -xzf - -C ./
```

### 6. Using Python Scripts

**Check VM Bot Status:**
```bash
# Run the built-in check script
python check_vm_bots.py
```

This script will:
- Check if bots are running
- Check for errors in logs
- Show data generation status
- Check backend health

**Custom Python Script:**
```python
import subprocess
import json

# SSH command to get data
command = "ssh azureuser@40.88.15.47 'cd /home/azureuser/MetaStackerBandit && find paper_trading_outputs -name \"*.jsonl.gz\" | head -10'"
result = subprocess.run(command, shell=True, capture_output=True, text=True)
print(result.stdout)
```

### 7. Via GitHub Actions Artifacts

After each deployment, GitHub Actions automatically downloads `paper_trading_outputs/` as an artifact:

1. Go to your GitHub repository
2. Click on "Actions" tab
3. Select the latest workflow run
4. Scroll down to "Artifacts"
5. Download `paper_trading_outputs` artifact

**Note:** This is a backup/snapshot, not real-time data.

## Quick Reference Commands

### Access File Browser
```bash
# Open in browser
# http://40.88.15.47:8000/files

# Or via API
curl "http://40.88.15.47:8000/api/files?base=paper_trading_outputs"
```

### Check Bot Status
```bash
# Via SSH
ssh azureuser@40.88.15.47 "cd /home/azureuser/MetaStackerBandit && ps aux | grep run_unified_bots"

# Via API
curl http://40.88.15.47:8000/api/dashboard/summary | jq
```

### View Recent Logs
```bash
# Via SSH
ssh azureuser@40.88.15.47 "cd /home/azureuser/MetaStackerBandit && tail -100 logs/start_project.log"

# Via API (signals)
curl "http://40.88.15.47:8000/api/logs/signals?bot_version=5m&limit=10"
```

### Download Latest Data
```bash
# Download all data
rsync -avz azureuser@40.88.15.47:/home/azureuser/MetaStackerBandit/paper_trading_outputs/ ./vm_data/

# Download only today's data
ssh azureuser@40.88.15.47 "cd /home/azureuser/MetaStackerBandit && find paper_trading_outputs -name '*2025-11-22*' -type f" | xargs -I {} scp azureuser@40.88.15.47:{} ./
```

## Data Structure

```
paper_trading_outputs/
├── 5m/                          # 5-minute bot data
│   ├── logs/
│   │   ├── signals/
│   │   │   └── date=2025-11-22/
│   │   │       └── asset=BTCUSDT/
│   │   │           └── signals.jsonl.gz
│   │   ├── execution/
│   │   ├── health/
│   │   ├── ensemble/
│   │   └── ...
│   ├── live_errors.log
│   └── ...
├── 1h/                          # 1-hour bot data
├── 12h/                         # 12-hour bot data
├── 24h/                         # 24-hour bot data
├── models/                      # Model weights
└── unified_runner_*.log         # Unified runner logs

logs/
├── start_project.log           # Main startup log
└── trading-bots.log            # Bot execution log
```

## Log Types Available

- **signals** - Trading signals and predictions
- **execution** - Order execution details
- **health** - Bot health metrics
- **ensemble** - Ensemble predictions
- **equity** - Equity tracking
- **costs** - Trading costs
- **order_intent** - Order intentions
- **feature_log** - Feature engineering logs
- **calibration** - Model calibration
- **hyperliquid_fill** - Hyperliquid fill data
- **overlay_status** - Overlay signal status
- **alerts** - System alerts

## Tips

1. **Use Frontend Dashboard** for quick visual inspection
2. **Use API** for programmatic access and automation
3. **Use SSH** for deep debugging and file inspection
4. **Use rsync** for efficient data downloads
5. **Use GitHub Actions artifacts** as backup snapshots

## Troubleshooting

**Can't access dashboard:**
```bash
# Check if backend is running
ssh azureuser@40.88.15.47 "curl http://localhost:8000/api/health"

# Check firewall/port
ssh azureuser@40.88.15.47 "netstat -tlnp | grep 8000"
```

**No data in paper_trading_outputs:**
```bash
# Check if bots are running
ssh azureuser@40.88.15.47 "ps aux | grep run_unified_bots"

# Check for errors
ssh azureuser@40.88.15.47 "tail -100 paper_trading_outputs/unified_runner_5m.log"
```

**Can't download via SCP:**
- Check SSH key permissions
- Verify VM is accessible
- Try using rsync instead

## Security Notes

- VM is accessible on port 8000 (HTTP, not HTTPS)
- Consider setting up HTTPS/SSL for production
- SSH access requires proper authentication
- Data is not encrypted in transit (use VPN or SSH tunnel for sensitive data)

