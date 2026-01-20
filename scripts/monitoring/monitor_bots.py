#!/usr/bin/env python3
"""
24/7 Trading Bot Monitor
Monitors the status of all trading bot versions and provides uptime statistics
"""

import time
import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List


class BotMonitor:
    def __init__(self):
        self.log_dir = "paper_trading_outputs/monitoring"
        self.status_file = "paper_trading_outputs/monitoring/bot_status.json"
        os.makedirs(self.log_dir, exist_ok=True)

    def check_docker_containers(self) -> Dict[str, Dict]:
        """Check status of Docker containers (deprecated - no longer using Docker)"""
        # Docker is no longer used - return empty dict
        return {}

    def check_local_processes(self) -> Dict[str, Dict]:
        """Check status of local Python processes"""
        processes = {}

        # First check if run_unified_bots.py is running (all bots run in one process)
        unified_runner_running = False
        try:
            if os.name == 'nt':  # Windows
                # Use tasklist with findstr to check for run_unified_bots.py
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                    capture_output=True, text=True, timeout=5
                )
                # Check process command line using wmic (more reliable)
                try:
                    wmic_result = subprocess.run(
                        ['wmic', 'process', 'where', 'name="python.exe"', 'get', 'commandline', '/format:list'],
                        capture_output=True, text=True, timeout=5
                    )
                    unified_runner_running = 'run_unified_bots.py' in wmic_result.stdout
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # Fallback: check if python.exe is running (less accurate but works)
                    unified_runner_running = 'python.exe' in result.stdout
            else:  # Unix/Linux
                result = subprocess.run(
                    ['pgrep', '-f', 'run_unified_bots.py'],
                    capture_output=True, text=True, timeout=5
                )
                unified_runner_running = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            unified_runner_running = False

        # Check each bot version
        versions = ['5m', '1h', '12h', '24h']
        for version in versions:
            try:
                # If unified runner is running, all bots should be running
                # But also check data files to confirm actual activity
                is_running = unified_runner_running
                
                # Verify by checking if bot has recent data files
                suffix = f"_{version}" if version in ["1h", "12h"] else ""
                equity_file = f'paper_trading_outputs/{version}/sheets_fallback/equity{suffix}.csv'
                
                if is_running and os.path.exists(equity_file):
                    # Check if file was modified recently (within last hour)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(equity_file))
                    time_diff = datetime.now() - mod_time
                    # If file exists but hasn't been updated in 2 hours, bot might be stuck
                    if time_diff.total_seconds() > 7200:  # 2 hours
                        is_running = False

                processes[f'trading-bot-{version}'] = {
                    'status': 'Running' if is_running else 'Stopped',
                    'running': is_running,
                    'type': 'local'
                }
            except Exception:
                processes[f'trading-bot-{version}'] = {
                    'status': 'Unknown',
                    'running': False,
                    'type': 'local'
                }

        return processes

    def check_log_files(self) -> Dict[str, Dict]:
        """Check log files for recent activity"""
        log_status = {}

        # Check unified runner logs and bot-specific data files
        log_files = {
            'trading-bot-5m': 'paper_trading_outputs/unified_runner_5m.log',
            'trading-bot-1h': 'paper_trading_outputs/unified_runner_1h.log',
            'trading-bot-12h': 'paper_trading_outputs/unified_runner_12h.log',
            'trading-bot-24h': 'paper_trading_outputs/unified_runner_24h.log'
        }

        for bot_name, log_file in log_files.items():
            if os.path.exists(log_file):
                # Check if log file was modified recently (within last 5 minutes)
                mod_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                time_diff = datetime.now() - mod_time

                is_recent = time_diff.total_seconds() < 300  # 5 minutes

                log_status[bot_name] = {
                    'log_exists': True,
                    'last_modified': mod_time.isoformat(),
                    'recent_activity': is_recent,
                    'file_size': os.path.getsize(log_file)
                }
            else:
                # Also check for data files as indicator of activity
                version = bot_name.split('-')[-1]
                suffix = f"_{version}" if version in ["1h", "12h"] else ""
                equity_file = f'paper_trading_outputs/{version}/sheets_fallback/equity{suffix}.csv'
                
                if os.path.exists(equity_file):
                    mod_time = datetime.fromtimestamp(os.path.getmtime(equity_file))
                    time_diff = datetime.now() - mod_time
                    is_recent = time_diff.total_seconds() < 3600  # 1 hour for data files
                    
                    log_status[bot_name] = {
                        'log_exists': True,
                        'last_modified': mod_time.isoformat(),
                        'recent_activity': is_recent,
                        'file_size': os.path.getsize(equity_file)
                    }
                else:
                    log_status[bot_name] = {
                        'log_exists': False,
                        'last_modified': None,
                        'recent_activity': False,
                        'file_size': 0
                    }

        return log_status

    def get_uptime_stats(self) -> Dict[str, str]:
        """Calculate uptime statistics"""
        stats = {}

        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    data = json.load(f)

                start_time = datetime.fromisoformat(data.get('start_time', datetime.now().isoformat()))
                uptime = datetime.now() - start_time

                stats['monitoring_uptime'] = str(uptime).split('.')[0]  # Remove microseconds
                stats['start_time'] = data.get('start_time')

                # Calculate availability
                total_checks = data.get('total_checks', 0)
                successful_checks = data.get('successful_checks', 0)

                if total_checks > 0:
                    availability = (successful_checks / total_checks) * 100
                    stats['availability'] = f"{availability:.2f}%"
                else:
                    stats['availability'] = "No data"

            except (json.JSONDecodeError, ValueError):
                stats['monitoring_uptime'] = "Unknown"
                stats['availability'] = "No data"
        else:
            stats['monitoring_uptime'] = "First run"
            stats['availability'] = "No data"

        return stats

    def save_status(self, status: Dict):
        """Save current status for uptime tracking"""
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'start_time': datetime.now().isoformat(),
            'total_checks': 1,
            'successful_checks': 1 if all(bot.get('running', False) for bot in status.values()) else 0,
            'versions': status
        }

        # Load existing data if available
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    existing = json.load(f)

                status_data['start_time'] = existing.get('start_time', status_data['start_time'])
                status_data['total_checks'] = existing.get('total_checks', 0) + 1
                status_data['successful_checks'] = existing.get('successful_checks', 0) + (1 if all(bot.get('running', False) for bot in status.values()) else 0)
            except (json.JSONDecodeError, ValueError):
                pass

        with open(self.status_file, 'w') as f:
            json.dump(status_data, f, indent=2)

    def print_status(self):
        """Print current status of all trading bots"""
        print("🚀 24/7 Trading Bot Monitor")
        print("=" * 50)
        print(f"📊 Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Get status from all sources
        docker_status = self.check_docker_containers()
        local_status = self.check_local_processes()
        log_status = self.check_log_files()
        uptime_stats = self.get_uptime_stats()

        print("⏱️  Uptime Statistics:")
        for key, value in uptime_stats.items():
            print(f"   {key}: {value}")
        print()

        # Combine status from all sources
        all_bots = {}
        for bot_name in ['trading-bot-5m', 'trading-bot-1h', 'trading-bot-12h', 'trading-bot-24h']:
            local_info = local_status.get(bot_name, {})
            log_info = log_status.get(bot_name, {})

            # Determine overall status
            running = local_info.get('running', False)
            recent_logs = log_info.get('recent_activity', False)

            all_bots[bot_name] = {
                'running': running,
                'recent_logs': recent_logs,
                'log_size': log_info.get('file_size', 0),
                'local_status': local_info.get('status', 'Not running locally')
            }

        # Print individual bot status
        for bot_name, status in all_bots.items():
            version = bot_name.split('-')[-1].upper()
            icon = "✅" if status['running'] else "❌"

            print(f"{icon} {version} Version ({bot_name}):")
            print(f"   Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
            print(f"   Recent Activity: {'🟢 Yes' if status['recent_logs'] else '🟡 No'}")
            print(f"   Log Size: {status['log_size']:,} bytes")
            print()

        # Overall assessment
        running_count = sum(1 for bot in all_bots.values() if bot['running'])
        total_count = len(all_bots)

        print("📈 Overall Status:")
        if running_count == total_count:
            print(f"   🎉 All {total_count} trading bots are running!")
        elif running_count > 0:
            print(f"   ⚠️  {running_count}/{total_count} trading bots are running")
        else:
            print(f"   🚨 No trading bots are currently running")

        # Save status for uptime tracking
        self.save_status(all_bots)

        return running_count == total_count


def main():
    """Main monitoring function"""
    monitor = BotMonitor()

    if len(os.sys.argv) > 1 and os.sys.argv[1] == '--watch':
        # Continuous monitoring mode
        print("👀 Starting continuous monitoring (Ctrl+C to stop)...")
        print()

        try:
            while True:
                monitor.print_status()
                print("\n" + "="*50)
                print(f"Next check in 60 seconds... ({datetime.now().strftime('%H:%M:%S')})")
                print()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
    else:
        # Single check mode
        all_running = monitor.print_status()

        if all_running:
            print("✅ All trading bots are running successfully!")
            print("🚀 Ready for 24/7 operation!")
        else:
            print("⚠️  Some trading bots are not running")
            print("💡 Start them with: python run_unified_bots.py")

        return 0 if all_running else 1


if __name__ == '__main__':
    exit(main())
