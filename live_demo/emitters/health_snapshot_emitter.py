"""
Health Snapshot Emitter for periodic system health reporting
"""

import json
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class HealthSnapshot:
    """System health snapshot with key metrics"""
    equity_value: Optional[float] = None
    drawdown_current: Optional[float] = None
    daily_pnl: Optional[float] = None
    rolling_sharpe: Optional[float] = None
    trade_count: Optional[int] = None
    win_rate: Optional[float] = None
    timestamp: Optional[str] = None


class HealthSnapshotEmitter:
    """Emits periodic health snapshots to JSONL log"""
    
    def __init__(self, base_logs_dir: str = "paper_trading_outputs/health_snapshots", 
                 emit_interval_seconds: int = 300):
        """
        Args:
            base_logs_dir: Directory to write health snapshot logs
            emit_interval_seconds: Minimum seconds between emissions (default 5 minutes)
        """
        self.base_logs_dir = Path(base_logs_dir)
        self.base_logs_dir.mkdir(parents=True, exist_ok=True)
        self.emit_interval = emit_interval_seconds
        self.last_emit_time: Optional[float] = None
        
        # Date-partitioned log file
        self._current_date = None
        self._log_file_handle = None
    
    def _get_log_file(self):
        """Get current date-partitioned log file handle"""
        today = datetime.utcnow().strftime("%Y%m%d")
        
        if today != self._current_date:
            # Close old file if open
            if self._log_file_handle:
                self._log_file_handle.close()
            
            # Open new date-partitioned file
            self._current_date = today
            log_path = self.base_logs_dir / f"health_snapshot_{today}.jsonl"
            self._log_file_handle = open(log_path, 'a', encoding='utf-8')
        
        return self._log_file_handle
    
    def maybe_emit(self, snapshot: HealthSnapshot):
        """Emit health snapshot if enough time has passed since last emission"""
        now = datetime.utcnow().timestamp()
        
        # Check if we should emit
        if self.last_emit_time is not None:
            elapsed = now - self.last_emit_time
            if elapsed < self.emit_interval:
                return  # Too soon, skip
        
        # Update last emit time
        self.last_emit_time = now
        
        # Add timestamp
        if snapshot.timestamp is None:
            snapshot.timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Write to log
        try:
            log_file = self._get_log_file()
            log_entry = asdict(snapshot)
            log_file.write(json.dumps(log_entry) + '\n')
            log_file.flush()
        except Exception as e:
            # Silently fail to avoid breaking main loop
            print(f"Warning: Failed to emit health snapshot: {e}")
    
    def emit_now(self, snapshot: HealthSnapshot):
        """Force emit health snapshot immediately, bypassing interval check"""
        old_last_emit = self.last_emit_time
        self.last_emit_time = None  # Force emission
        try:
            self.maybe_emit(snapshot)
        finally:
            if self.last_emit_time is None:
                self.last_emit_time = old_last_emit
    
    def close(self):
        """Close log file handles"""
        if self._log_file_handle:
            self._log_file_handle.close()
            self._log_file_handle = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
