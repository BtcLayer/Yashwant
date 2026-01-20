#!/usr/bin/env python3
"""
Check VM Bot Status
Checks if bots are running, generating data, and identifies any issues
"""

import subprocess
import sys
from pathlib import Path

VM_HOST = "40.88.15.47"
VM_USER = "azureuser"
PROJECT_DIR = "/home/azureuser/MetaStackerBandit"

def run_ssh_command(command):
    """Run SSH command on VM"""
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", f"{VM_USER}@{VM_HOST}", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "SSH command timed out"
    except Exception as e:
        return False, "", str(e)

def check_bot_processes():
    """Check if bot processes are running"""
    safe_print("\n" + "="*60)
    safe_print("1. CHECKING BOT PROCESSES")
    safe_print("="*60)
    
    command = f"cd {PROJECT_DIR} && ps aux | grep -E '(run_unified_bots|start_project|gunicorn|uvicorn)' | grep -v grep"
    success, stdout, stderr = run_ssh_command(command)
    
    if success and stdout.strip():
        safe_print("OK: Bot processes found:")
        for line in stdout.strip().split('\n'):
            if line.strip():
                parts = line.split()
                pid = parts[1] if len(parts) > 1 else "N/A"
                cmd = ' '.join(parts[10:]) if len(parts) > 10 else line
                safe_print(f"   PID {pid}: {cmd[:80]}")
    else:
        safe_print("ERROR: No bot processes found!")
        safe_print("   Bots may have crashed or not started")
    
    # Count processes
    command = f"cd {PROJECT_DIR} && ps aux | grep -E '(run_unified_bots|start_project)' | grep -v grep | wc -l"
    success, stdout, stderr = run_ssh_command(command)
    if success:
        count = int(stdout.strip()) if stdout.strip().isdigit() else 0
        print(f"\n   Total bot processes: {count}")

def check_logs_for_errors():
    """Check logs for errors, especially balance-related"""
    safe_print("\n" + "="*60)
    safe_print("2. CHECKING LOGS FOR ERRORS")
    safe_print("="*60)
    
    # Check start_project.log
    command = f"cd {PROJECT_DIR} && if [ -f logs/start_project.log ]; then tail -50 logs/start_project.log | grep -i -E '(error|exception|crash|balance|bannace|failed|traceback)' | head -10; else echo 'File not found'; fi"
    success, stdout, stderr = run_ssh_command(command)
    if stdout and stdout.strip() and "File not found" not in stdout:
        print("⚠️  Errors in start_project.log:")
        for line in stdout.strip().split('\n'):
            if line.strip():
                print(f"   {line[:100]}")
    else:
        print("✅ No errors in start_project.log")
    
    # Check trading-bots.log
    command = f"cd {PROJECT_DIR} && if [ -f logs/trading-bots.log ]; then tail -50 logs/trading-bots.log | grep -i -E '(error|exception|crash|balance|bannace|failed|traceback)' | head -10; else echo 'File not found'; fi"
    success, stdout, stderr = run_ssh_command(command)
    if stdout and stdout.strip() and "File not found" not in stdout:
        print("\n⚠️  Errors in trading-bots.log:")
        for line in stdout.strip().split('\n'):
            if line.strip():
                print(f"   {line[:100]}")
    else:
        print("✅ No errors in trading-bots.log")
    
    # Check unified runner logs
    print("\n   Checking unified runner logs...")
    for tf in ["5m", "1h", "12h", "24h"]:
        command = f"cd {PROJECT_DIR} && if [ -f paper_trading_outputs/unified_runner_{tf}.log ]; then tail -20 paper_trading_outputs/unified_runner_{tf}.log | grep -i -E '(error|exception|crash|balance|bannace|failed)' | head -5; else echo ''; fi"
        success, stdout, stderr = run_ssh_command(command)
        if stdout.strip():
            print(f"   ⚠️  {tf}: Errors found")
            for line in stdout.strip().split('\n')[:3]:
                if line.strip():
                    print(f"      {line[:80]}")
        else:
            print(f"   ✅ {tf}: No errors")

def check_data_generation():
    """Check if data is being generated"""
    safe_print("\n" + "="*60)
    safe_print("3. CHECKING DATA GENERATION")
    safe_print("="*60)
    
    # Check if directory exists
    command = f"cd {PROJECT_DIR} && if [ -d paper_trading_outputs ]; then echo 'exists'; else echo 'not found'; fi"
    success, stdout, stderr = run_ssh_command(command)
    
    if "not found" in stdout:
        print("❌ paper_trading_outputs directory not found!")
        return
    
    print("✅ paper_trading_outputs directory exists")
    
    # Count files
    command = f"cd {PROJECT_DIR} && find paper_trading_outputs -type f | wc -l"
    success, stdout, stderr = run_ssh_command(command)
    if success and stdout.strip().isdigit():
        file_count = int(stdout.strip())
        print(f"   Total files: {file_count}")
    
    # Check size
    command = f"cd {PROJECT_DIR} && du -sh paper_trading_outputs 2>/dev/null | cut -f1"
    success, stdout, stderr = run_ssh_command(command)
    if success and stdout.strip():
        print(f"   Total size: {stdout.strip()}")
    
    # Check by timeframe
    print("\n   Files by timeframe:")
    for tf in ["5m", "1h", "12h", "24h"]:
        command = f"cd {PROJECT_DIR} && if [ -d paper_trading_outputs/{tf} ]; then find paper_trading_outputs/{tf} -type f | wc -l; else echo '0'; fi"
        success, stdout, stderr = run_ssh_command(command)
        if success:
            count = int(stdout.strip()) if stdout.strip().isdigit() else 0
            if count > 0:
                # Get size
                size_cmd = f"cd {PROJECT_DIR} && du -sh paper_trading_outputs/{tf} 2>/dev/null | cut -f1"
                size_success, size_out, _ = run_ssh_command(size_cmd)
                size = size_out.strip() if size_success else "N/A"
                print(f"      {tf}: {count} files ({size})")
            else:
                print(f"      {tf}: No files")
    
    # Check most recent files
    print("\n   Most recent files:")
    command = f"cd {PROJECT_DIR} && find paper_trading_outputs -type f -printf '%T@ %p\\n' 2>/dev/null | sort -n | tail -5 | cut -d' ' -f2- | while read f; do echo \"$(basename $f) - $(stat -c %y \"$f\" 2>/dev/null | cut -d' ' -f1-2)\"; done"
    success, stdout, stderr = run_ssh_command(command)
    if success and stdout.strip():
        for line in stdout.strip().split('\n'):
            if line.strip():
                print(f"      {line}")

def check_balance_errors():
    """Check specifically for balance-related errors"""
    safe_print("\n" + "="*60)
    safe_print("4. CHECKING FOR BALANCE ERRORS")
    safe_print("="*60)
    
    command = f"cd {PROJECT_DIR} && grep -r -i -E '(balance|bannace|insufficient|funds|margin|not enough)' logs/ paper_trading_outputs/*.log 2>/dev/null | head -10"
    success, stdout, stderr = run_ssh_command(command)
    
    if success and stdout.strip():
        print("⚠️  Balance-related errors found:")
        for line in stdout.strip().split('\n')[:10]:
            if line.strip():
                print(f"   {line[:100]}")
    else:
        print("✅ No balance-related errors found")
        print("   (This is good - bots are likely in dry_run mode)")

def check_health_endpoint():
    """Check backend health endpoint"""
    safe_print("\n" + "="*60)
    safe_print("5. CHECKING BACKEND HEALTH")
    safe_print("="*60)
    
    command = f"curl -s http://localhost:8000/api/health 2>/dev/null | head -5"
    success, stdout, stderr = run_ssh_command(command)
    
    if success and stdout.strip():
        print("✅ Backend is responding:")
        print(f"   {stdout.strip()[:200]}")
    else:
        print("⚠️  Backend health endpoint not responding")
        print("   Backend may not be running")

def safe_print(message):
    """Print with Unicode fallback for Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback for Windows console
        message_ascii = message.encode('ascii', 'replace').decode('ascii')
        print(message_ascii)

def main():
    """Main function"""
    safe_print("="*60)
    safe_print("VM BOT STATUS CHECK")
    safe_print("="*60)
    safe_print(f"\nVM: {VM_USER}@{VM_HOST}")
    safe_print(f"Project: {PROJECT_DIR}")
    
    # Check SSH connection first
    safe_print("\nTesting SSH connection...")
    command = "echo 'SSH connection successful'"
    success, stdout, stderr = run_ssh_command(command)
    if not success:
        safe_print(f"ERROR: Cannot connect to VM: {stderr}")
        safe_print("\nMake sure you have SSH access configured:")
        safe_print(f"  ssh {VM_USER}@{VM_HOST}")
        sys.exit(1)
    safe_print("OK: SSH connection successful")
    
    # Run all checks
    check_bot_processes()
    check_logs_for_errors()
    check_data_generation()
    check_balance_errors()
    check_health_endpoint()
    
    safe_print("\n" + "="*60)
    safe_print("CHECK COMPLETE")
    safe_print("="*60)
    safe_print("\nTo check manually:")
    safe_print(f"   ssh {VM_USER}@{VM_HOST}")
    safe_print(f"   cd {PROJECT_DIR}")
    safe_print("   ps aux | grep run_unified_bots")
    safe_print("   tail -100 logs/trading-bots.log")
    safe_print("   ls -lh paper_trading_outputs/")

if __name__ == "__main__":
    main()

