#!/usr/bin/env python3
"""
TASK-5: CI Log Validation Script

Validates that all logs follow the canonical schema and path pattern:
  logs/{stream}/date=YYYY-MM-DD/asset={symbol}/{stream}.jsonl

Usage:
  python scripts/validate_logs.py [--root paper_trading_outputs/5m]
  
Exit codes:
  0 - All validations passed
  1 - Validation failures found
"""

import os
import sys
import json
import glob
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import re


# Canonical log streams and their required fields
STREAM_SCHEMAS = {
    "signals": ["ts", "symbol", "asset"],
    "execution": ["ts", "asset", "side"],
    "execution_log": ["ts", "asset", "side", "fill_px", "fill_qty"],
    "costs": ["ts", "symbol", "asset"],
    "costs_log": ["ts", "asset", "trade_notional", "fee_bps"],
    "health": ["ts", "symbol"],
    "ensemble_log": ["asset", "pred_stack_bps"],
    "pnl_equity_log": ["asset", "equity_value"],
    "calibration_log": ["asset", "pred_cal_bps"],
    "sizing_risk_log": ["asset", "raw_score_bps"],
    "kpi_scorecard": ["asset", "event"],
    "market_ingest_log": ["asset", "bar_id"],
    "order_intent": ["ts", "symbol"],
    "overlay_status": ["asset", "confidence"],
    "alerts": ["asset"],
    "hyperliquid_fills": ["asset", "coin"],
    "repro": ["ts", "symbol"],
    "feature_log": ["asset"],
    "snapshot_health": [],  # Informational only, no required fields
}


class LogValidator:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats = {
            "total_files": 0,
            "valid_files": 0,
            "invalid_files": 0,
            "deprecated_paths": 0,
            "total_records": 0,
            "invalid_records": 0,
        }

    def validate_all(self) -> bool:
        """Run all validations. Returns True if all pass."""
        print(f"[*] Validating logs in: {self.root_dir}")
        print("=" * 70)
        
        # Check if logs directory exists
        logs_dir = self.root_dir / "logs"
        if not logs_dir.exists():
            self.errors.append(f"Logs directory not found: {logs_dir}")
            return False
        
        # Find all JSONL files
        jsonl_files = list(logs_dir.rglob("*.jsonl"))
        self.stats["total_files"] = len(jsonl_files)
        
        print(f"\n[INFO] Found {len(jsonl_files)} log files")
        
        # Validate each file
        for file_path in jsonl_files:
            self._validate_file(file_path)
        
        # Check for deprecated paths
        self._check_deprecated_paths()
        
        # Print results
        self._print_results()
        
        return len(self.errors) == 0

    def _validate_file(self, file_path: Path):
        """Validate a single log file."""
        rel_path = file_path.relative_to(self.root_dir)
        
        # Check path pattern
        path_valid = self._validate_path_pattern(rel_path)
        
        # Extract stream name from path
        stream_name = self._extract_stream_name(rel_path)
        
        if not stream_name:
            self.errors.append(f"Cannot determine stream name from path: {rel_path}")
            self.stats["invalid_files"] += 1
            return
        
        # Validate file contents
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    self.stats["total_records"] += 1
                    
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Validate JSON
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        self.errors.append(
                            f"{rel_path}:{line_num} - Invalid JSON: {e}"
                        )
                        self.stats["invalid_records"] += 1
                        continue
                    
                    # Validate schema
                    self._validate_record_schema(record, stream_name, rel_path, line_num)
            
            if path_valid:
                self.stats["valid_files"] += 1
            else:
                self.stats["invalid_files"] += 1
                
        except Exception as e:
            self.errors.append(f"Error reading {rel_path}: {e}")
            self.stats["invalid_files"] += 1

    def _validate_path_pattern(self, rel_path: Path) -> bool:
        """
        Validate that path follows canonical pattern:
        logs/{stream}/date=YYYY-MM-DD/asset={symbol}/{stream}.jsonl
        """
        parts = rel_path.parts
        
        # Should be: logs, {stream}, date=..., asset=..., {stream}.jsonl
        if len(parts) < 5:
            self.errors.append(
                f"Invalid path structure (too few parts): {rel_path}\n"
                f"  Expected: logs/{{stream}}/date=YYYY-MM-DD/asset={{symbol}}/{{stream}}.jsonl"
            )
            return False
        
        # Check logs prefix
        if parts[0] != "logs":
            self.errors.append(f"Path should start with 'logs/': {rel_path}")
            return False
        
        # Check date partition
        date_part = None
        for part in parts:
            if part.startswith("date="):
                date_part = part
                break
        
        if not date_part:
            self.errors.append(f"Missing date partition (date=YYYY-MM-DD): {rel_path}")
            return False
        
        # Validate date format
        date_str = date_part.replace("date=", "")
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            self.errors.append(
                f"Invalid date format in {rel_path}: {date_part}\n"
                f"  Expected: date=YYYY-MM-DD"
            )
            return False
        
        # Check asset partition
        asset_part = None
        for part in parts:
            if part.startswith("asset="):
                asset_part = part
                break
        
        if not asset_part:
            self.warnings.append(f"Missing asset partition (asset={{symbol}}): {rel_path}")
            return False
        
        return True

    def _extract_stream_name(self, rel_path: Path) -> str:
        """Extract stream name from path."""
        # Stream name is typically the second part: logs/{stream}/...
        parts = rel_path.parts
        if len(parts) >= 2:
            return parts[1]
        return ""

    def _validate_record_schema(
        self, record: Dict[str, Any], stream_name: str, file_path: Path, line_num: int
    ):
        """Validate that a record has required fields for its stream."""
        # Get required fields for this stream
        required_fields = STREAM_SCHEMAS.get(stream_name, [])
        
        if not required_fields:
            # Unknown stream - just warn
            if stream_name not in ["snapshot_health", "default"]:
                self.warnings.append(
                    f"Unknown stream type: {stream_name} (in {file_path})"
                )
            return
        
        # Check for required fields
        missing_fields = []
        for field in required_fields:
            if field not in record:
                missing_fields.append(field)
        
        if missing_fields:
            self.errors.append(
                f"{file_path}:{line_num} - Missing required fields: {missing_fields}"
            )
            self.stats["invalid_records"] += 1

    def _check_deprecated_paths(self):
        """Check for logs in deprecated locations."""
        deprecated_patterns = [
            "logs/default/**/*.jsonl",  # Old default namespace
            "logs/*/[!date=]*/*.jsonl",  # Non-partitioned logs
        ]
        
        for pattern in deprecated_patterns:
            full_pattern = str(self.root_dir / pattern)
            deprecated_files = glob.glob(full_pattern, recursive=True)
            
            for file_path in deprecated_files:
                rel_path = Path(file_path).relative_to(self.root_dir)
                
                # Skip if it's actually in a valid partitioned path
                if "date=" in str(rel_path) and "asset=" in str(rel_path):
                    continue
                
                self.warnings.append(
                    f"Deprecated path (non-partitioned): {rel_path}\n"
                    f"  Should be: logs/{{stream}}/date=YYYY-MM-DD/asset={{symbol}}/{{stream}}.jsonl"
                )
                self.stats["deprecated_paths"] += 1

    def _print_results(self):
        """Print validation results."""
        print("\n" + "=" * 70)
        print("[RESULTS] VALIDATION RESULTS")
        print("=" * 70)
        
        print(f"\n[FILES]:")
        print(f"  Total:       {self.stats['total_files']}")
        print(f"  Valid:       {self.stats['valid_files']}")
        print(f"  Invalid:     {self.stats['invalid_files']}")
        print(f"  Deprecated:  {self.stats['deprecated_paths']}")
        
        print(f"\n[RECORDS]:")
        print(f"  Total:       {self.stats['total_records']}")
        print(f"  Invalid:     {self.stats['invalid_records']}")
        
        if self.warnings:
            print(f"\n[WARNING] WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:10]:  # Show first 10
                print(f"  - {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")
        
        if self.errors:
            print(f"\n[ERROR] ERRORS ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")
        
        print("\n" + "=" * 70)
        
        if len(self.errors) == 0:
            print("[PASS] ALL VALIDATIONS PASSED")
        else:
            print("[FAIL] VALIDATION FAILED")
        
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Validate log files follow canonical schema and path pattern"
    )
    parser.add_argument(
        "--root",
        default="paper_trading_outputs/5m",
        help="Root directory to validate (default: paper_trading_outputs/5m)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    
    args = parser.parse_args()
    
    # Validate
    validator = LogValidator(args.root)
    success = validator.validate_all()
    
    # Exit with appropriate code
    if not success:
        sys.exit(1)
    
    if args.strict and validator.warnings:
        print("\n[WARNING] Strict mode: Warnings treated as errors")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
