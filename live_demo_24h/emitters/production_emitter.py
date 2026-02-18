"""
Production Log Emitter for MetaStackerBandit
Features: Log rotation, sampling, error handling, compression, retry logic
"""

import json
import os
import gzip
import time
import threading
import queue
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import pytz
from dataclasses import dataclass
from enum import Enum
import hashlib
import random

IST = pytz.timezone("Asia/Kolkata")


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class EmitterConfig:
    base_dir: str = "paper_trading_outputs/logs"
    max_file_size_mb: int = 100
    max_files: int = 10
    compression: bool = True
    sampling_rate: float = 1.0  # 1.0 = no sampling, 0.1 = 10% sampling
    retry_attempts: int = 3
    retry_delay: float = 1.0
    batch_size: int = 100
    flush_interval: float = 5.0  # seconds
    enable_async: bool = True


class ProductionLogEmitter:
    """Production-ready log emitter with rotation, sampling, and error handling"""

    def __init__(self, config: EmitterConfig):
        self.config = config
        self.logger = self._setup_logger()
        self._queues: Dict[str, queue.Queue] = {}
        self._writers: Dict[str, threading.Thread] = {}
        self._file_handles: Dict[str, Any] = {}
        self._file_sizes: Dict[str, int] = {}
        self._last_flush: Dict[str, float] = {}
        self._lock = threading.RLock()

        # Create base directory
        Path(self.config.base_dir).mkdir(parents=True, exist_ok=True)

        if self.config.enable_async:
            self._start_background_writers()

    def _setup_logger(self) -> logging.Logger:
        """Setup internal logger for emitter operations"""
        logger = logging.getLogger(f"ProductionLogEmitter_{id(self)}")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _start_background_writers(self):
        """Start background writer threads for async logging"""
        for log_type in [
            "market",
            "signals",
            "ensemble",
            "risk",
            "execution",
            "costs",
            "health",
            "repro",
            "order_intent",
            "feature_log",
            "calibration",
        ]:
            self._queues[log_type] = queue.Queue(maxsize=10000)
            self._writers[log_type] = threading.Thread(
                target=self._background_writer,
                args=(log_type,),
                daemon=True,
                name=f"Writer-{log_type}",
            )
            self._writers[log_type].start()

    def _background_writer(self, log_type: str):
        """Background writer thread for async logging"""
        while True:
            try:
                # Get batch of records
                records = []
                timeout = self.config.flush_interval

                # Try to get batch_size records or timeout
                for _ in range(self.config.batch_size):
                    try:
                        record = self._queues[log_type].get(timeout=timeout)
                        records.append(record)
                        timeout = 0.1  # Reduce timeout for subsequent records
                    except queue.Empty:
                        break

                if records:
                    self._write_batch(log_type, records)

            except Exception as e:
                self.logger.error(f"Background writer error for {log_type}: {e}")
                time.sleep(1)

    def _write_batch(self, log_type: str, records: List[Dict[str, Any]]):
        """Write batch of records to file"""
        try:
            file_path = self._get_file_path(log_type)

            # Check if file needs rotation
            if self._should_rotate_file(log_type, file_path):
                self._rotate_file(log_type, file_path)
                file_path = self._get_file_path(log_type)

            # Write records
            with self._lock:
                mode = "a" if os.path.exists(file_path) else "w"
                open_func = gzip.open if self.config.compression else open

                with open_func(file_path, mode, encoding="utf-8") as f:
                    for record in records:
                        f.write(json.dumps(record, separators=(",", ":")) + "\n")

                # Update file size
                self._file_sizes[log_type] = os.path.getsize(file_path)
                self._last_flush[log_type] = time.time()

        except Exception as e:
            self.logger.error(f"Error writing batch for {log_type}: {e}")
            # Retry individual records
            for record in records:
                self._write_single_with_retry(log_type, record)

    def _write_single_with_retry(self, log_type: str, record: Dict[str, Any]):
        """Write single record with retry logic"""
        for attempt in range(self.config.retry_attempts):
            try:
                file_path = self._get_file_path(log_type)

                if self._should_rotate_file(log_type, file_path):
                    self._rotate_file(log_type, file_path)
                    file_path = self._get_file_path(log_type)

                with self._lock:
                    mode = "a" if os.path.exists(file_path) else "w"
                    open_func = gzip.open if self.config.compression else open

                    with open_func(file_path, mode, encoding="utf-8") as f:
                        f.write(json.dumps(record, separators=(",", ":")) + "\n")

                    self._file_sizes[log_type] = os.path.getsize(file_path)
                    self._last_flush[log_type] = time.time()

                return  # Success

            except Exception as e:
                self.logger.warning(
                    f"Write attempt {attempt + 1} failed for {log_type}: {e}"
                )
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(
                        self.config.retry_delay * (2**attempt)
                    )  # Exponential backoff
                else:
                    self.logger.error(f"All retry attempts failed for {log_type}: {e}")
                    # Write to error log
                    self._write_error_log(log_type, record, str(e))

    def _write_error_log(self, log_type: str, record: Dict[str, Any], error: str):
        """Write failed records to error log"""
        try:
            error_dir = Path(self.config.base_dir) / "errors"
            error_dir.mkdir(exist_ok=True)

            error_file = error_dir / f"{log_type}_errors.jsonl"
            error_record = {
                "timestamp": datetime.now(IST).isoformat(),
                "log_type": log_type,
                "original_record": record,
                "error": error,
            }

            with open(error_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_record) + "\n")

        except Exception as e:
            self.logger.critical(f"Failed to write error log: {e}")

    def _get_file_path(self, log_type: str) -> str:
        """Get current file path for log type"""
        date_str = datetime.now(IST).strftime("%Y-%m-%d")
        log_dir = Path(self.config.base_dir) / log_type / f"date={date_str}"
        log_dir.mkdir(parents=True, exist_ok=True)

        ext = ".jsonl.gz" if self.config.compression else ".jsonl"
        return str(log_dir / f"{log_type}{ext}")

    def _should_rotate_file(self, log_type: str, file_path: str) -> bool:
        """Check if file should be rotated"""
        if not os.path.exists(file_path):
            return False

        # Size-based rotation
        file_size = os.path.getsize(file_path)
        max_size_bytes = self.config.max_file_size_mb * 1024 * 1024

        return file_size >= max_size_bytes

    def _rotate_file(self, log_type: str, file_path: str):
        """Rotate log file"""
        try:
            # Create rotated filename with timestamp
            timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
            base_path = Path(file_path)
            rotated_path = (
                base_path.parent / f"{base_path.stem}_{timestamp}{base_path.suffix}"
            )

            # Move current file to rotated name
            os.rename(file_path, str(rotated_path))

            # Clean up old files
            self._cleanup_old_files(log_type, base_path.parent)

            self.logger.info(f"Rotated {log_type} log file: {rotated_path}")

        except Exception as e:
            self.logger.error(f"Error rotating {log_type} log file: {e}")

    def _cleanup_old_files(self, log_type: str, log_dir: Path):
        """Clean up old log files"""
        try:
            pattern = f"{log_type}_*.jsonl*"
            files = list(log_dir.glob(pattern))
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Keep only max_files
            for old_file in files[self.config.max_files :]:
                old_file.unlink()
                self.logger.info(f"Cleaned up old log file: {old_file}")

        except Exception as e:
            self.logger.error(f"Error cleaning up old files for {log_type}: {e}")

    def _should_sample(self, log_type: str) -> bool:
        """Determine if record should be sampled"""
        if self.config.sampling_rate >= 1.0:
            return True
        return random.random() < self.config.sampling_rate

    def _add_metadata(self, record: Dict[str, Any], log_type: str) -> Dict[str, Any]:
        """Add metadata to record"""
        if "ts_ist" not in record:
            record["ts_ist"] = datetime.now(IST).isoformat()

        record["_emitter_metadata"] = {
            "log_type": log_type,
            "emitter_version": "1.0.0",
            "sampled": self._should_sample(log_type),
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        }

        return record

    def emit_market_data(self, record: Dict[str, Any]):
        """Emit market data log"""
        record = self._add_metadata(record, "market")
        if self.config.enable_async:
            self._queues["market"].put(record)
        else:
            self._write_single_with_retry("market", record)

    def emit_signals(self, record: Dict[str, Any]):
        """Emit signals log"""
        record = self._add_metadata(record, "signals")
        if self.config.enable_async:
            self._queues["signals"].put(record)
        else:
            self._write_single_with_retry("signals", record)

    def emit_ensemble(self, record: Dict[str, Any]):
        """Emit ensemble log"""
        record = self._add_metadata(record, "ensemble")
        if self.config.enable_async:
            self._queues["ensemble"].put(record)
        else:
            self._write_single_with_retry("ensemble", record)

    def emit_risk(self, record: Dict[str, Any]):
        """Emit risk log"""
        record = self._add_metadata(record, "risk")
        if self.config.enable_async:
            self._queues["risk"].put(record)
        else:
            self._write_single_with_retry("risk", record)

    def emit_execution(self, record: Dict[str, Any]):
        """Emit execution log"""
        record = self._add_metadata(record, "execution")
        if self.config.enable_async:
            self._queues["execution"].put(record)
        else:
            self._write_single_with_retry("execution", record)

    def emit_costs(self, record: Dict[str, Any]):
        """Emit costs log"""
        record = self._add_metadata(record, "costs")
        if self.config.enable_async:
            self._queues["costs"].put(record)
        else:
            self._write_single_with_retry("costs", record)

    def emit_health(self, record: Dict[str, Any]):
        """Emit health log"""
        record = self._add_metadata(record, "health")
        if self.config.enable_async:
            self._queues["health"].put(record)
        else:
            self._write_single_with_retry("health", record)

    def emit_repro(self, record: Dict[str, Any]):
        """Emit repro/config log"""
        record = self._add_metadata(record, "repro")
        if self.config.enable_async:
            self._queues["repro"].put(record)
        else:
            self._write_single_with_retry("repro", record)

    def emit_order_intent(self, record: Dict[str, Any]):
        """Emit order intent log"""
        record = self._add_metadata(record, "order_intent")
        if self.config.enable_async:
            self._queues["order_intent"].put(record)
        else:
            self._write_single_with_retry("order_intent", record)

    def emit_feature_log(self, record: Dict[str, Any]):
        """Emit feature log"""
        record = self._add_metadata(record, "feature_log")
        if self.config.enable_async:
            self._queues["feature_log"].put(record)
        else:
            self._write_single_with_retry("feature_log", record)

    def emit_calibration(self, record: Dict[str, Any]):
        """Emit calibration log"""
        record = self._add_metadata(record, "calibration")
        if self.config.enable_async:
            self._queues["calibration"].put(record)
        else:
            self._write_single_with_retry("calibration", record)

    def flush_all(self):
        """Flush all pending records"""
        if not self.config.enable_async:
            return

        for log_type in self._queues:
            # Wait for queue to empty
            while not self._queues[log_type].empty():
                time.sleep(0.1)

            # Force flush
            self._last_flush[log_type] = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get emitter statistics"""
        stats = {
            "config": {
                "base_dir": self.config.base_dir,
                "max_file_size_mb": self.config.max_file_size_mb,
                "max_files": self.config.max_files,
                "compression": self.config.compression,
                "sampling_rate": self.config.sampling_rate,
                "async_enabled": self.config.enable_async,
            },
            "queues": {},
            "files": {},
        }

        for log_type in self._queues:
            stats["queues"][log_type] = {
                "size": self._queues[log_type].qsize(),
                "maxsize": self._queues[log_type].maxsize,
            }

            file_path = self._get_file_path(log_type)
            if os.path.exists(file_path):
                stats["files"][log_type] = {
                    "path": file_path,
                    "size_mb": os.path.getsize(file_path) / (1024 * 1024),
                    "last_modified": datetime.fromtimestamp(
                        os.path.getmtime(file_path), IST
                    ).isoformat(),
                }

        return stats

    def close(self):
        """Close emitter and flush all records"""
        self.flush_all()

        # Stop background writers
        for writer in self._writers.values():
            writer.join(timeout=5)

        self.logger.info("ProductionLogEmitter closed")


# Global emitter instance
_emitter: Optional[ProductionLogEmitter] = None


def get_production_emitter(
    config: Optional[EmitterConfig] = None,
) -> ProductionLogEmitter:
    """Get global production emitter instance"""
    global _emitter
    if _emitter is None:
        if config is None:
            config = EmitterConfig()
        _emitter = ProductionLogEmitter(config)
    return _emitter


def close_production_emitter():
    """Close global production emitter"""
    global _emitter
    if _emitter is not None:
        _emitter.close()
        _emitter = None
