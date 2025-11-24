# GitHub CI/CD Setup for Azure VM Deployment

This guide explains how to set up automated deployment to the Azure VM using GitHub Actions.

## Prerequisites

- Azure VM running and accessible
- SSH access to the VM
- GitHub repository with Actions enabled

## Step 1: Generate SSH Key Pair

On your local machine, generate an SSH key pair (if you don't already have one):

```bash
ssh-keygen -t ed25519 -C "github-actions-vm-deploy" -f ~/.ssh/github_actions_vm_key
```

This creates:

- `~/.ssh/github_actions_vm_key` (private key - keep secret!)
- `~/.ssh/github_actions_vm_key.pub` (public key - add to VM)

## Step 2: Add Public Key to VM

Copy the public key to the VM:

```bash
# Copy public key to VM
ssh-copy-id -i ~/.ssh/github_actions_vm_key.pub azureuser@40.88.15.47

# Or manually:
cat ~/.ssh/github_actions_vm_key.pub | ssh azureuser@40.88.15.47 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

## Step 3: Add Private Key to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `VM_SSH_PRIVATE_KEY`
5. Value: Copy the entire contents of `~/.ssh/github_actions_vm_key` (the private key)

   ```bash
   cat ~/.ssh/github_actions_vm_key
   ```

6. Click **Add secret**

## Step 4: Verify SSH Connection

Test that the SSH key works:

```bash
ssh -i ~/.ssh/github_actions_vm_key azureuser@40.88.15.47 "echo 'SSH connection successful!'"
```

## Step 5: Update VM Host IP (if needed)

If your VM IP changes, update it in `.github/workflows/ci-cd-vm.yml`:

```yaml
env:
  VM_HOST: YOUR_VM_IP_HERE
```

## How It Works

When you push to `main` branch:

1. **Build & Test Job:**
   - Tests Python module imports
   - Builds React frontend (for testing)
   - Validates code before deployment

2. **Deploy to VM Job:**
   - Connects to VM via SSH
   - Pulls latest code from GitHub
   - Preserves bot data (paper_trading_outputs, logs)
   - Updates Python dependencies
   - Stops existing services (start_project.py, gunicorn, bots)
   - Starts application using `start_project.py --gunicorn --daemon`
   - Frontend auto-rebuilds if source files changed
   - Verifies deployment with health check

## Manual Trigger

You can also trigger deployment manually:

1. Go to **Actions** tab in GitHub
2. Select **MetaStackerBandit VM Deployment**
3. Click **Run workflow**
4. Select branch and click **Run workflow**

## Troubleshooting

### SSH Connection Fails

- Verify public key is in `~/.ssh/authorized_keys` on VM
- Check VM firewall allows SSH (port 22)
- Verify private key is correctly added to GitHub Secrets

### Deployment Fails

- Check GitHub Actions logs for error messages
- SSH into VM and check logs: `tail -f logs/start_project.log`
- Verify `start_project.py` is working: `python start_project.py --help`
- Check if processes are running: `ps aux | grep start_project.py`

### Health Check Fails

- Application may need more time to start (wait 30-60 seconds)
- Check if port 8000 is open in Azure NSG
- Verify gunicorn is running: `ps aux | grep gunicorn`

## Security Notes

- **Never commit private keys to the repository**
- Keep the private key secure
- Rotate keys periodically
- Use separate keys for different environments if needed
