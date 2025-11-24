"""
FastAPI Backend for MetaStackerBandit Dashboard
Serves trading bot data and metrics
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import gzip
import time
import subprocess
import threading
import sys

app = FastAPI(title="MetaStackerBandit API", version="1.0.0")

# Start trading bots when backend starts (default: enabled)
# Set AUTO_START_BOTS=false to disable
AUTO_START_BOTS = os.environ.get("AUTO_START_BOTS", "true").lower() not in ("false", "0", "no", "off")
BOTS_PROCESS = None

def safe_print(message: str):
    """Print message with Unicode encoding fallback for Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback for Windows console that doesn't support Unicode
        # Replace emojis with ASCII equivalents
        message_ascii = message.replace('🤖', '[BOT]').replace('⚠️', '[WARN]')
        message_ascii = message_ascii.replace('✅', '[OK]').replace('❌', '[ERROR]')
        message_ascii = message_ascii.replace('🔍', '[CHECK]').replace('📦', '[BUILD]')
        message_ascii = message_ascii.replace('🚀', '[START]').replace('🌐', '[WEB]')
        print(message_ascii)

def start_trading_bots():
    """Start trading bots in background (enabled by default)"""
    global BOTS_PROCESS
    if not AUTO_START_BOTS:
        safe_print("⚠️ Trading bots auto-start is disabled (set AUTO_START_BOTS=true to enable)")
        return
    
    if BOTS_PROCESS is None:
        try:
            BASE_DIR = Path(__file__).parent.parent
            bots_script = BASE_DIR / "run_unified_bots.py"
            if bots_script.exists():
                safe_print("🤖 Auto-starting trading bots...")
                # Start bots in background
                BOTS_PROCESS = subprocess.Popen(
                    [sys.executable, str(bots_script)],
                    cwd=str(BASE_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                safe_print(f"✅ Trading bots started (PID: {BOTS_PROCESS.pid})")
        except Exception as e:
            safe_print(f"⚠️ Failed to start trading bots: {e}")

# Start bots on app startup (enabled by default)
@app.on_event("startup")
async def startup_event():
    # Start bots in a separate thread to avoid blocking
    threading.Thread(target=start_trading_bots, daemon=True).start()

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files
BASE_DIR = Path(__file__).parent.parent
FRONTEND_BUILD_DIR = BASE_DIR / "frontend" / "build"

# Mount static files if frontend build exists (but register API routes first)
# Static files mount (doesn't interfere with API routes)
if FRONTEND_BUILD_DIR.exists() and (FRONTEND_BUILD_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_BUILD_DIR / "static")), name="static")

# Base directory for trading outputs
OUTPUTS_DIR = BASE_DIR / "paper_trading_outputs"
LOGS_DIR = BASE_DIR / "paper_trading_outputs" / "logs"


def read_csv_safe(filepath: Path, limit: Optional[int] = None) -> List[Dict]:
    """Safely read CSV file and return as list of dicts"""
    try:
        if not filepath.exists():
            return []
        df = pd.read_csv(filepath)
        if limit:
            df = df.tail(limit)
        # Replace NaN with None, but keep numeric values as numbers
        # Convert to dict, preserving types
        records = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                # Keep NaN as empty string, but preserve other values
                if pd.isna(val):
                    record[col] = ""
                else:
                    record[col] = val
            records.append(record)
        return records
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []


def read_jsonl_safe(filepath: Path, limit: Optional[int] = None) -> List[Dict]:
    """Safely read JSONL file (compressed or not) and return as list of dicts"""
    try:
        if not filepath.exists():
            return []
        
        records = []
        open_func = gzip.open if filepath.suffix == ".gz" else open
        mode = "rt" if filepath.suffix == ".gz" else "r"
        
        with open_func(filepath, mode, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
                if limit and len(records) >= limit:
                    break
        
        return records[-limit:] if limit else records
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []


@app.get("/api")
@app.get("/api/")
async def api_root():
    """API root endpoint - lists available endpoints"""
    return {
        "name": "MetaStackerBandit API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "version": "/api/version",
            "health": "/api/health",
            "dashboard": "/api/dashboard/summary",
            "bots": "/api/bots/{version}",
            "logs": "/api/logs/{log_type}",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/version")
async def get_version():
    """Get API version and code verification"""
    # Check if 24h bot code is present
    import inspect
    source = inspect.getsource(get_dashboard_summary)
    has_24h_preinit = "required_bots = [\"5m\", \"1h\", \"12h\", \"24h\"]" in source
    has_24h_assert = "\"24h\" in summary[\"bots\"]" in source
    
    return {
        "version": "1.0.0",
        "has_24h_preinit": has_24h_preinit,
        "has_24h_assert": has_24h_assert,
        "code_checks": {
            "preinit_24h": has_24h_preinit,
            "assert_24h": has_24h_assert,
            "source_length": len(source)
        }
    }


@app.get("/api/debug/bots")
async def debug_bots():
    """Debug endpoint to check bot data structure"""
    summary = await get_dashboard_summary()
    status = await get_bots_status()
    
    file_checks = {}
    for version in ["5m", "1h", "12h", "24h"]:
        suffix = f"_{version}" if version not in ["5m", "24h"] else ""
        equity_file = OUTPUTS_DIR / version / "sheets_fallback" / f"equity{suffix}.csv"
        signals_file = OUTPUTS_DIR / version / "sheets_fallback" / f"signals{suffix}.csv"
        
        file_checks[version] = {
            "equity_file": str(equity_file),
            "signals_file": str(signals_file),
            "equity_exists": equity_file.exists(),
            "signals_exists": signals_file.exists(),
            "directory_exists": (OUTPUTS_DIR / version).exists(),
            "sheets_fallback_exists": (OUTPUTS_DIR / version / "sheets_fallback").exists()
        }
    
    return {
        "dashboard_summary": summary,
        "bots_status": status,
        "file_checks": file_checks,
        "outputs_dir": str(OUTPUTS_DIR),
        "outputs_dir_exists": OUTPUTS_DIR.exists()
    }


@app.get("/api/bots/status")
async def get_bots_status():
    """Get status of all bot versions"""
    bots = {}
    
    # CRITICAL: Always process all 4 bots, including 24h
    for version in ["5m", "1h", "12h", "24h"]:
        version_dir = OUTPUTS_DIR / version
        # 5m and 24h use no suffix, 1h and 12h use suffix
        suffix = f"_{version}" if version in ["1h", "12h"] else ""
        equity_file = version_dir / "sheets_fallback" / f"equity{suffix}.csv"
        signals_file = version_dir / "sheets_fallback" / f"signals{suffix}.csv"
        
        equity_data = read_csv_safe(equity_file, limit=1)
        signals_data = read_csv_safe(signals_file, limit=1)
        
        bots[version] = {
            "status": "running" if equity_file.exists() or signals_file.exists() else "unknown",
            "last_equity": equity_data[-1] if equity_data else None,
            "last_signal": signals_data[-1] if signals_data else None,
            "has_data": equity_file.exists() or signals_file.exists()
        }
    
    return {"bots": bots}


def calculate_advanced_metrics(equity_df: pd.DataFrame, signals_df: pd.DataFrame = None, executions_df: pd.DataFrame = None):
    """Calculate advanced trading metrics from equity and trading data"""
    if equity_df.empty:
        return {}

    # Ensure proper data types
    equity_df['ts_iso'] = pd.to_datetime(equity_df['ts_iso'])
    equity_df = equity_df.sort_values('ts_iso')
    equity_df['equity'] = pd.to_numeric(equity_df['equity'], errors='coerce')
    equity_df['realized'] = pd.to_numeric(equity_df['realized'], errors='coerce')
    equity_df['unrealized'] = pd.to_numeric(equity_df['unrealized'], errors='coerce')
    equity_df['last_price'] = pd.to_numeric(equity_df['last_price'], errors='coerce')

    # Drop NaN values
    equity_df = equity_df.dropna(subset=['equity'])

    if len(equity_df) < 2:
        return {}

    # Calculate returns
    equity_df['returns'] = equity_df['equity'].pct_change()
    equity_df['returns'] = equity_df['returns'].fillna(0)

    # Calculate drawdowns
    equity_df['cumulative_max'] = equity_df['equity'].cummax()
    equity_df['drawdown'] = (equity_df['equity'] - equity_df['cumulative_max']) / equity_df['cumulative_max']
    equity_df['drawdown_pct'] = equity_df['drawdown'] * 100

    # Risk metrics
    returns_mean = equity_df['returns'].mean()
    returns_std = equity_df['returns'].std()

    # Sharpe Ratio (annualized, assuming daily data)
    if returns_std > 0:
        sharpe_ratio = (returns_mean / returns_std) * np.sqrt(252)  # Assuming ~252 trading days/year
    else:
        sharpe_ratio = 0

    # Sortino Ratio (downside deviation)
    downside_returns = equity_df['returns'][equity_df['returns'] < 0]
    if len(downside_returns) > 0:
        downside_std = downside_returns.std()
        sortino_ratio = returns_mean / downside_std * np.sqrt(252) if downside_std > 0 else 0
    else:
        sortino_ratio = 0

    # Calmar Ratio
    max_drawdown = abs(equity_df['drawdown'].min()) if len(equity_df['drawdown']) > 0 else 0
    annual_return = returns_mean * 252
    calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0

    # Rolling metrics (7-day and 30-day windows)
    window_7d = min(7, len(equity_df) - 1)
    window_30d = min(30, len(equity_df) - 1)

    if window_7d > 0:
        equity_df['sharpe_7d'] = equity_df['returns'].rolling(window=window_7d).apply(
            lambda x: (x.mean() / x.std()) * np.sqrt(252) if x.std() > 0 else 0
        )
        equity_df['volatility_7d'] = equity_df['returns'].rolling(window=window_7d).std() * np.sqrt(252) * 100
        equity_df['returns_7d'] = equity_df['returns'].rolling(window=window_7d).sum()

    if window_30d > 0:
        equity_df['sharpe_30d'] = equity_df['returns'].rolling(window=window_30d).apply(
            lambda x: (x.mean() / x.std()) * np.sqrt(252) if x.std() > 0 else 0
        )
        equity_df['volatility_30d'] = equity_df['returns'].rolling(window=window_30d).std() * np.sqrt(252) * 100
        equity_df['returns_30d'] = equity_df['returns'].rolling(window=window_30d).sum()

    # Win rate and profit factor from signals/executions
    win_rate = 0
    profit_factor = 0
    total_trades = 0
    winning_trades = 0
    gross_profit = 0
    gross_loss = 0

    if executions_df is not None and not executions_df.empty:
        executions_df['realized_pnl'] = pd.to_numeric(executions_df['realized_pnl'], errors='coerce')
        executions_df = executions_df.dropna(subset=['realized_pnl'])

        if not executions_df.empty:
            total_trades = len(executions_df)
            winning_trades = len(executions_df[executions_df['realized_pnl'] > 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0

            gross_profit = executions_df[executions_df['realized_pnl'] > 0]['realized_pnl'].sum()
            gross_loss = abs(executions_df[executions_df['realized_pnl'] < 0]['realized_pnl'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # BTC correlation (using last_price as proxy)
    btc_correlation = 0
    if len(equity_df) > 1:
        price_returns = equity_df['last_price'].pct_change().fillna(0)
        equity_returns = equity_df['returns']
        if price_returns.std() > 0 and equity_returns.std() > 0:
            btc_correlation = price_returns.corr(equity_returns)

    # Calculate alpha and beta (simplified, using price as market proxy)
    if len(equity_df) > 1 and returns_std > 0:
        price_returns = equity_df['last_price'].pct_change().fillna(0)
        market_std = price_returns.std()
        if market_std > 0:
            beta = (price_returns.cov(equity_df['returns']) / (price_returns.var())) if price_returns.var() > 0 else 0
            alpha = returns_mean - beta * price_returns.mean()
        else:
            beta = 0
            alpha = 0
    else:
        beta = 0
        alpha = 0

    # Current metrics summary
    current_metrics = {
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio,
        'max_drawdown_pct': max_drawdown * 100,
        'volatility': returns_std * np.sqrt(252) * 100,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        'btc_correlation': btc_correlation,
        'beta': beta,
        'alpha': alpha,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'avg_win': gross_profit / winning_trades if winning_trades > 0 else 0,
        'avg_loss': gross_loss / (total_trades - winning_trades) if (total_trades - winning_trades) > 0 else 0
    }

    return equity_df, current_metrics


@app.get("/api/bots/{version}/equity")
async def get_equity(version: str, limit: Optional[int] = 200):
    """Get comprehensive equity data with advanced metrics for a specific bot version"""
    if version not in ["5m", "1h", "12h", "24h"]:
        raise HTTPException(status_code=400, detail="Invalid version. Use: 5m, 1h, 12h, or 24h")

    # 5m and 24h use no suffix, 1h and 12h use suffix
    suffix = f"_{version}" if version in ["1h", "12h"] else ""
    equity_file = OUTPUTS_DIR / version / "sheets_fallback" / f"equity{suffix}.csv"
    signals_file = OUTPUTS_DIR / version / "sheets_fallback" / f"signals{suffix}.csv"

    # 5m and 24h have executions file
    executions_file = None
    if version in ["5m", "24h"]:
        executions_file = OUTPUTS_DIR / version / "sheets_fallback" / "executions_paper.csv"

    # Read data
    equity_data = read_csv_safe(equity_file, limit=limit)
    signals_data = read_csv_safe(signals_file, limit=limit)
    executions_data = read_csv_safe(executions_file, limit=limit) if executions_file else []

    if not equity_data:
        return {"version": version, "data": [], "metrics": {}, "count": 0}

    # Convert to DataFrames for calculations
    equity_df = pd.DataFrame(equity_data)
    signals_df = pd.DataFrame(signals_data) if signals_data else pd.DataFrame()
    executions_df = pd.DataFrame(executions_data) if executions_data else pd.DataFrame()

    # Calculate advanced metrics
    enhanced_equity_df, current_metrics = calculate_advanced_metrics(equity_df, signals_df, executions_df)

    # Convert back to dict format for JSON response
    enhanced_data = []
    for _, row in enhanced_equity_df.iterrows():
        data_point = {
            'ts_iso': row['ts_iso'].isoformat() if pd.notna(row['ts_iso']) else '',
            'ts': row.get('ts', ''),
            'equity': float(row['equity']) if pd.notna(row['equity']) else 0,
            'realized': float(row['realized']) if pd.notna(row['realized']) else 0,
            'unrealized': float(row['unrealized']) if pd.notna(row['unrealized']) else 0,
            'last_price': float(row['last_price']) if pd.notna(row['last_price']) else 0,
            'returns': float(row['returns']) if pd.notna(row['returns']) else 0,
            'drawdown': float(row['drawdown']) if pd.notna(row['drawdown']) else 0,
            'drawdown_pct': float(row['drawdown_pct']) if pd.notna(row['drawdown_pct']) else 0
        }

        # Add rolling metrics if available
        if 'sharpe_7d' in row and pd.notna(row['sharpe_7d']):
            data_point['sharpe_7d'] = float(row['sharpe_7d'])
        if 'sharpe_30d' in row and pd.notna(row['sharpe_30d']):
            data_point['sharpe_30d'] = float(row['sharpe_30d'])
        if 'volatility_7d' in row and pd.notna(row['volatility_7d']):
            data_point['volatility_7d'] = float(row['volatility_7d'])
        if 'volatility_30d' in row and pd.notna(row['volatility_30d']):
            data_point['volatility_30d'] = float(row['volatility_30d'])
        if 'returns_7d' in row and pd.notna(row['returns_7d']):
            data_point['returns_7d'] = float(row['returns_7d'])
        if 'returns_30d' in row and pd.notna(row['returns_30d']):
            data_point['returns_30d'] = float(row['returns_30d'])

        enhanced_data.append(data_point)

    return {
        "version": version,
        "data": enhanced_data,
        "metrics": current_metrics,
        "count": len(enhanced_data),
        "hasMetrics": bool(current_metrics),
        "metricsKeys": list(current_metrics.keys()) if current_metrics else []
    }


@app.get("/api/bots/{version}/signals")
async def get_signals(version: str, limit: Optional[int] = 100):
    """Get trading signals for a specific bot version"""
    if version not in ["5m", "1h", "12h", "24h"]:
        raise HTTPException(status_code=400, detail="Invalid version. Use: 5m, 1h, 12h, or 24h")
    
    # 5m and 24h use no suffix, 1h and 12h use suffix
    suffix = f"_{version}" if version in ["1h", "12h"] else ""
    signals_file = OUTPUTS_DIR / version / "sheets_fallback" / f"signals{suffix}.csv"
    
    data = read_csv_safe(signals_file, limit=limit)
    file_exists = signals_file.exists()
    
    # If no CSV data, try reading from signals.jsonl as fallback (check multiple locations)
    if not data:
        signals_jsonl_paths = [
            OUTPUTS_DIR / version / "logs" / "signals" / "signals.jsonl",  # Direct location
            OUTPUTS_DIR / version / "logs" / "default" / "signals" / "signals.jsonl",  # 5m bot location
            OUTPUTS_DIR / version / "logs" / version / "signals" / "signals.jsonl",  # Nested location
        ]
        
        for signals_jsonl_file in signals_jsonl_paths:
            if signals_jsonl_file.exists():
                signals_jsonl_data = read_jsonl_safe(signals_jsonl_file, limit=limit)
                # Convert signals.jsonl format to CSV-like format
                data = []
                for item in signals_jsonl_data:
                    signal_item = {}
                    
                    if item.get("sanitized"):
                        # Handle sanitized format from log router
                        sanitized = item["sanitized"]
                        decision = sanitized.get("decision", {})
                        model = sanitized.get("model", {})
                        features = sanitized.get("features", {})
                        
                        signal_item = {
                            "ts_iso": item.get("ts_ist", item.get("ts_iso", "")),
                            "ts": item.get("ts", ""),
                            "symbol": sanitized.get("symbol", ""),
                            "dir": decision.get("dir", ""),
                            "S_top": decision.get("S_top", model.get("S_top", "")),
                            "S_bot": decision.get("S_bot", model.get("S_bot", "")),
                            "alpha": decision.get("alpha", model.get("alpha", "")),
                            "close": features.get("close", features.get("price", "")),
                            "volume": features.get("volume", ""),
                        }
                    else:
                        # Handle direct format from log emitter
                        decision = item.get("decision", {})
                        decision_details = decision.get("details", {})
                        signals_dict = decision_details.get("signals", {})
                        model_out = item.get("model_out", {})
                        features = item.get("features", [])
                        
                        # Extract S_top and S_bot from decision.details.signals
                        S_top = signals_dict.get("S_top", "")
                        S_bot = signals_dict.get("S_bot", "")
                        
                        signal_item = {
                            "ts_iso": item.get("ts_ist", item.get("ts_iso", "")),
                            "ts": item.get("ts", ""),
                            "symbol": item.get("symbol", ""),
                            "dir": decision.get("dir", ""),
                            "S_top": S_top,
                            "S_bot": S_bot,
                            "alpha": decision.get("alpha", model_out.get("s_model", "")),
                            "close": "",  # Features is an array, not a dict
                            "volume": "",  # Features is an array, not a dict
                        }
                    
                    if signal_item:
                        data.append(signal_item)
                if data:
                    file_exists = True
                    break
    
    return {
        "version": version,
        "data": data,
        "count": len(data),
        "file_exists": file_exists,
        "hasData": len(data) > 0
    }


@app.get("/api/bots/{version}/executions")
async def get_executions(version: str, limit: Optional[int] = 100):
    """Get execution data for a specific bot version"""
    if version not in ["5m", "1h", "12h", "24h"]:
        raise HTTPException(status_code=400, detail="Invalid version. Use: 5m, 1h, 12h, or 24h")
    
    # 5m and 24h have executions file
    if version not in ["5m", "24h"]:
        # 1h and 12h don't have executions file
        return {"version": version, "data": [], "count": 0}
    
    executions_file = OUTPUTS_DIR / version / "sheets_fallback" / "executions_paper.csv"
    data = read_csv_safe(executions_file, limit=limit)
    file_exists = executions_file.exists()
    
    # If no CSV data, try reading from execution logs as fallback (check multiple locations)
    if not data:
        execution_jsonl_paths = [
            OUTPUTS_DIR / version / "logs" / "execution" / "execution.jsonl",  # Direct location
            OUTPUTS_DIR / version / "logs" / version / "execution_log" / f"date={datetime.now().strftime('%Y-%m-%d')}" / "asset=BTCUSDT" / "execution_log.jsonl.gz",  # Date-partitioned
        ]
        
        # Also try to find latest date if today's doesn't exist
        execution_log_dir = OUTPUTS_DIR / version / "logs" / version / "execution_log"
        if execution_log_dir.exists():
            dates = []
            for item in execution_log_dir.iterdir():
                if item.is_dir() and item.name.startswith("date="):
                    dates.append(item.name.replace("date=", ""))
            if dates:
                latest_date = sorted(dates, reverse=True)[0]
                execution_jsonl_paths.append(
                    execution_log_dir / f"date={latest_date}" / "asset=BTCUSDT" / "execution_log.jsonl.gz"
                )
        
        for execution_jsonl_file in execution_jsonl_paths:
            if execution_jsonl_file.exists():
                execution_jsonl_data = read_jsonl_safe(execution_jsonl_file, limit=limit)
                # Convert execution.jsonl format to CSV-like format
                data = []
                for item in execution_jsonl_data:
                    if item.get("sanitized"):
                        # Handle sanitized format from log router
                        sanitized = item["sanitized"]
                        exec_data = sanitized.get("exec", sanitized.get("execution", {}))
                        risk_data = sanitized.get("risk", sanitized.get("risk_state", {}))
                        
                        execution_item = {
                            "ts_iso": item.get("ts_iso", ""),
                            "ts": item.get("ts", ""),
                            "symbol": sanitized.get("symbol", ""),
                            "side": exec_data.get("side", ""),
                            "qty": exec_data.get("qty", exec_data.get("size", "")),
                            "fill_price": exec_data.get("fill_price", exec_data.get("price", "")),
                            "notional_usd": exec_data.get("notional_usd", ""),
                            "realized_pnl": risk_data.get("realized_pnl", ""),
                            "unrealized_pnl": risk_data.get("unrealized_pnl", ""),
                        }
                        data.append(execution_item)
                    elif item.get("execution"):
                        # Handle direct execution format
                        exec_data = item["execution"]
                        risk_data = item.get("risk_state", {})
                        
                        execution_item = {
                            "ts_iso": item.get("ts_ist", item.get("ts_iso", "")),
                            "ts": item.get("ts", ""),
                            "symbol": item.get("symbol", ""),
                            "side": exec_data.get("side", ""),
                            "qty": exec_data.get("qty", exec_data.get("size", "")),
                            "fill_price": exec_data.get("fill_price", exec_data.get("price", "")),
                            "notional_usd": exec_data.get("notional_usd", ""),
                            "realized_pnl": risk_data.get("realized_pnl", ""),
                            "unrealized_pnl": risk_data.get("unrealized_pnl", ""),
                        }
                        data.append(execution_item)
                    else:
                        data.append(item)
                if data:
                    file_exists = True
                    break
    
    return {
        "version": version,
        "data": data,
        "count": len(data),
        "file_exists": file_exists,
        "hasData": len(data) > 0
    }


@app.get("/api/bots/{version}/health")
async def get_health_metrics(version: str, limit: Optional[int] = 100):
    """Get health metrics for a specific bot version"""
    if version not in ["5m", "1h", "12h", "24h"]:
        raise HTTPException(status_code=400, detail="Invalid version. Use: 5m, 1h, 12h, or 24h")
    
    # 5m and 24h use no suffix, 1h and 12h use suffix
    suffix = f"_{version}" if version in ["1h", "12h"] else ""
    health_file = OUTPUTS_DIR / version / "sheets_fallback" / f"health_metrics{suffix}.csv"
    
    # Try alternative names if primary doesn't exist (for 1h and 12h)
    if not health_file.exists() and version in ["1h", "12h"]:
        # Try without suffix
        alt_file = OUTPUTS_DIR / version / "sheets_fallback" / "health_metrics.csv"
        if alt_file.exists():
            health_file = alt_file
    
    data = read_csv_safe(health_file, limit=limit)
    file_exists = health_file.exists()
    
    # If still no data, try reading from bot's own log directory (health.jsonl)
    if not data:
        health_jsonl_file = OUTPUTS_DIR / version / "logs" / "health" / "health.jsonl"
        if health_jsonl_file.exists():
            health_jsonl_data = read_jsonl_safe(health_jsonl_file, limit=limit)
            # Convert health.jsonl format to CSV-like format
            data = []
            for item in health_jsonl_data:
                if item.get("metrics"):
                    metrics = item["metrics"]
                    health_item = {
                        "ts_iso": item.get("ts_ist", item.get("ts_iso", "")),
                        "ts": item.get("ts", ""),
                        **metrics
                    }
                    data.append(health_item)
                else:
                    data.append(item)
            if data:
                file_exists = True
    
    # If still no data, try reading from KPI scorecard logs as fallback
    if not data:
        # Try bot-specific KPI logs first
        bot_kpi_dir = OUTPUTS_DIR / version / "logs" / "kpi_scorecard"
        if bot_kpi_dir.exists():
            dates = []
            for item in bot_kpi_dir.iterdir():
                if item.is_dir() and item.name.startswith("date="):
                    dates.append(item.name.replace("date=", ""))
            if dates:
                latest_date = sorted(dates, reverse=True)[0]
                kpi_log_file = bot_kpi_dir / f"date={latest_date}" / "asset=BTCUSDT" / "kpi_scorecard.jsonl.gz"
                if not kpi_log_file.exists():
                    kpi_log_file = bot_kpi_dir / f"date={latest_date}" / "kpi_scorecard.jsonl.gz"
                if kpi_log_file.exists():
                    kpi_data = read_jsonl_safe(kpi_log_file, limit=limit)
                    # Convert KPI data to health metrics format
                    data = []
                    for item in kpi_data:
                        if item.get("sanitized"):
                            sanitized = item["sanitized"]
                            health_item = {
                                "ts_iso": item.get("ts_iso", ""),
                                "ts": item.get("ts", ""),
                                "Sharpe_roll_1d": sanitized.get("sharpe_1w", ""),
                                "max_dd_to_date": sanitized.get("max_dd_pct", ""),
                                "ic_drift": sanitized.get("ic_drift", ""),
                                **sanitized
                            }
                            data.append(health_item)
                        else:
                            data.append(item)
                    if data:
                        file_exists = True
        
        # Also try legacy location
        if not data:
            kpi_file = LOGS_DIR / "kpi_scorecard"
            if kpi_file.exists():
                # Try latest date
                dates = []
                for item in kpi_file.iterdir():
                    if item.is_dir() and item.name.startswith("date="):
                        dates.append(item.name.replace("date=", ""))
                if dates:
                    latest_date = sorted(dates, reverse=True)[0]
                    kpi_log_file = kpi_file / f"date={latest_date}" / "asset=BTCUSDT" / "kpi_scorecard.jsonl.gz"
                    if kpi_log_file.exists():
                        kpi_data = read_jsonl_safe(kpi_log_file, limit=limit)
                        # Convert KPI data to health metrics format
                        data = []
                        for item in kpi_data:
                            if item.get("sanitized"):
                                sanitized = item["sanitized"]
                                health_item = {
                                    "ts_iso": item.get("ts_iso", ""),
                                    "ts": item.get("ts", ""),
                                    "Sharpe_roll_1d": sanitized.get("sharpe_1w", ""),
                                    "max_dd_to_date": sanitized.get("max_dd_pct", ""),
                                    "ic_drift": sanitized.get("ic_drift", ""),
                                    **sanitized
                                }
                                data.append(health_item)
                            else:
                                data.append(item)
                        if data:
                            file_exists = True
    
    # Normalize field names for frontend compatibility
    # Map common variations to expected frontend field names
    normalized_data = []
    for item in data:
        normalized_item = dict(item)  # Copy original item
        
        # Map Sharpe variations
        if "Sharpe_1w" in normalized_item and "Sharpe_roll_1d" not in normalized_item:
            normalized_item["Sharpe_roll_1d"] = normalized_item.get("Sharpe_1w", "")
        if "sharpe_1w" in normalized_item and "Sharpe_roll_1d" not in normalized_item:
            normalized_item["Sharpe_roll_1d"] = normalized_item.get("sharpe_1w", "")
        if "Sharpe_roll_1d" not in normalized_item:
            # Try to find any Sharpe field
            for key in normalized_item.keys():
                if "sharpe" in key.lower() and "1" in key.lower():
                    normalized_item["Sharpe_roll_1d"] = normalized_item[key]
                    break
        
        # Map max drawdown variations
        if "max_DD_pct" in normalized_item and "max_dd_to_date" not in normalized_item:
            normalized_item["max_dd_to_date"] = normalized_item.get("max_DD_pct", "")
        if "max_dd_pct" in normalized_item and "max_dd_to_date" not in normalized_item:
            normalized_item["max_dd_to_date"] = normalized_item.get("max_dd_pct", "")
        if "max_dd_to_date" not in normalized_item:
            # Try to find any max drawdown field
            for key in normalized_item.keys():
                if "max" in key.lower() and ("dd" in key.lower() or "drawdown" in key.lower()):
                    normalized_item["max_dd_to_date"] = normalized_item[key]
                    break
        
        # Map IC drift (usually already correct, but check variations)
        if "ic_drift" not in normalized_item:
            for key in normalized_item.keys():
                if "ic" in key.lower() and "drift" in key.lower():
                    normalized_item["ic_drift"] = normalized_item[key]
                    break
        
        normalized_data.append(normalized_item)
    
    return {"version": version, "data": normalized_data, "count": len(normalized_data), "file_exists": file_exists}


@app.get("/api/bots/{version}/bandit")
async def get_bandit_stats(version: str, limit: Optional[int] = 100):
    """Get bandit statistics for a specific bot version"""
    if version not in ["5m", "1h", "12h", "24h"]:
        raise HTTPException(status_code=400, detail="Invalid version. Use: 5m, 1h, 12h, or 24h")
    
    # 5m and 24h use no suffix, 1h and 12h use suffix
    suffix = f"_{version}" if version in ["1h", "12h"] else ""
    bandit_file = OUTPUTS_DIR / version / "sheets_fallback" / f"bandit{suffix}.csv"
    
    data = read_csv_safe(bandit_file, limit=limit)
    return {"version": version, "data": data, "count": len(data)}


@app.get("/api/bots/{version}/overlay")
async def get_overlay(version: str, limit: Optional[int] = 100):
    """Get overlay data for a specific bot version"""
    if version not in ["5m", "1h", "12h", "24h"]:
        raise HTTPException(status_code=400, detail="Invalid version. Use: 5m, 1h, 12h, or 24h")
    
    # 5m and 24h use no suffix, 1h and 12h use suffix
    suffix = f"_{version}" if version in ["1h", "12h"] else ""
    overlay_file = OUTPUTS_DIR / version / "sheets_fallback" / f"overlay{suffix}.csv"
    
    data = read_csv_safe(overlay_file, limit=limit)
    return {"version": version, "data": data, "count": len(data)}


@app.get("/api/logs/types")
async def get_log_types(bot_version: Optional[str] = None):
    """Get list of available log types
    
    Args:
        bot_version: Optional bot version filter (5m, 1h, 12h, 24h). If None, returns log types from all bots.
    """
    log_types = set()
    
    # LogEmitter writes to: paper_trading_outputs/{bot_version}/logs/{log_type}/
    # Also check legacy location: paper_trading_outputs/logs/{bot_version}/{log_type}/
    # If bot_version is specified, only check that bot; otherwise check all bots
    if bot_version and bot_version in ["5m", "1h", "12h", "24h"]:
        bot_versions = [bot_version]
    else:
        bot_versions = ["5m", "1h", "12h", "24h"]
    
    # Check bot version directories (correct location)
    # Logs can be in two places:
    # 1. paper_trading_outputs/{version}/logs/{log_type}/ (direct)
    # 2. paper_trading_outputs/{version}/logs/{version}/{log_type}/ (nested)
    for version in bot_versions:
        version_logs_dir = OUTPUTS_DIR / version / "logs"
        if version_logs_dir.exists():
            # Check direct log types
            for item in version_logs_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Skip the nested version directory (we'll check it separately)
                    if item.name == version:
                        continue
                    # Check if this has log files
                    has_logs = False
                    for subitem in item.iterdir():
                        if subitem.is_dir() and subitem.name.startswith("date="):
                            has_logs = True
                            break
                        elif subitem.name.endswith(".jsonl") or subitem.name.endswith(".jsonl.gz"):
                            has_logs = True
                            break
                    
                    if has_logs:
                        log_types.add(item.name)
            
            # Check nested log types (paper_trading_outputs/{version}/logs/{version}/{log_type}/)
            nested_version_dir = version_logs_dir / version
            if nested_version_dir.exists():
                for item in nested_version_dir.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        has_logs = False
                        for subitem in item.iterdir():
                            if subitem.is_dir() and subitem.name.startswith("date="):
                                has_logs = True
                                break
                            elif subitem.name.endswith(".jsonl") or subitem.name.endswith(".jsonl.gz"):
                                has_logs = True
                                break
                        
                        if has_logs:
                            log_types.add(item.name)
    
    # Also check legacy location (paper_trading_outputs/logs/)
    if LOGS_DIR.exists():
        # Check root level log types
        for item in LOGS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                has_logs = False
                for subitem in item.iterdir():
                    if subitem.is_dir() and subitem.name.startswith("date="):
                        has_logs = True
                        break
                    elif subitem.name.endswith(".jsonl") or subitem.name.endswith(".jsonl.gz"):
                        has_logs = True
                        break
                if has_logs:
                    log_types.add(item.name)
        
        # Check bot version directories in legacy location
        for version in bot_versions:
            version_dir = LOGS_DIR / version
            if version_dir.exists() and version_dir.is_dir():
                for item in version_dir.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        has_logs = False
                        for subitem in item.iterdir():
                            if subitem.is_dir() and subitem.name.startswith("date="):
                                has_logs = True
                                break
                            elif subitem.name.endswith(".jsonl") or subitem.name.endswith(".jsonl.gz"):
                                has_logs = True
                                break
                        if has_logs:
                            log_types.add(item.name)
    
    return {"log_types": sorted(log_types)}


@app.get("/api/logs/{log_type}/dates")
async def get_log_dates(log_type: str, bot_version: Optional[str] = None):
    """Get available dates for a log type
    
    Args:
        log_type: Type of log
        bot_version: Optional bot version filter (5m, 1h, 12h, 24h). If None, returns dates from all bots.
    """
    dates = set()
    # If bot_version is specified, only check that bot; otherwise check all bots
    if bot_version and bot_version in ["5m", "1h", "12h", "24h"]:
        bot_versions = [bot_version]
    else:
        bot_versions = ["5m", "1h", "12h", "24h"]
    
    # Check bot version directories (correct location)
    # Check both direct and nested locations
    for version in bot_versions:
        # Direct: paper_trading_outputs/{version}/logs/{log_type}/
        version_log_dir = OUTPUTS_DIR / version / "logs" / log_type
        if version_log_dir.exists():
            for item in version_log_dir.iterdir():
                if item.is_dir() and item.name.startswith("date="):
                    date_str = item.name.replace("date=", "")
                    dates.add(date_str)
        
        # Nested: paper_trading_outputs/{version}/logs/{version}/{log_type}/
        nested_log_dir = OUTPUTS_DIR / version / "logs" / version / log_type
        if nested_log_dir.exists():
            for item in nested_log_dir.iterdir():
                if item.is_dir() and item.name.startswith("date="):
                    date_str = item.name.replace("date=", "")
                    dates.add(date_str)
    
    # Also check legacy location (paper_trading_outputs/logs/)
    log_type_dir = LOGS_DIR / log_type
    if log_type_dir.exists():
        for item in log_type_dir.iterdir():
            if item.is_dir() and item.name.startswith("date="):
                date_str = item.name.replace("date=", "")
                dates.add(date_str)
    
    for version in bot_versions:
        version_log_dir = LOGS_DIR / version / log_type
        if version_log_dir.exists():
            for item in version_log_dir.iterdir():
                if item.is_dir() and item.name.startswith("date="):
                    date_str = item.name.replace("date=", "")
                    dates.add(date_str)
    
    return {"log_type": log_type, "dates": sorted(dates, reverse=True)}


@app.get("/api/logs/{log_type}")
async def get_logs(log_type: str, date: Optional[str] = None, limit: Optional[int] = 100, asset: str = "BTCUSDT", bot_version: Optional[str] = None):
    """Get logs from JSONL files - checks bot version directories and legacy locations
    
    Args:
        log_type: Type of log to retrieve
        date: Optional date filter (YYYY-MM-DD)
        limit: Maximum number of logs to return
        asset: Asset filter (default: BTCUSDT)
        bot_version: Optional bot version filter (5m, 1h, 12h, 24h). If None, returns logs from all bots.
    """
    all_dates = set()
    # If bot_version is specified, only check that bot; otherwise check all bots
    if bot_version and bot_version in ["5m", "1h", "12h", "24h"]:
        bot_versions = [bot_version]
    else:
        bot_versions = ["5m", "1h", "12h", "24h"]
    
    # Collect dates from bot version directories (correct location)
    for version in bot_versions:
        version_log_dir = OUTPUTS_DIR / version / "logs" / log_type
        if version_log_dir.exists():
            for item in version_log_dir.iterdir():
                if item.is_dir() and item.name.startswith("date="):
                    all_dates.add(item.name.replace("date=", ""))
    
    # Also collect dates from legacy location
    log_type_dir = LOGS_DIR / log_type
    if log_type_dir.exists():
        for item in log_type_dir.iterdir():
            if item.is_dir() and item.name.startswith("date="):
                all_dates.add(item.name.replace("date=", ""))
    
    for version in bot_versions:
        version_log_dir = LOGS_DIR / version / log_type
        if version_log_dir.exists():
            for item in version_log_dir.iterdir():
                if item.is_dir() and item.name.startswith("date="):
                    all_dates.add(item.name.replace("date=", ""))
    
    if date is None:
        if all_dates:
            date = sorted(all_dates, reverse=True)[0]
        else:
            date = datetime.now().strftime("%Y-%m-%d")
    
    # Try multiple paths in order of preference
    # Correct location: paper_trading_outputs/{version}/logs/{log_type}/ (direct)
    # Also: paper_trading_outputs/{version}/logs/{version}/{log_type}/ (nested)
    log_file = None
    paths_to_try = []
    
    # First try correct location (bot version directories)
    for version in bot_versions:
        # Direct location
        paths_to_try.extend([
            OUTPUTS_DIR / version / "logs" / log_type / f"date={date}" / f"asset={asset}" / f"{log_type}.jsonl.gz",
            OUTPUTS_DIR / version / "logs" / log_type / f"date={date}" / f"{log_type}.jsonl.gz",
            OUTPUTS_DIR / version / "logs" / log_type / f"{log_type}.jsonl",
            OUTPUTS_DIR / version / "logs" / log_type / f"{log_type}.jsonl.gz",
        ])
        # Nested location
        paths_to_try.extend([
            OUTPUTS_DIR / version / "logs" / version / log_type / f"date={date}" / f"asset={asset}" / f"{log_type}.jsonl.gz",
            OUTPUTS_DIR / version / "logs" / version / log_type / f"date={date}" / f"{log_type}.jsonl.gz",
            OUTPUTS_DIR / version / "logs" / version / log_type / f"{log_type}.jsonl",
            OUTPUTS_DIR / version / "logs" / version / log_type / f"{log_type}.jsonl.gz",
        ])
    
    # Also try legacy location
    paths_to_try.extend([
        LOGS_DIR / log_type / f"date={date}" / f"asset={asset}" / f"{log_type}.jsonl.gz",
        LOGS_DIR / log_type / f"date={date}" / f"{log_type}.jsonl.gz",
        LOGS_DIR / log_type / f"{log_type}.jsonl.gz",
    ])
    
    for version in bot_versions:
        paths_to_try.extend([
            LOGS_DIR / version / log_type / f"date={date}" / f"asset={asset}" / f"{log_type}.jsonl.gz",
            LOGS_DIR / version / log_type / f"date={date}" / f"{log_type}.jsonl.gz",
            LOGS_DIR / version / log_type / f"{log_type}.jsonl.gz",
        ])
    
    # Find first existing file
    for path in paths_to_try:
        if path.exists():
            log_file = path
            break
    
    # If no date-partitioned file found, try reading from specified bot versions and merge
    if log_file is None:
        all_data = []
        # Only check the specified bot versions (already filtered above)
        for version in bot_versions:
            # Try direct location first
            version_log_dir = OUTPUTS_DIR / version / "logs" / log_type
            if version_log_dir.exists():
                # Try date-partitioned
                date_file = version_log_dir / f"date={date}" / f"asset={asset}" / f"{log_type}.jsonl.gz"
                if not date_file.exists():
                    date_file = version_log_dir / f"date={date}" / f"{log_type}.jsonl.gz"
                if not date_file.exists():
                    date_file = version_log_dir / f"{log_type}.jsonl"
                if not date_file.exists():
                    date_file = version_log_dir / f"{log_type}.jsonl.gz"
                
                if date_file.exists():
                    version_data = read_jsonl_safe(date_file, limit=limit)
                    all_data.extend(version_data)
            
            # Also try nested location
            nested_log_dir = OUTPUTS_DIR / version / "logs" / version / log_type
            if nested_log_dir.exists():
                date_file = nested_log_dir / f"date={date}" / f"asset={asset}" / f"{log_type}.jsonl.gz"
                if not date_file.exists():
                    date_file = nested_log_dir / f"date={date}" / f"{log_type}.jsonl.gz"
                if not date_file.exists():
                    date_file = nested_log_dir / f"{log_type}.jsonl"
                if not date_file.exists():
                    date_file = nested_log_dir / f"{log_type}.jsonl.gz"
                
                if date_file.exists():
                    version_data = read_jsonl_safe(date_file, limit=limit)
                    all_data.extend(version_data)
        
        # Also try legacy location (only if no bot_version filter or if it's in legacy location)
        # Legacy location doesn't have bot-specific structure, so only check if no bot_version filter
        if not bot_version:
            root_file = LOGS_DIR / log_type / f"date={date}" / f"asset={asset}" / f"{log_type}.jsonl.gz"
            if not root_file.exists():
                root_file = LOGS_DIR / log_type / f"date={date}" / f"{log_type}.jsonl.gz"
            if not root_file.exists():
                root_file = LOGS_DIR / log_type / f"{log_type}.jsonl.gz"
            
            if root_file.exists():
                root_data = read_jsonl_safe(root_file, limit=limit)
                all_data.extend(root_data)
        
        # Sort by timestamp and limit
        if all_data:
            # Try to sort by timestamp
            try:
                all_data.sort(key=lambda x: x.get('ts_iso', x.get('ts', x.get('timestamp', ''))), reverse=True)
            except:
                pass
            all_data = all_data[:limit] if limit else all_data
        
        return {
            "log_type": log_type,
            "date": date,
            "asset": asset,
            "data": all_data,
            "count": len(all_data),
            "file_exists": len(all_data) > 0
        }
    
    data = read_jsonl_safe(log_file, limit=limit)
    return {
        "log_type": log_type,
        "date": date,
        "asset": asset,
        "data": data,
        "count": len(data),
        "file_exists": log_file.exists()
    }


@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Get summary data for dashboard"""
    summary = {
        "bots": {},
        "total_equity": 0,
        "total_signals": 0,
        "last_update": datetime.now().isoformat()
    }
    
    for version in ["5m", "1h", "12h", "24h"]:
        # 5m and 24h use no suffix, 1h and 12h use suffix
        suffix = f"_{version}" if version in ["1h", "12h"] else ""
        
        equity_file = OUTPUTS_DIR / version / "sheets_fallback" / f"equity{suffix}.csv"
        signals_file = OUTPUTS_DIR / version / "sheets_fallback" / f"signals{suffix}.csv"
        
        equity_data = read_csv_safe(equity_file, limit=1)
        signals_data = read_csv_safe(signals_file, limit=10)
        
        # If no signals from CSV, try JSONL fallback for dashboard summary
        if not signals_data:
            signals_jsonl_paths = [
                OUTPUTS_DIR / version / "logs" / "signals" / "signals.jsonl",
                OUTPUTS_DIR / version / "logs" / "default" / "signals" / "signals.jsonl",
                OUTPUTS_DIR / version / "logs" / version / "signals" / "signals.jsonl",
            ]
            for signals_jsonl_file in signals_jsonl_paths:
                if signals_jsonl_file.exists():
                    signals_jsonl_data = read_jsonl_safe(signals_jsonl_file, limit=10)
                    if signals_jsonl_data:
                        signals_data = signals_jsonl_data
                        break
        
        last_equity = equity_data[-1] if equity_data else {}
        equity_value = float(last_equity.get("equity", 0)) if last_equity and "equity" in last_equity else 0
        
        summary["bots"][version] = {
            "equity": equity_value,
            "signals_count": len(signals_data),
            "last_signal": signals_data[-1] if signals_data else None
        }
        summary["total_equity"] += equity_value
        summary["total_signals"] += len(signals_data)
    
    return summary


# Serve frontend routes (must be AFTER all API routes to avoid intercepting them)
if FRONTEND_BUILD_DIR.exists():
    @app.get("/", response_class=FileResponse)
    async def serve_frontend():
        """Serve React frontend"""
        index_file = FRONTEND_BUILD_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=500, detail="Frontend not built. Please build the frontend first.")
    
    # File browser endpoints (before catch-all route)
    @app.get("/api/files")
    async def list_files(
        path: str = Query("", description="Directory path relative to project root"),
        base: str = Query("paper_trading_outputs", description="Base directory: paper_trading_outputs or logs")
    ):
        """List files and directories in the specified path"""
        try:
            # Security: prevent directory traversal
            if ".." in path or path.startswith("/"):
                raise HTTPException(status_code=400, detail="Invalid path")
            
            # Determine base directory
            if base == "paper_trading_outputs":
                base_dir = OUTPUTS_DIR
            elif base == "logs":
                # Logs are actually stored in paper_trading_outputs/logs
                # Also check for root logs directory (for application logs like start_project.log)
                root_logs_dir = BASE_DIR / "logs"
                paper_logs_dir = OUTPUTS_DIR / "logs"
                
                # Prefer paper_trading_outputs/logs (where bot logs are)
                if paper_logs_dir.exists():
                    base_dir = paper_logs_dir
                elif root_logs_dir.exists():
                    base_dir = root_logs_dir
                else:
                    # Default to paper_trading_outputs/logs even if it doesn't exist yet
                    base_dir = paper_logs_dir
            else:
                raise HTTPException(status_code=400, detail="Invalid base directory")
            
            # Build full path
            if path:
                full_path = base_dir / path
            else:
                full_path = base_dir
            
            # Ensure path is within base directory (security)
            try:
                full_path = full_path.resolve()
                base_dir_resolved = base_dir.resolve()
                if not str(full_path).startswith(str(base_dir_resolved)):
                    raise HTTPException(status_code=403, detail="Access denied")
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid path")
            
            if not full_path.exists():
                raise HTTPException(status_code=404, detail="Path not found")
            
            if not full_path.is_dir():
                raise HTTPException(status_code=400, detail="Path is not a directory")
            
            # List files and directories
            items = []
            try:
                for item in sorted(full_path.iterdir()):
                    try:
                        stat = item.stat()
                        items.append({
                            "name": item.name,
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat.st_size if item.is_file() else None,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "path": str(item.relative_to(base_dir)).replace("\\", "/")
                        })
                    except (OSError, PermissionError):
                        continue
            except (OSError, PermissionError):
                # Directory might be empty or inaccessible
                pass
            
            return {
                "path": path,
                "base": base,
                "items": items,
                "parent": str(full_path.parent.relative_to(base_dir)).replace("\\", "/") if full_path != base_dir else None,
                "empty": len(items) == 0
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")
    
    @app.get("/api/files/download/{file_path:path}")
    async def download_file(file_path: str, base: str = Query("paper_trading_outputs", description="Base directory")):
        """Download a file"""
        try:
            # Security: prevent directory traversal
            if ".." in file_path or file_path.startswith("/"):
                raise HTTPException(status_code=400, detail="Invalid path")
            
            # Determine base directory
            if base == "paper_trading_outputs":
                base_dir = OUTPUTS_DIR
            elif base == "logs":
                # Logs are actually stored in paper_trading_outputs/logs
                # Also check for root logs directory (for application logs)
                root_logs_dir = BASE_DIR / "logs"
                paper_logs_dir = OUTPUTS_DIR / "logs"
                
                # Prefer paper_trading_outputs/logs (where bot logs are)
                if paper_logs_dir.exists():
                    base_dir = paper_logs_dir
                elif root_logs_dir.exists():
                    base_dir = root_logs_dir
                else:
                    # Default to paper_trading_outputs/logs
                    base_dir = paper_logs_dir
            else:
                raise HTTPException(status_code=400, detail="Invalid base directory")
            
            # Build full path
            full_path = base_dir / file_path
            
            # Ensure path is within base directory (security)
            try:
                full_path = full_path.resolve()
                base_dir_resolved = base_dir.resolve()
                if not str(full_path).startswith(str(base_dir_resolved)):
                    raise HTTPException(status_code=403, detail="Access denied")
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid path")
            
            if not full_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            if not full_path.is_file():
                raise HTTPException(status_code=400, detail="Path is not a file")
            
            # Determine media type
            media_type = "application/octet-stream"
            if file_path.endswith(".jsonl") or file_path.endswith(".json"):
                media_type = "application/json"
            elif file_path.endswith(".csv"):
                media_type = "text/csv"
            elif file_path.endswith(".log"):
                media_type = "text/plain"
            elif file_path.endswith(".gz"):
                media_type = "application/gzip"
            
            return FileResponse(
                str(full_path),
                media_type=media_type,
                filename=full_path.name,
                headers={"Content-Disposition": f'attachment; filename="{full_path.name}"'}
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")
    
    @app.get("/files", response_class=HTMLResponse)
    async def file_browser(
        path: str = Query("", description="Directory path"),
        base: str = Query("paper_trading_outputs", description="Base directory: paper_trading_outputs or logs")
    ):
        """Web-based file browser interface"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MetaStackerBandit - File Browser</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        h1 {{
            margin: 0 0 20px 0;
            color: #333;
        }}
        .breadcrumb {{
            margin-bottom: 20px;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 4px;
        }}
        .breadcrumb a {{
            color: #0066cc;
            text-decoration: none;
        }}
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}
        .controls {{
            margin-bottom: 20px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 4px;
        }}
        .controls select, .controls input {{
            padding: 8px;
            margin-right: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .controls button {{
            padding: 8px 16px;
            background: #0066cc;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        .controls button:hover {{
            background: #0052a3;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #f9f9f9;
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #ddd;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        .type-dir {{
            color: #0066cc;
            font-weight: bold;
        }}
        .type-file {{
            color: #666;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .size {{
            color: #999;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📁 File Browser - MetaStackerBandit</h1>
        
        <div class="controls">
            <label>Base Directory:</label>
            <select id="baseSelect" onchange="changeBase()">
                <option value="paper_trading_outputs" {'selected' if base == 'paper_trading_outputs' else ''}>paper_trading_outputs (Bot Data)</option>
                <option value="logs" {'selected' if base == 'logs' else ''}>logs (paper_trading_outputs/logs)</option>
            </select>
            <button onclick="refresh()">Refresh</button>
            <small style="margin-left: 10px; color: #666;">Note: Logs are stored in paper_trading_outputs/logs</small>
        </div>
        
        <div class="breadcrumb" id="breadcrumb">
            <a href="/files?base={base}">Home</a>
            {' / ' + path.replace('/', ' / ') if path else ''}
        </div>
        
        <div id="loading">Loading...</div>
        <div id="content" style="display:none;">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Size</th>
                        <th>Modified</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="fileList"></tbody>
            </table>
        </div>
    </div>
    
    <script>
        const base = '{base}';
        const currentPath = '{path}';
        
        function changeBase() {{
            const newBase = document.getElementById('baseSelect').value;
            window.location.href = `/files?base=${{newBase}}`;
        }}
        
        function refresh() {{
            loadFiles();
        }}
        
        function loadFiles() {{
            const path = currentPath;
            const baseDir = base;
            fetch(`/api/files?path=${{encodeURIComponent(path)}}&base=${{baseDir}}`)
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('content').style.display = 'block';
                    
                    const tbody = document.getElementById('fileList');
                    tbody.innerHTML = '';
                    
                    // Add parent directory link
                    if (data.parent !== null) {{
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td><a href="/files?path=${{encodeURIComponent(data.parent)}}&base=${{baseDir}}">..</a></td>
                            <td class="type-dir">Directory</td>
                            <td>-</td>
                            <td>-</td>
                            <td>-</td>
                        `;
                    }}
                    
                    // Add files and directories
                    if (data.items.length === 0) {{
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td colspan="5" style="text-align: center; color: #999; padding: 20px;">
                                📁 This directory is empty
                                <br><small>Switch to "paper_trading_outputs" to see bot data</small>
                            </td>
                        `;
                    }} else {{
                        data.items.forEach(item => {{
                            const row = tbody.insertRow();
                            const size = item.size ? formatSize(item.size) : '-';
                            const modified = new Date(item.modified).toLocaleString();
                            
                            if (item.type === 'directory') {{
                                row.innerHTML = `
                                    <td><a href="/files?path=${{encodeURIComponent(item.path)}}&base=${{baseDir}}">${{item.name}}/</a></td>
                                    <td class="type-dir">Directory</td>
                                    <td>-</td>
                                    <td>${{modified}}</td>
                                    <td>-</td>
                                `;
                            }} else {{
                                row.innerHTML = `
                                    <td>${{item.name}}</td>
                                    <td class="type-file">File</td>
                                    <td class="size">${{size}}</td>
                                    <td>${{modified}}</td>
                                    <td><a href="/api/files/download/${{encodeURIComponent(item.path)}}?base=${{baseDir}}">Download</a></td>
                                `;
                            }}
                        }});
                    }}
                    
                    // Update breadcrumb
                    updateBreadcrumb(data.path, baseDir);
                }})
                .catch(error => {{
                    document.getElementById('loading').innerHTML = 'Error: ' + error.message;
                }});
        }}
        
        function formatSize(bytes) {{
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
            if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
            return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
        }}
        
        function updateBreadcrumb(path, baseDir) {{
            const breadcrumb = document.getElementById('breadcrumb');
            let html = `<a href="/files?base=${{baseDir}}">Home</a>`;
            
            if (path) {{
                const parts = path.split('/').filter(p => p);
                let currentPath = '';
                parts.forEach((part, index) => {{
                    currentPath += (currentPath ? '/' : '') + part;
                    html += ` / <a href="/files?path=${{encodeURIComponent(currentPath)}}&base=${{baseDir}}">${{part}}</a>`;
                }});
            }}
            
            breadcrumb.innerHTML = html;
        }}
        
        // Load files on page load
        loadFiles();
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html)
    
    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        """Serve React frontend routes (SPA routing) - only for non-API routes"""
        # Don't interfere with API routes (they should be handled above)
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        
        # Don't interfere with file browser
        if path == "files" or path.startswith("files/"):
            raise HTTPException(status_code=404, detail="Use /files endpoint")
        
        # Check if it's a static file
        static_file = FRONTEND_BUILD_DIR / path
        if static_file.exists() and static_file.is_file():
            return FileResponse(str(static_file))
        
        # Otherwise serve index.html for SPA routing
        index_file = FRONTEND_BUILD_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        
        raise HTTPException(status_code=404, detail="Not found")



# Removed duplicate endpoints - use /api/bots/status and /api/logs/{log_type} instead



@app.get("/api/bots/{bot_version}/status")
async def get_bot_status(bot_version: str):
    """Get the status of a specific trading bot"""
    try:
        # Check if bot directory exists (indicates bot is configured)
        bot_dir = OUTPUTS_DIR / bot_version / "sheets_fallback"
        if bot_dir.exists():
            # Check if recent data exists (indicates bot is running)
            equity_file = bot_dir / "equity.csv"
            if equity_file.exists():
                # Get file modification time
                import os
                file_time = os.path.getmtime(str(equity_file))
                current_time = time.time()
                # If file was modified within last 5 minutes, consider bot "running"
                if current_time - file_time < 300:  # 5 minutes
                    return {"version": bot_version, "status": "running"}
                else:
                    return {"version": bot_version, "status": "stopped"}
            else:
                return {"version": bot_version, "status": "stopped"}
        else:
            return {"version": bot_version, "status": "not_configured"}
    except Exception as e:
        return {"version": bot_version, "status": "error", "error": str(e)}


# Removed duplicate /logs/{log_type}/{date} endpoint - use /api/logs/{log_type}?date=... instead


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





