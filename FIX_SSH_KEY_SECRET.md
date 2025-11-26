# Fix GitHub Actions SSH Key Secret

## Problem
The CI/CD deployment is failing with:
```
Load key "/home/runner/.ssh/vm_key": error in libcrypto
Permission denied (publickey)
```

This means the SSH key in GitHub Secrets is corrupted or incorrectly formatted.

## Solution

### Step 1: Get the Correct Private Key

The private key is located at: `C:\Users\YOUR_USERNAME\.ssh\github_actions_vm_key`

**Correct key content:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAlFl/4E+UtYyrTiJ18JkmlGeq9Qlg+ao+WFcjed+WTUwAAAKDEAVEQxAFR
EAAAAAtzc2gtZWQyNTUxOQAAACAlFl/4E+UtYyrTiJ18JkmlGeq9Qlg+ao+WFcjed+WTUw
AAAECMqWG3bM+01JObUJ72jHrfdPy+xn0YOxHLCOlfqe8pcCUWX/gT5S1jKtOInXwmSaUZ
6r1CWD5qj5YVyN535ZNTAAAAGGdpdGh1Yi1hY3Rpb25zLXZtLWRlcGxveQECAwQF
-----END OPENSSH PRIVATE KEY-----
```

### Step 2: Update GitHub Secret

1. Go to your GitHub repository
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Find the secret named: `VM_SSH_PRIVATE_KEY`
4. Click **Update** (pencil icon)
5. **IMPORTANT**: Delete ALL existing content in the secret value field
6. Copy the ENTIRE key content above (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`)
7. Paste it into the secret value field
8. **Ensure:**
   - No extra spaces before/after
   - No extra line breaks
   - The BEGIN and END markers are on their own lines
   - No Windows line endings (should be LF, not CRLF)
9. Click **Update secret**

### Step 3: Verify the Fix

After updating, the CI/CD workflow should work. To test:

1. Go to **Actions** tab
2. Find the failed workflow run
3. Click **Re-run all jobs** (or push a new commit)
4. The deployment should now succeed

### Alternative: Use PowerShell to Copy Key

Run this in PowerShell to copy the key to clipboard:

```powershell
Get-Content "$env:USERPROFILE\.ssh\github_actions_vm_key" | Set-Clipboard
Write-Host "✅ Key copied to clipboard! Paste it into GitHub Secrets."
```

Then paste directly into GitHub Secrets (Ctrl+V).

## Common Issues

### Issue 1: Extra Characters
- **Symptom**: Key has extra spaces or characters
- **Fix**: Copy the key exactly as shown, no modifications

### Issue 2: Wrong Line Endings
- **Symptom**: Key has Windows line endings (CRLF)
- **Fix**: GitHub Secrets should handle this, but ensure the key is pasted cleanly

### Issue 3: Missing BEGIN/END Markers
- **Symptom**: Key doesn't have the header/footer
- **Fix**: Include the entire key including BEGIN and END lines

### Issue 4: Wrong Key
- **Symptom**: Using a different SSH key
- **Fix**: Make sure you're using `github_actions_vm_key`, not `id_rsa` or another key

## Verification

After updating, the workflow should show:
- ✅ SSH connection successful
- ✅ Code pulled from GitHub
- ✅ Application deployed
- ✅ Health check passed

