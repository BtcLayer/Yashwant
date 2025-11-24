# Bot Data Management

## How Bot Data is Handled During Deployment

### ⚠️ CRITICAL: Your Bot Data is Safe!

When you push code to GitHub and it deploys to the VM, **your bot data is NOT overwritten**. Here's how it works:

## Data Storage Locations

Bot data is stored in these directories on the VM:

- **`paper_trading_outputs/`** - All trading logs, signals, executions, JSONL files
- **`logs/`** - Application logs, bot logs, startup logs

## Protection Mechanisms

### 1. `.gitignore` Protection

The `.gitignore` file ensures bot data is **never committed** to git:

```
paper_trading_outputs/
logs/
*.jsonl
*.jsonl.gz
*.csv
*.log
```

**This means:**
- Bot data is **never** in your git repository
- Local repo doesn't have VM's historical data
- Each deployment preserves existing VM data

### 2. Deployment Process Protection

The GitHub Actions workflow now includes **automatic data backup and restore**:

```bash
# Before git reset:
1. Backup paper_trading_outputs/ to /tmp/
2. Backup logs/ to /tmp/

# After git reset:
3. Restore paper_trading_outputs/ from backup
4. Restore logs/ from backup
```

### 3. Git Reset Behavior

`git reset --hard origin/main` only affects **tracked files**:
- ✅ Code files (Python, JS, etc.) - **Updated from remote**
- ✅ Configuration files - **Updated from remote**
- ❌ Ignored files (bot data) - **NOT TOUCHED**
- ❌ Untracked files - **NOT TOUCHED**

## How It Works

### Scenario: You Push Code to GitHub

1. **GitHub Actions triggers** deployment
2. **VM receives** deployment command
3. **Backup phase:**
   - `paper_trading_outputs/` → `/tmp/vm_data_backup/`
   - `logs/` → `/tmp/vm_data_backup/`
4. **Code update phase:**
   - `git fetch origin`
   - `git reset --hard origin/main` (only updates tracked files)
   - `git clean` (removes untracked files, but excludes data dirs)
5. **Restore phase:**
   - Restore `paper_trading_outputs/` from backup
   - Restore `logs/` from backup
6. **Restart services:**
   - Bots continue with all historical data intact

### Result

✅ **Code updated** from your local repository  
✅ **Bot data preserved** from VM's long-running history  
✅ **No data loss** - all accumulated data remains

## Data Flow

```
Local Development:
├── Code changes → Git → GitHub
└── NO bot data (data only on VM)

VM Production:
├── Code from GitHub → Updated
└── Bot data → Accumulates over time → Preserved
```

## Important Notes

1. **Bot data NEVER syncs from local to VM**
   - Your local repo doesn't have VM's data
   - VM data accumulates independently

2. **Bot data NEVER syncs from VM to local**
   - VM data stays on VM
   - GitHub Actions downloads as artifacts (backup only)

3. **Each deployment preserves VM data**
   - Data accumulates continuously
   - Historical data is never lost
   - Only code gets updated

## Verification

To verify your data is safe:

```bash
# SSH into VM
ssh azureuser@40.88.15.47

# Check data directories
ls -lh paper_trading_outputs/
ls -lh logs/

# Check data after deployment
# Data should still be there after git reset
```

## Backup Strategy

While data is preserved during deployments, consider:

1. **Regular backups** of `paper_trading_outputs/`
2. **GitHub Actions artifacts** (downloads data after each deployment)
3. **External backup** to cloud storage (optional)

## Summary

✅ **Your bot data is SAFE**  
✅ **Each deployment preserves existing data**  
✅ **Data accumulates on VM over time**  
✅ **Local repo and VM data are separate**

The deployment process is designed to update code while preserving all accumulated bot data on the VM.

