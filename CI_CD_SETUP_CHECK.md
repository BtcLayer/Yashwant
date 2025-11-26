# CI/CD Setup Status

## ✅ Completed

1. **Workflow File Updated**: `.github/workflows/ci-cd-vm.yml` has been updated with new VM IP:
   - `VM_HOST: 172.191.90.145` ✅

## ⚠️ Action Required: SSH Key Setup

The new VM was created with auto-generated SSH keys, but GitHub Actions needs to use the existing `VM_SSH_PRIVATE_KEY` secret. You need to add the public key to the new VM.

### Option 1: Use Existing GitHub Secret (Recommended)

If you still have the SSH key that's stored in GitHub Secrets (`VM_SSH_PRIVATE_KEY`), add its public key to the new VM:

**Step 1: Get the public key from your local machine**

If you have the private key locally:
```bash
# On your local machine
ssh-keygen -y -f ~/.ssh/github_actions_vm_key > ~/.ssh/github_actions_vm_key.pub
cat ~/.ssh/github_actions_vm_key.pub
```

**Step 2: Add public key to VM**

```bash
# SSH into VM
ssh azureuser@172.191.90.145

# On the VM, add the public key
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "PASTE_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Option 2: Generate New SSH Key Pair

If you don't have the old key, generate a new one:

**Step 1: Generate new key pair**

```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions-vm-deploy" -f ~/.ssh/github_actions_vm_key_new
```

**Step 2: Add public key to VM**

```bash
# Copy public key to VM
ssh-copy-id -i ~/.ssh/github_actions_vm_key_new.pub azureuser@172.191.90.145

# Or manually:
cat ~/.ssh/github_actions_vm_key_new.pub | ssh azureuser@172.191.90.145 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

**Step 3: Update GitHub Secret**

1. Go to GitHub repository: **Settings** → **Secrets and variables** → **Actions**
2. Find `VM_SSH_PRIVATE_KEY` secret
3. Click **Update**
4. Paste the contents of `~/.ssh/github_actions_vm_key_new` (the private key)
5. Click **Update secret**

### Option 3: Use Azure CLI to Add Key

```powershell
# Get the public key content
$publicKey = Get-Content "$env:USERPROFILE\.ssh\github_actions_vm_key.pub" -Raw

# Add to VM via Azure CLI
az vm run-command invoke `
    -g trading-bot-rg `
    -n metastacker-vm `
    --command-id RunShellScript `
    --scripts "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$publicKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

## ✅ Verify Setup

### Test SSH Connection

```bash
# Test with the key
ssh -i ~/.ssh/github_actions_vm_key azureuser@172.191.90.145 "echo 'SSH connection successful!'"
```

### Test CI/CD

1. Make a small change to any file
2. Commit and push to `main` branch:
   ```bash
   git add .
   git commit -m "Test CI/CD deployment"
   git push origin main
   ```
3. Check GitHub Actions: Go to **Actions** tab and watch the workflow run

## 📋 Summary

- ✅ Workflow file: Updated with new IP
- ⚠️ SSH Key: Needs to be added to new VM
- ⚠️ GitHub Secret: May need updating if using new key

Once the SSH key is set up, CI/CD will work automatically on every push to `main`!

