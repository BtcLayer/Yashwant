"""
AUTOMATION DASHBOARD - Central Monitoring System

Provides real-time view of:
- Bot status (running/paused)
- Performance metrics (Sharpe, win rate, PnL)
- Cohort signals (S_top, S_bot, flow_diff)
- Recent trades and signals
- System health
- Alert status

Run with: python scripts/monitoring/automation_dashboard.py
Access at: http://localhost:8050
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from flask import Flask, render_template, jsonify
from flask_cors import CORS

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

app = Flask(__name__, 
            template_folder=str(Path(__file__).parent / 'templates'),
            static_folder=str(Path(__file__).parent / 'static'))
CORS(app)

class DashboardDataCollector:
    """Collects data from various system components"""
    
    def __init__(self):
        self.paper_trading_root = os.environ.get('PAPER_TRADING_ROOT', 
                                                  str(project_root / 'paper_trading_outputs' / '5m'))
        self.live_demo_root = project_root / 'live_demo'
        
    def get_bot_status(self):
        """Check if bot is running"""
        try:
            # Check multiple indicators of bot activity
            indicators = []
            
            # 1. Check debug CSV (most reliable - updated every bar)
            debug_file = Path(self.paper_trading_root) / 'user_fills_poll_debug.csv'
            if debug_file.exists():
                mod_time = debug_file.stat().st_mtime
                age_seconds = time.time() - mod_time
                indicators.append(('debug_csv', age_seconds))
            
            # 2. Check trades CSV
            trades_file = Path(self.paper_trading_root) / 'trades.csv'
            if trades_file.exists():
                mod_time = trades_file.stat().st_mtime
                age_seconds = time.time() - mod_time
                indicators.append(('trades_csv', age_seconds))
            
            # 3. Check equity CSV
            equity_file = Path(self.paper_trading_root) / 'equity.csv'
            if equity_file.exists():
                mod_time = equity_file.stat().st_mtime
                age_seconds = time.time() - mod_time
                indicators.append(('equity_csv', age_seconds))
            
            # 4. Check snapshot CSV in live_demo
            snapshot_file = self.live_demo_root / 'snapshot.csv'
            if snapshot_file.exists():
                mod_time = snapshot_file.stat().st_mtime
                age_seconds = time.time() - mod_time
                indicators.append(('snapshot_csv', age_seconds))
            
            # If any indicator shows recent activity (< 5 minutes for 5m bars)
            if indicators:
                most_recent = min(indicators, key=lambda x: x[1])
                file_name, age_seconds = most_recent
                
                # Bot is running if any file updated in last 10 minutes (2 bars)
                if age_seconds < 600:
                    return {
                        'status': 'running',
                        'last_activity': f'{int(age_seconds)}s ago ({file_name})',
                        'uptime_seconds': age_seconds
                    }
            
            return {
                'status': 'stopped',
                'last_activity': 'No recent activity (>10min)',
                'uptime_seconds': 0
            }
        except Exception as e:
            return {
                'status': 'unknown',
                'error': str(e),
                'uptime_seconds': 0
            }
    
    def get_performance_metrics(self):
        """Get current performance metrics"""
        try:
            # Try to load equity data
            equity_file = Path(self.paper_trading_root) / 'equity.csv'
            if equity_file.exists():
                df = pd.read_csv(equity_file)
                if len(df) > 0:
                    returns = df['equity'].pct_change().dropna()
                    
                    # Calculate metrics
                    total_return = (df['equity'].iloc[-1] / df['equity'].iloc[0] - 1) * 100
                    sharpe = returns.mean() / returns.std() * np.sqrt(252 * 288) if len(returns) > 1 else 0
                    max_dd = ((df['equity'] / df['equity'].cummax()) - 1).min() * 100
                    
                    return {
                        'total_return_pct': round(total_return, 2),
                        'sharpe_ratio': round(sharpe, 2),
                        'max_drawdown_pct': round(max_dd, 2),
                        'current_equity': round(df['equity'].iloc[-1], 2),
                        'trades_count': len(df)
                    }
            
            return {
                'total_return_pct': 0,
                'sharpe_ratio': 0,
                'max_drawdown_pct': 0,
                'current_equity': 100000,
                'trades_count': 0
            }
        except Exception as e:
            return {
                'error': str(e),
                'total_return_pct': 0,
                'sharpe_ratio': 0,
                'max_drawdown_pct': 0,
                'current_equity': 100000,
                'trades_count': 0
            }
    
    def get_cohort_status(self):
        """Get cohort loading status"""
        try:
            top_file = self.live_demo_root / 'top_cohort.csv'
            bottom_file = self.live_demo_root / 'bottom_cohort.csv'
            
            status = {
                'top_cohort_loaded': False,
                'bottom_cohort_loaded': False,
                'top_count': 0,
                'bottom_count': 0,
                'total_addresses': 0
            }
            
            if top_file.exists():
                df_top = pd.read_csv(top_file)
                status['top_cohort_loaded'] = True
                status['top_count'] = len(df_top)
            
            if bottom_file.exists():
                df_bottom = pd.read_csv(bottom_file)
                status['bottom_cohort_loaded'] = True
                status['bottom_count'] = len(df_bottom)
            
            status['total_addresses'] = status['top_count'] + status['bottom_count']
            
            return status
        except Exception as e:
            return {
                'error': str(e),
                'top_cohort_loaded': False,
                'bottom_cohort_loaded': False,
                'top_count': 0,
                'bottom_count': 0,
                'total_addresses': 0
            }
    
    def get_recent_trades(self, limit=10):
        """Get recent trades"""
        try:
            trades_file = Path(self.paper_trading_root) / 'trades.csv'
            if trades_file.exists():
                df = pd.read_csv(trades_file)
                df = df.tail(limit)
                
                trades = []
                for _, row in df.iterrows():
                    trades.append({
                        'timestamp': row.get('timestamp', 'N/A'),
                        'symbol': row.get('symbol', 'BTC'),
                        'side': row.get('side', 'N/A'),
                        'size': round(row.get('size', 0), 4),
                        'price': round(row.get('price', 0), 2),
                        'pnl': round(row.get('pnl', 0), 2) if 'pnl' in row else 0,
                        'confidence': round(row.get('confidence', 0), 3) if 'confidence' in row else 0
                    })
                
                return trades[::-1]  # Reverse to show newest first
            
            return []
        except Exception as e:
            return [{'error': str(e)}]
    
    def get_recent_signals(self, limit=20):
        """Get recent signal data"""
        try:
            debug_file = Path(self.paper_trading_root) / 'user_fills_poll_debug.csv'
            if debug_file.exists():
                df = pd.read_csv(debug_file)
                df = df.tail(limit)
                
                signals = []
                for _, row in df.iterrows():
                    signals.append({
                        'timestamp': row.get('timestamp', 'N/A'),
                        'S_top': round(row.get('S_top', 0), 4),
                        'S_bot': round(row.get('S_bot', 0), 4),
                        'flow_diff': round(row.get('flow_diff', 0), 4),
                        'alpha': round(row.get('alpha', 0), 4) if 'alpha' in row else 0,
                        'conf': round(row.get('conf', 0), 3) if 'conf' in row else 0,
                        'dir': int(row.get('dir', 0)) if 'dir' in row else 0
                    })
                
                return signals[::-1]  # Reverse to show newest first
            
            return []
        except Exception as e:
            return [{'error': str(e)}]
    
    def get_config(self):
        """Get current configuration"""
        try:
            config_file = self.live_demo_root / 'config.json'
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                return {
                    'symbol': config.get('data', {}).get('symbol', 'BTCUSDT'),
                    'interval': config.get('data', {}).get('interval', '5m'),
                    'S_MIN': config.get('thresholds', {}).get('S_MIN', 0),
                    'M_MIN': config.get('thresholds', {}).get('M_MIN', 0),
                    'CONF_MIN': config.get('thresholds', {}).get('CONF_MIN', 0),
                    'ALPHA_MIN': config.get('thresholds', {}).get('ALPHA_MIN', 0),
                    'stop_loss_bps': config.get('risk', {}).get('stop_loss_bps', 0),
                    'take_profit_bps': config.get('risk', {}).get('take_profit_bps', 0)
                }
            
            return {}
        except Exception as e:
            return {'error': str(e)}
    
    def get_health_snapshot(self):
        """Get system health snapshot"""
        try:
            snapshot_file = self.live_demo_root / 'snapshot.csv'
            if snapshot_file.exists():
                df = pd.read_csv(snapshot_file)
                if len(df) > 0:
                    latest = df.iloc[-1].to_dict()
                    return {
                        'ic_1h': round(latest.get('ic_1h', 0), 4),
                        'sharpe_1d': round(latest.get('sharpe_1d', 0), 2),
                        'hit_rate': round(latest.get('hit_rate', 0), 3),
                        'alpha_mean': round(latest.get('alpha_mean', 0), 4),
                        'last_update': latest.get('timestamp', 'N/A')
                    }
            
            return {}
        except Exception as e:
            return {'error': str(e)}

# Initialize data collector
collector = DashboardDataCollector()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """Get all dashboard data"""
    try:
        data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'bot_status': collector.get_bot_status(),
            'performance': collector.get_performance_metrics(),
            'cohorts': collector.get_cohort_status(),
            'config': collector.get_config(),
            'health': collector.get_health_snapshot(),
            'recent_trades': collector.get_recent_trades(10),
            'recent_signals': collector.get_recent_signals(20)
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def api_performance():
    """Get performance metrics only"""
    return jsonify(collector.get_performance_metrics())

@app.route('/api/trades')
def api_trades():
    """Get recent trades"""
    limit = int(request.args.get('limit', 10))
    return jsonify(collector.get_recent_trades(limit))

@app.route('/api/signals')
def api_signals():
    """Get recent signals"""
    limit = int(request.args.get('limit', 20))
    return jsonify(collector.get_recent_signals(limit))

def main():
    """Start dashboard server"""
    print("=" * 80)
    print("AUTOMATION DASHBOARD")
    print("=" * 80)
    print(f"Starting dashboard server...")
    print(f"Access at: http://localhost:8050")
    print(f"Monitoring: {collector.paper_trading_root}")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=8050, debug=False)

if __name__ == '__main__':
    main()
