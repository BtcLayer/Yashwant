# Add GitHub Actions SSH Key to VM

Since you're already SSH'd into the VM, run this command:

```bash
# Add GitHub Actions public key to authorized_keys
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICUWX/gT5S1jKtOInXwmSaUZ6r1CWD5qj5YVyN535ZNT github-actions-vm-deploy" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Verify it was added
echo "✅ Key added. Current authorized keys:"
cat ~/.ssh/authorized_keys
```

This will add the GitHub Actions SSH key so CI/CD can deploy to the VM.

After running this, CI/CD will work automatically on every push to `main`!

