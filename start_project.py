#!/usr/bin/env python3
"""
MetaStackerBandit - Single Script Startup
Starts backend, frontend, and optionally trading bots all from one script.
Everything accessible on one port (8000) - backend serves frontend.
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path
from typing import Optional

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message: str, color: str = Colors.RESET):
    """Print colored message"""
    try:
        print(f"{color}{message}{Colors.RESET}")
    except UnicodeEncodeError:
        # Fallback for Windows console that doesn't support Unicode
        # Replace box-drawing characters with ASCII equivalents
        message_ascii = message.replace('╔', '+').replace('═', '=').replace('╗', '+')
        message_ascii = message_ascii.replace('║', '|').replace('╚', '+').replace('╝', '+')
        print(f"{color}{message_ascii}{Colors.RESET}")

def check_dependencies():
    """Check if required dependencies are installed"""
    print_colored("\n🔍 Checking dependencies...", Colors.CYAN)
    
    # Check Python
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print_colored("❌ Python 3.8+ required", Colors.RED)
        return False
    print_colored(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}", Colors.GREEN)
    
    # Check Node.js (for frontend)
    try:
        # On Windows, use shell=True to find node in PATH
        use_shell = os.name == 'nt'
        result = subprocess.run(
            ["node", "--version"] if not use_shell else "node --version",
            capture_output=True,
            text=True,
            timeout=5,
            shell=use_shell
        )
        if result.returncode == 0:
            print_colored(f"✅ Node.js {result.stdout.strip()}", Colors.GREEN)
        else:
            print_colored("⚠️  Node.js not found (frontend build may fail)", Colors.YELLOW)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Try with shell=True as fallback (especially on Windows)
        try:
            result = subprocess.run(
                "node --version",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print_colored(f"✅ Node.js {result.stdout.strip()}", Colors.GREEN)
            else:
                print_colored("⚠️  Node.js not found (frontend build may fail)", Colors.YELLOW)
        except:
            print_colored("⚠️  Node.js not found (frontend build may fail)", Colors.YELLOW)
    
    # Check npm
    try:
        # On Windows, use shell=True to find npm in PATH
        use_shell = os.name == 'nt'
        result = subprocess.run(
            ["npm", "--version"] if not use_shell else "npm --version",
            capture_output=True,
            text=True,
            timeout=5,
            shell=use_shell
        )
        if result.returncode == 0:
            print_colored(f"✅ npm {result.stdout.strip()}", Colors.GREEN)
        else:
            print_colored("⚠️  npm not found (frontend build may fail)", Colors.YELLOW)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Try with shell=True as fallback (especially on Windows)
        try:
            result = subprocess.run(
                "npm --version",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print_colored(f"✅ npm {result.stdout.strip()}", Colors.GREEN)
            else:
                print_colored("⚠️  npm not found (frontend build may fail)", Colors.YELLOW)
        except:
            print_colored("⚠️  npm not found (frontend build may fail)", Colors.YELLOW)
    
    return True

def build_frontend(base_dir: Path, force: bool = False) -> bool:
    """Build React frontend if not already built or if source files changed"""
    frontend_dir = base_dir / "frontend"
    build_dir = frontend_dir / "build"
    
    # Check if build exists and is up-to-date
    if build_dir.exists() and (build_dir / "index.html").exists() and not force:
        # Check if any source files are newer than the build
        build_time = (build_dir / "index.html").stat().st_mtime
        
        # Check key source files/directories
        source_paths = [
            frontend_dir / "src",
            frontend_dir / "public",
            frontend_dir / "package.json",
            frontend_dir / "package-lock.json"
        ]
        
        needs_rebuild = False
        for source_path in source_paths:
            if source_path.exists():
                if source_path.is_dir():
                    # Check all files in directory recursively
                    for file_path in source_path.rglob("*"):
                        if file_path.is_file() and file_path.stat().st_mtime > build_time:
                            needs_rebuild = True
                            break
                else:
                    # Single file
                    if source_path.stat().st_mtime > build_time:
                        needs_rebuild = True
                if needs_rebuild:
                    break
        
        if not needs_rebuild:
            print_colored("✅ Frontend already built and up-to-date", Colors.GREEN)
            return True
        else:
            print_colored("📦 Source files changed, rebuilding frontend...", Colors.YELLOW)
    
    print_colored("\n📦 Building frontend...", Colors.CYAN)
    print_colored("   This may take a few minutes on first run...", Colors.YELLOW)
    
    try:
        # Check if node_modules exists
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print_colored("   Installing npm dependencies...", Colors.YELLOW)
            # Use shell=True on Windows for npm commands
            use_shell = os.name == 'nt'
            install_result = subprocess.run(
                ["npm", "install"] if not use_shell else "npm install",
                cwd=str(frontend_dir),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
                shell=use_shell
            )
            if install_result.returncode != 0:
                print_colored(f"❌ npm install failed: {install_result.stderr}", Colors.RED)
                return False
            print_colored("✅ npm dependencies installed", Colors.GREEN)
        
        # Build frontend
        print_colored("   Building React app...", Colors.YELLOW)
        # Use shell=True on Windows for npm commands
        use_shell = os.name == 'nt'
        build_result = subprocess.run(
            ["npm", "run", "build"] if not use_shell else "npm run build",
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes
            shell=use_shell
        )
        
        if build_result.returncode != 0:
            print_colored(f"❌ Frontend build failed: {build_result.stderr}", Colors.RED)
            return False
        
        if build_dir.exists() and (build_dir / "index.html").exists():
            print_colored("✅ Frontend built successfully", Colors.GREEN)
            return True
        else:
            print_colored("❌ Frontend build directory not found", Colors.RED)
            return False
            
    except subprocess.TimeoutExpired:
        print_colored("❌ Frontend build timed out", Colors.RED)
        return False
    except Exception as e:
        print_colored(f"❌ Frontend build error: {e}", Colors.RED)
        return False

def kill_processes_on_port(port: int) -> bool:
    """Kill processes using the specified port
    
    Args:
        port: Port number to free up
        
    Returns:
        True if any processes were killed, False otherwise
    """
    killed_any = False
    try:
        if os.name == 'nt':  # Windows
            # Use netstat to find processes on the port
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                pids_to_kill = set()
                for line in lines:
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) > 0:
                            pid = parts[-1]
                            if pid.isdigit():
                                pids_to_kill.add(int(pid))
                
                for pid in pids_to_kill:
                    try:
                        # Try graceful termination first
                        process = subprocess.run(
                            ["taskkill", "/PID", str(pid), "/F"],
                            capture_output=True,
                            timeout=5
                        )
                        if process.returncode == 0:
                            killed_any = True
                            print_colored(f"   Killed process {pid} on port {port}", Colors.YELLOW)
                    except Exception:
                        pass
        else:  # Linux/Mac
            # Use lsof to find processes on the port
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.isdigit():
                            try:
                                os.kill(int(pid), signal.SIGTERM)
                                time.sleep(0.5)
                                # Force kill if still running
                                try:
                                    os.kill(int(pid), signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                                killed_any = True
                                print_colored(f"   Killed process {pid} on port {port}", Colors.YELLOW)
                            except (ProcessLookupError, PermissionError):
                                pass
            except FileNotFoundError:
                # lsof not available, try fuser
                try:
                    result = subprocess.run(
                        ["fuser", "-k", f"{port}/tcp"],
                        capture_output=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        killed_any = True
                except FileNotFoundError:
                    pass
    except Exception as e:
        # Silently fail - port might be free already
        pass
    
    return killed_any

def kill_existing_bot_processes(base_dir: Path) -> bool:
    """Kill any existing bot processes (run_unified_bots.py)
    
    Args:
        base_dir: Project base directory
        
    Returns:
        True if any processes were killed, False otherwise
    """
    killed_any = False
    try:
        bots_script = base_dir / "run_unified_bots.py"
        if not bots_script.exists():
            return False
        
        if os.name == 'nt':  # Windows
            # Find Python processes running run_unified_bots.py
            try:
                result = subprocess.run(
                    ["wmic", "process", "where", "commandline like '%run_unified_bots.py%'", "get", "processid"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        pid = line.strip()
                        if pid.isdigit():
                            try:
                                subprocess.run(
                                    ["taskkill", "/PID", pid, "/F"],
                                    capture_output=True,
                                    timeout=5
                                )
                                killed_any = True
                                print_colored(f"   Killed existing bot process {pid}", Colors.YELLOW)
                            except Exception:
                                pass
            except Exception:
                # Fallback: try to find by process name and script
                pass
        else:  # Linux/Mac
            # Use ps and grep to find processes
            try:
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'run_unified_bots.py' in line:
                            parts = line.split()
                            if len(parts) > 1:
                                pid = parts[1]
                                if pid.isdigit():
                                    try:
                                        os.kill(int(pid), signal.SIGTERM)
                                        time.sleep(0.5)
                                        try:
                                            os.kill(int(pid), signal.SIGKILL)
                                        except ProcessLookupError:
                                            pass
                                        killed_any = True
                                        print_colored(f"   Killed existing bot process {pid}", Colors.YELLOW)
                                    except (ProcessLookupError, PermissionError):
                                        pass
            except Exception:
                pass
    except Exception:
        pass
    
    return killed_any

def start_backend(base_dir: Path, port: int = 8000, auto_start_bots: bool = True, internal_port: Optional[int] = None, use_gunicorn: bool = False) -> Optional[subprocess.Popen]:
    """Start FastAPI backend server
    
    Args:
        base_dir: Project base directory
        port: External port (for nginx) or actual port (if no nginx)
        auto_start_bots: Whether to auto-start trading bots
        internal_port: Internal port for backend (when using nginx). If None, uses port directly.
        use_gunicorn: Use gunicorn instead of uvicorn (for production)
    """
    actual_port = internal_port if internal_port else port
    
    # Kill any existing processes on the port
    print_colored(f"🔍 Checking port {actual_port}...", Colors.CYAN)
    if kill_processes_on_port(actual_port):
        print_colored(f"   Waiting 2 seconds for port to be released...", Colors.YELLOW)
        time.sleep(2)
    else:
        print_colored(f"   Port {actual_port} is free", Colors.GREEN)
    
    # Gunicorn doesn't work on Windows (requires fcntl module)
    if use_gunicorn and os.name == 'nt':
        print_colored("⚠️  Gunicorn is not supported on Windows (requires Unix). Falling back to uvicorn...", Colors.YELLOW)
        use_gunicorn = False
    
    server_type = "gunicorn" if use_gunicorn else "uvicorn"
    print_colored(f"\n🚀 Starting backend on port {actual_port} ({server_type})...", Colors.CYAN)
    
    backend_dir = base_dir / "backend"
    if not backend_dir.exists():
        print_colored("❌ Backend directory not found", Colors.RED)
        return None
    
    # Set environment variable for auto-start bots
    env = os.environ.copy()
    if auto_start_bots:
        env["AUTO_START_BOTS"] = "true"
    else:
        env["AUTO_START_BOTS"] = "false"
    
    # Set environment variables for production
    env["PYTHONPATH"] = str(base_dir)
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    env.setdefault("NUMPY_MKL", "1")
    
    try:
        # Windows-specific flags
        creation_flags = 0
        if os.name == 'nt':  # Windows
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        if use_gunicorn:
            # Use gunicorn with uvicorn workers for production
            process = subprocess.Popen(
                [
                    sys.executable, "-m", "gunicorn",
                    "main:app",
                    "--bind", f"0.0.0.0:{actual_port}",
                    "--workers", "2",
                    "--worker-class", "uvicorn.workers.UvicornWorker",
                    "--timeout", "120",
                    "--access-logfile", "-",
                    "--error-logfile", "-"
                ],
                cwd=str(backend_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creation_flags
            )
        else:
            # Use uvicorn directly
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(actual_port)],
                cwd=str(backend_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creation_flags
            )
        
        # Wait a moment to check if it started
        time.sleep(2)
        if process.poll() is None:
            print_colored(f"✅ Backend started on port {actual_port} (PID: {process.pid})", Colors.GREEN)
            return process
        else:
            stdout, _ = process.communicate()
            print_colored(f"❌ Backend failed to start: {stdout}", Colors.RED)
            return None
            
    except Exception as e:
        print_colored(f"❌ Failed to start backend: {e}", Colors.RED)
        return None

def check_nginx_installed() -> bool:
    """Check if nginx is installed"""
    try:
        result = subprocess.run(["nginx", "-v"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def start_nginx(base_dir: Path, port: int = 8000) -> Optional[subprocess.Popen]:
    """Start nginx as reverse proxy"""
    print_colored(f"\n🌐 Starting nginx on port {port}...", Colors.CYAN)
    
    nginx_conf = base_dir / "nginx.conf"
    frontend_build = base_dir / "frontend" / "build"
    
    if not nginx_conf.exists():
        print_colored("❌ nginx.conf not found", Colors.RED)
        return None
    
    if not frontend_build.exists():
        print_colored("❌ Frontend build directory not found", Colors.RED)
        return None
    
    # Create nginx config with correct paths
    try:
        # Read template
        with open(nginx_conf, 'r') as f:
            config_content = f.read()
        
        # Replace paths for current OS
        if os.name == 'nt':  # Windows
            # For Windows, nginx typically uses forward slashes
            frontend_path = str(frontend_build).replace('\\', '/')
        else:  # Linux/Mac
            frontend_path = str(frontend_build)
        
        # Update root path in config
        config_content = config_content.replace('/usr/share/nginx/html', frontend_path)
        
        # Write temporary config
        temp_conf = base_dir / "nginx_temp.conf"
        with open(temp_conf, 'w') as f:
            f.write(config_content)
        
        # Test nginx config
        test_result = subprocess.run(
            ["nginx", "-t", "-c", str(temp_conf)],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if test_result.returncode != 0:
            print_colored(f"❌ Nginx config test failed: {test_result.stderr}", Colors.RED)
            return None
        
        # Start nginx
        creation_flags = 0
        if os.name == 'nt':  # Windows
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        process = subprocess.Popen(
            ["nginx", "-c", str(temp_conf), "-g", "daemon off;"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creation_flags
        )
        
        time.sleep(1)
        if process.poll() is None:
            print_colored(f"✅ Nginx started (PID: {process.pid})", Colors.GREEN)
            return process
        else:
            stdout, _ = process.communicate()
            print_colored(f"❌ Nginx failed to start: {stdout}", Colors.RED)
            return None
            
    except Exception as e:
        print_colored(f"❌ Failed to start nginx: {e}", Colors.RED)
        return None

def print_backend_output(process: subprocess.Popen):
    """Print backend output in real-time"""
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[Backend] {line.rstrip()}")

def wait_for_backend(port: int = 8000, timeout: int = 30) -> bool:
    """Wait for backend to be ready"""
    import urllib.request
    import urllib.error
    
    print_colored(f"\n⏳ Waiting for backend to be ready...", Colors.YELLOW)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Try multiple endpoints to check if backend is ready
            endpoints = [
                f"http://localhost:{port}/api/dashboard/summary",
                f"http://localhost:{port}/docs",
                f"http://localhost:{port}/api/health"
            ]
            
            for endpoint in endpoints:
                try:
                    response = urllib.request.urlopen(endpoint, timeout=2)
                    if response.status in [200, 404]:  # 404 is OK, means server is responding
                        print_colored("✅ Backend is ready!", Colors.GREEN)
                        return True
                except urllib.error.HTTPError as e:
                    if e.code in [200, 404]:  # Server is responding
                        print_colored("✅ Backend is ready!", Colors.GREEN)
                        return True
        except (urllib.error.URLError, ConnectionRefusedError):
            time.sleep(1)
        except Exception:
            time.sleep(1)
    
    print_colored("⚠️  Backend may not be fully ready yet", Colors.YELLOW)
    return False

def main():
    """Main entry point"""
    print_colored("""
╔══════════════════════════════════════════════════════════════╗
║         MetaStackerBandit - Single Script Startup            ║
║     Starts backend, frontend, and bots all in one go!         ║
╚══════════════════════════════════════════════════════════════╝
    """, Colors.BOLD + Colors.CYAN)
    
    # Get base directory
    base_dir = Path(__file__).parent.resolve()
    print_colored(f"📁 Project directory: {base_dir}", Colors.CYAN)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Start MetaStackerBandit project")
    parser.add_argument("--port", type=int, default=8000, help="Port for frontend/nginx (default: 8000)")
    parser.add_argument("--no-bots", action="store_true", help="Don't auto-start trading bots")
    parser.add_argument("--no-build", action="store_true", help="Skip frontend build (use existing)")
    parser.add_argument("--nginx", action="store_true", help="Use nginx as reverse proxy (requires nginx installed)")
    parser.add_argument("--daemon", action="store_true", help="Run in background (for production deployment)")
    parser.add_argument("--gunicorn", action="store_true", help="Use gunicorn instead of uvicorn (for production, Unix/Linux only - auto-falls back to uvicorn on Windows)")
    args = parser.parse_args()
    
    # Kill existing processes before starting
    print_colored("\n🔍 Cleaning up existing processes...", Colors.CYAN)
    killed_bots = kill_existing_bot_processes(base_dir)
    if killed_bots:
        print_colored("   Waiting 1 second for cleanup...", Colors.YELLOW)
        time.sleep(1)
    
    # Check dependencies
    if not check_dependencies():
        print_colored("\n❌ Dependency check failed", Colors.RED)
        sys.exit(1)
    
    # Build frontend if needed
    if not args.no_build:
        if not build_frontend(base_dir):
            print_colored("\n⚠️  Frontend build failed, but continuing with backend...", Colors.YELLOW)
            print_colored("   You can access the API at http://localhost:8000/api/", Colors.YELLOW)
    
    # Check if nginx should be used
    use_nginx = args.nginx
    if use_nginx:
        if not check_nginx_installed():
            print_colored("\n⚠️  Nginx not found. Install nginx or use --no-nginx", Colors.YELLOW)
            print_colored("   Falling back to FastAPI serving frontend directly", Colors.YELLOW)
            use_nginx = False
        else:
            print_colored("\n✅ Nginx found, using as reverse proxy", Colors.GREEN)
    
    # Start backend
    # If using nginx, backend runs on internal port 8001, nginx on 8000
    # If not using nginx, backend runs directly on port 8000
    backend_port = 8001 if use_nginx else args.port
    backend_process = start_backend(
        base_dir, 
        port=args.port,
        internal_port=backend_port,
        auto_start_bots=not args.no_bots,
        use_gunicorn=args.gunicorn
    )
    
    if not backend_process:
        print_colored("\n❌ Failed to start backend", Colors.RED)
        sys.exit(1)
    
    # Start nginx if requested
    nginx_process = None
    if use_nginx:
        nginx_process = start_nginx(base_dir, port=args.port)
        if not nginx_process:
            print_colored("\n⚠️  Nginx failed to start, but backend is running", Colors.YELLOW)
            print_colored(f"   You can access the API at http://localhost:{backend_port}/api/", Colors.YELLOW)
            use_nginx = False
    
    # Start output thread
    output_thread = threading.Thread(
        target=print_backend_output,
        args=(backend_process,),
        daemon=True
    )
    output_thread.start()
    
    # Wait for backend to be ready
    wait_for_backend(port=backend_port)
    
    # Wait for nginx if used
    if use_nginx and nginx_process:
        time.sleep(1)
        wait_for_backend(port=args.port)
    
    # Handle daemon mode (for production deployment)
    if args.daemon:
        print_colored(f"""
╔══════════════════════════════════════════════════════════════╗
║              🎉 PROJECT STARTED IN BACKGROUND!                ║
╚══════════════════════════════════════════════════════════════╝

🌐 Access the application:
   • Frontend: http://localhost:{args.port}/
   • API: http://localhost:{args.port}/api/
   • API Docs: http://localhost:{args.port}/docs

{'🌐 Nginx: Running (reverse proxy)' if use_nginx else '📦 Backend: Serving frontend directly'}
🤖 Trading Bots: {'Enabled' if not args.no_bots else 'Disabled'}
📊 Backend PID: {backend_process.pid}{f' | Nginx PID: {nginx_process.pid}' if nginx_process else ''}

✅ Running in background mode (daemon)
    """, Colors.BOLD + Colors.GREEN)
        
        # In daemon mode, detach and return
        # The processes will continue running
        return
    
    # Print success message (interactive mode)
    proxy_info = " (via nginx)" if use_nginx else ""
    print_colored(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🎉 PROJECT STARTED!                       ║
╚══════════════════════════════════════════════════════════════╝

🌐 Access the application:
   • Frontend: http://localhost:{args.port}/
   • API: http://localhost:{args.port}/api/
   • API Docs: http://localhost:{args.port}/docs

{'🌐 Nginx: Running (reverse proxy)' if use_nginx else '📦 Backend: Serving frontend directly'}
🤖 Trading Bots: {'Enabled' if not args.no_bots else 'Disabled'}
📊 Backend PID: {backend_process.pid}{f' | Nginx PID: {nginx_process.pid}' if nginx_process else ''}

Press Ctrl+C to stop all services...
    """, Colors.BOLD + Colors.GREEN)
    
    # Handle shutdown
    def signal_handler(sig, frame):
        print_colored("\n\n🛑 Shutting down...", Colors.YELLOW)
        if nginx_process:
            nginx_process.terminate()
            try:
                nginx_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                nginx_process.kill()
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
        # Clean up temp nginx config
        temp_conf = base_dir / "nginx_temp.conf"
        if temp_conf.exists():
            try:
                temp_conf.unlink()
            except:
                pass
        print_colored("✅ All services stopped", Colors.GREEN)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Keep script running
    try:
        # Wait for either process to exit
        while True:
            if backend_process.poll() is not None:
                print_colored("\n⚠️  Backend process exited", Colors.YELLOW)
                break
            if nginx_process and nginx_process.poll() is not None:
                print_colored("\n⚠️  Nginx process exited", Colors.YELLOW)
                break
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()

