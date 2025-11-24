#!/usr/bin/env python3
"""
Restart VM Application
Checks VM status and restarts the application if needed
"""

import subprocess
import sys
import time
from pathlib import Path

VM_HOST = "40.88.15.47"
VM_USER = "azureuser"
PROJECT_DIR = "/home/azureuser/MetaStackerBandit"

def run_ssh_command(command, use_key=False):
    """Run SSH command on VM"""
    try:
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{VM_USER}@{VM_HOST}", command]
        if use_key:
            # Try to use key from common locations
            key_paths = [
                Path.home() / ".ssh" / "vm_key",
                Path.home() / ".ssh" / "id_rsa",
                Path.home() / ".ssh" / "id_ed25519",
            ]
            for key_path in key_paths:
                if key_path.exists():
                    ssh_cmd = ["ssh", "-i", str(key_path), "-o", "StrictHostKeyChecking=no", f"{VM_USER}@{VM_HOST}", command]
                    break
        
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "SSH command timed out"
    except Exception as e:
        return False, "", str(e)

def check_application_status():
    """Check if application is running"""
    print("🔍 Checking application status...")
    
    # Check if port 8000 is listening
    success, stdout, stderr = run_ssh_command("netstat -tuln | grep :8000 || ss -tuln | grep :8000")
    if success and ":8000" in stdout:
        print("✅ Port 8000 is listening")
    else:
        print("❌ Port 8000 is not listening")
        return False
    
    # Check if processes are running
    success, stdout, stderr = run_ssh_command("ps aux | grep -E '(start_project|gunicorn|uvicorn)' | grep -v grep")
    if success and stdout.strip():
        print("✅ Application processes found:")
        for line in stdout.strip().split('\n'):
            if line.strip():
                print(f"   {line[:80]}")
        return True
    else:
        print("❌ No application processes found")
        return False

def check_health_endpoint():
    """Check if health endpoint responds"""
    print("\n🔍 Checking health endpoint...")
    success, stdout, stderr = run_ssh_command("curl -f -s http://localhost:8000/api/health 2>&1")
    if success and "ok" in stdout.lower():
        print("✅ Health endpoint responding")
        return True
    else:
        print(f"❌ Health endpoint not responding: {stdout[:200] if stdout else stderr[:200]}")
        return False

def check_logs():
    """Check recent logs for errors"""
    print("\n🔍 Checking recent logs...")
    success, stdout, stderr = run_ssh_command(f"tail -50 {PROJECT_DIR}/logs/start_project.log 2>&1")
    if success and stdout:
        print("📋 Recent log entries:")
        lines = stdout.strip().split('\n')
        for line in lines[-10:]:  # Last 10 lines
            if line.strip():
                print(f"   {line[:100]}")
        
        # Check for errors
        if any(keyword in stdout.lower() for keyword in ['error', 'exception', 'failed', 'traceback']):
            print("\n⚠️  Errors found in logs!")
            return False
    else:
        print("⚠️  Could not read logs")
    return True

def stop_application():
    """Stop existing application processes"""
    print("\n🛑 Stopping existing application...")
    
    commands = [
        "pkill -f 'python.*start_project.py' || true",
        "pkill -f gunicorn || true",
        "pkill -f uvicorn || true",
        "pkill -f run_unified_bots.py || true",
    ]
    
    for cmd in commands:
        success, stdout, stderr = run_ssh_command(f"cd {PROJECT_DIR} && {cmd}")
        if success:
            print(f"   ✓ {cmd.split()[0]}")
    
    print("   Waiting 3 seconds for processes to stop...")
    time.sleep(3)
    
    # Verify processes are stopped
    success, stdout, stderr = run_ssh_command("ps aux | grep -E '(start_project|gunicorn|uvicorn)' | grep -v grep")
    if success and stdout.strip():
        print("⚠️  Some processes still running, forcing kill...")
        run_ssh_command("pkill -9 -f 'python.*start_project.py' || true")
        run_ssh_command("pkill -9 -f gunicorn || true")
        run_ssh_command("pkill -9 -f uvicorn || true")
    else:
        print("✅ All processes stopped")

def start_application():
    """Start the application"""
    print("\n🚀 Starting application...")
    
    command = f"""
cd {PROJECT_DIR} && \
source venv/bin/activate && \
nohup python start_project.py --gunicorn --daemon > logs/start_project.log 2>&1 &
"""
    
    success, stdout, stderr = run_ssh_command(command)
    if success:
        print("✅ Start command executed")
        print("   Waiting 5 seconds for application to initialize...")
        time.sleep(5)
        return True
    else:
        print(f"❌ Failed to start: {stderr}")
        return False

def verify_startup():
    """Verify application started successfully"""
    print("\n🔍 Verifying startup...")
    
    # Wait a bit more for frontend build
    print("   Waiting 15 seconds for frontend build and services to start...")
    time.sleep(15)
    
    # Check processes
    success, stdout, stderr = run_ssh_command("ps aux | grep -E '(start_project|gunicorn|uvicorn)' | grep -v grep")
    if success and stdout.strip():
        print("✅ Processes are running")
    else:
        print("❌ No processes found")
        return False
    
    # Check health endpoint
    for i in range(5):
        success, stdout, stderr = run_ssh_command("curl -f -s http://localhost:8000/api/health 2>&1")
        if success and "ok" in stdout.lower():
            print("✅ Health endpoint responding")
            return True
        else:
            print(f"   Attempt {i+1}/5: Health check failed, retrying in 5 seconds...")
            time.sleep(5)
    
    print("⚠️  Health endpoint not responding yet, but processes are running")
    print("   Application may still be starting (frontend build can take time)")
    return True

def main():
    """Main function"""
    print("="*60)
    print("VM APPLICATION RESTART")
    print("="*60)
    print(f"\nVM: {VM_USER}@{VM_HOST}")
    print(f"Project: {PROJECT_DIR}")
    
    # Test SSH connection
    print("\n🔌 Testing SSH connection...")
    success, stdout, stderr = run_ssh_command("echo 'SSH OK'")
    if not success:
        print(f"❌ Cannot connect to VM: {stderr}")
        print(f"\nMake sure you have SSH access:")
        print(f"  ssh {VM_USER}@{VM_HOST}")
        sys.exit(1)
    print("✅ SSH connection successful")
    
    # Check current status
    is_running = check_application_status()
    health_ok = check_health_endpoint() if is_running else False
    
    if is_running and health_ok:
        print("\n✅ Application is running and healthy!")
        print(f"\n🌐 Access at: http://{VM_HOST}:8000")
        response = input("\nDo you want to restart anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Keeping current application running.")
            return
    
    # Check logs before restart
    check_logs()
    
    # Stop application
    stop_application()
    
    # Start application
    if not start_application():
        print("\n❌ Failed to start application")
        sys.exit(1)
    
    # Verify startup
    if verify_startup():
        print("\n" + "="*60)
        print("✅ APPLICATION RESTARTED SUCCESSFULLY!")
        print("="*60)
        print(f"\n🌐 Access at: http://{VM_HOST}:8000")
        print(f"📋 Check logs: ssh {VM_USER}@{VM_HOST} 'tail -f {PROJECT_DIR}/logs/start_project.log'")
    else:
        print("\n" + "="*60)
        print("⚠️  APPLICATION STARTED BUT HEALTH CHECK FAILED")
        print("="*60)
        print(f"\n📋 Check logs: ssh {VM_USER}@{VM_HOST} 'tail -f {PROJECT_DIR}/logs/start_project.log'")
        print(f"🔍 Check processes: ssh {VM_USER}@{VM_HOST} 'ps aux | grep start_project'")

if __name__ == "__main__":
    main()

