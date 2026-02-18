#!/usr/bin/env python3
"""Unit tests for cross-stream validation in validate_emitted_records.py"""

import pytest
import json
import tempfile
from pathlib import Path
from scripts.validate_emitted_records import (
    validate_logs,
    cross_stream_checks,
    LogSpec,
    LOG_SPECS,
)


class TestCrossStreamValidation:
    """Test suite for execution→costs cross-stream validation."""
    
    def test_detects_missing_costs(self):
        """Test that validator detects executed trades without costs."""
        exec_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "result": "FILLED",
                "ts": 1000000,
            }
        ]
        costs_records = []  # No costs!
        
        config = {
            'COST_MAX_FRAC': 0.25,
            'IMPACT_BPS_WARN': 500,
            'IMPACT_BPS_ERROR': 5000
        }
        
        issues = cross_stream_checks(exec_records, costs_records, config)
        
        # Should detect missing costs
        assert len(issues) > 0
        assert any("no costs record" in msg.lower() for level, msg in issues)
        assert any(level == "ERROR" for level, msg in issues)
    
    def test_detects_excessive_costs(self):
        """Test that validator detects cost_usd > COST_MAX_FRAC * notional."""
        exec_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "result": "FILLED",
                "ts": 1000000,
            }
        ]
        costs_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "ts": 1000000,
                "costs": {
                    "trade_notional": 1000.0,
                    "cost_usd": 300.0,  # 30% of notional (exceeds 25% threshold)
                }
            }
        ]
        
        config = {
            'COST_MAX_FRAC': 0.25,
            'IMPACT_BPS_WARN': 500,
            'IMPACT_BPS_ERROR': 5000
        }
        
        issues = cross_stream_checks(exec_records, costs_records, config)
        
        # Should detect excessive costs
        assert len(issues) > 0
        assert any("exceeds" in msg.lower() and "notional" in msg.lower() for level, msg in issues)
        assert any(level == "ERROR" for level, msg in issues)
    
    def test_detects_high_impact_bps(self):
        """Test that validator detects impact_bps > thresholds."""
        exec_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "result": "FILLED",
                "ts": 1000000,
            }
        ]
        costs_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "ts": 1000000,
                "costs": {
                    "trade_notional": 1000.0,
                    "cost_usd": 50.0,
                    "impact_bps": 6000,  # Exceeds ERROR threshold (5000)
                }
            }
        ]
        
        config = {
            'COST_MAX_FRAC': 0.25,
            'IMPACT_BPS_WARN': 500,
            'IMPACT_BPS_ERROR': 5000
        }
        
        issues = cross_stream_checks(exec_records, costs_records, config)
        
        # Should detect high impact
        assert len(issues) > 0
        assert any("impact_bps" in msg.lower() for level, msg in issues)
        assert any(level == "ERROR" for level, msg in issues)
    
    def test_warns_on_moderate_impact_bps(self):
        """Test that validator warns on impact_bps between WARN and ERROR thresholds."""
        exec_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "result": "FILLED",
                "ts": 1000000,
            }
        ]
        costs_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "ts": 1000000,
                "costs": {
                    "trade_notional": 1000.0,
                    "cost_usd": 50.0,
                    "impact_bps": 800,  # Between WARN (500) and ERROR (5000)
                }
            }
        ]
        
        config = {
            'COST_MAX_FRAC': 0.25,
            'IMPACT_BPS_WARN': 500,
            'IMPACT_BPS_ERROR': 5000
        }
        
        issues = cross_stream_checks(exec_records, costs_records, config)
        
        # Should warn (not error)
        assert len(issues) > 0
        assert any("impact_bps" in msg.lower() and level == "WARN" for level, msg in issues)
    
    def test_passes_valid_execution_with_costs(self):
        """Test that validator passes when execution has valid costs."""
        exec_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "result": "FILLED",
                "ts": 1000000,
            }
        ]
        costs_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "ts": 1000000,
                "costs": {
                    "trade_notional": 1000.0,
                    "cost_usd": 50.0,  # 5% of notional (OK)
                    "impact_bps": 100,  # Low impact (OK)
                }
            }
        ]
        
        config = {
            'COST_MAX_FRAC': 0.25,
            'IMPACT_BPS_WARN': 500,
            'IMPACT_BPS_ERROR': 5000
        }
        
        issues = cross_stream_checks(exec_records, costs_records, config)
        
        # Should pass (no errors)
        errors = [msg for level, msg in issues if level == "ERROR"]
        assert len(errors) == 0
    
    def test_ignores_non_executed_trades(self):
        """Test that validator ignores trades that weren't executed."""
        exec_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "result": "VETOED",  # Not executed
                "ts": 1000000,
            }
        ]
        costs_records = []  # No costs, but that's OK since not executed
        
        config = {
            'COST_MAX_FRAC': 0.25,
            'IMPACT_BPS_WARN': 500,
            'IMPACT_BPS_ERROR': 5000
        }
        
        issues = cross_stream_checks(exec_records, costs_records, config)
        
        # Should not complain about missing costs for vetoed trades
        assert len(issues) == 0
    
    def test_handles_multiple_executions(self):
        """Test validator with multiple executions and costs."""
        exec_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "result": "FILLED",
                "ts": 1000000,
            },
            {
                "run_id": "run_002",
                "bar_id": 101,
                "symbol": "BTCUSDT",
                "result": "FILLED",
                "ts": 1000100,
            },
        ]
        costs_records = [
            {
                "run_id": "run_001",
                "bar_id": 100,
                "symbol": "BTCUSDT",
                "ts": 1000000,
                "costs": {
                    "trade_notional": 1000.0,
                    "cost_usd": 50.0,
                    "impact_bps": 100,
                }
            },
            # Missing costs for run_002!
        ]
        
        config = {
            'COST_MAX_FRAC': 0.25,
            'IMPACT_BPS_WARN': 500,
            'IMPACT_BPS_ERROR': 5000
        }
        
        issues = cross_stream_checks(exec_records, costs_records, config)
        
        # Should detect missing costs for run_002
        assert len(issues) > 0
        assert any("run_002" in msg or "run_id=run_002" in msg for level, msg in issues)


class TestLogSpecValidation:
    """Test suite for LogSpec validation."""
    
    def test_log_specs_include_required_streams(self):
        """Test that LOG_SPECS includes signals, order_intent, and costs."""
        spec_names = [spec.name for spec in LOG_SPECS]
        
        assert "signals" in spec_names
        assert "order_intent" in spec_names
        assert "costs" in spec_names
    
    def test_order_intent_spec_has_required_fields(self):
        """Test that order_intent LogSpec has required fields."""
        order_intent_spec = next((s for s in LOG_SPECS if s.name == "order_intent"), None)
        
        assert order_intent_spec is not None
        assert "run_id" in order_intent_spec.required_fields
        assert "bar_id" in order_intent_spec.required_fields
        assert "symbol" in order_intent_spec.required_fields
        assert "strategy_id" in order_intent_spec.required_fields
        assert "schema_version" in order_intent_spec.required_fields
    
    def test_costs_spec_has_required_fields(self):
        """Test that costs LogSpec has required fields."""
        costs_spec = next((s for s in LOG_SPECS if s.name == "costs"), None)
        
        assert costs_spec is not None
        assert "run_id" in costs_spec.required_fields
        assert "bar_id" in costs_spec.required_fields
        assert "symbol" in costs_spec.required_fields
        assert "strategy_id" in costs_spec.required_fields
        assert "schema_version" in costs_spec.required_fields


class TestValidateLogsIntegration:
    """Integration tests for validate_logs function."""
    
    def test_validate_logs_with_valid_files(self):
        """Test validate_logs with valid log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_root = Path(tmpdir)
            
            # Create signals.jsonl
            signals_file = log_root / "signals.jsonl"
            with signals_file.open('w') as f:
                f.write(json.dumps({
                    "ts": 1000000,
                    "symbol": "BTCUSDT",
                    "features": {},
                    "model_out": {},
                    "decision": {},
                    "cohort": {},
                    "strategy_id": "test",
                    "schema_version": "1.0"
                }) + "\n")
            
            # Run validator
            issues = validate_logs(log_root, strict=False, max_records=5)
            
            # Should have some warnings (missing order_intent and costs)
            # but shouldn't crash
            assert isinstance(issues, int)
    
    def test_validate_logs_detects_missing_fields(self):
        """Test that validate_logs detects missing required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_root = Path(tmpdir)
            
            # Create signals.jsonl with missing fields
            signals_file = log_root / "signals.jsonl"
            with signals_file.open('w') as f:
                f.write(json.dumps({
                    "ts": 1000000,
                    "symbol": "BTCUSDT",
                    # Missing: features, model_out, decision, cohort, strategy_id, schema_version
                }) + "\n")
            
            # Run validator
            issues = validate_logs(log_root, strict=False, max_records=5)
            
            # Should detect missing fields
            assert issues > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
