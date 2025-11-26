#!/bin/bash
mkdir -p /home/azureuser/.ssh
chmod 700 /home/azureuser/.ssh

# Add GitHub Actions key
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICUWX/gT5S1jKtOInXwmSaUZ6r1CWD5qj5YVyN535ZNT github-actions-vm-deploy" >> /home/azureuser/.ssh/authorized_keys

chmod 600 /home/azureuser/.ssh/authorized_keys

echo "✅ GitHub Actions SSH key added"
echo ""
echo "=== All Authorized Keys ==="
cat /home/azureuser/.ssh/authorized_keys

