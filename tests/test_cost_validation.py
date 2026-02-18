"""Test cost validation bounds and semantic checks"""
import json
from pathlib import Path
import pytest
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validate_logs import LogValidator


def test_cost_bounds_valid(tmp_path: Path):
    """Valid cost record passes validation"""
    log_dir = tmp_path / "logs" / "costs" / "date=2026-02-09" / "asset=BTC"
    log_dir.mkdir(parents=True)
    
    record = {
        "ts": "2026-02-09T10:00:00+00:00",
        "symbol": "BTC",
        "asset": "BTC-PERP",
        "notional_usd": 10000,
        "fee_bps": 5.0,
        "impact_bps": 15.0,
        "cost_bps": 20.0,
        "total_cost_usd": 20.0,
        "cost_gt_notional": False,
        "is_forced": False,
        "is_synthetic": False
    }
    
    with open(log_dir / "costs.jsonl", "w") as f:
        f.write(json.dumps(record) + "\n")
    
    validator = LogValidator(str(tmp_path))
    success = validator.validate_all()
    assert success, f"Expected validation to pass, got {len(validator.errors)} errors: {validator.errors}"


def test_cost_bounds_fee_too_high(tmp_path: Path):
    """Fee > 50 bps should fail"""
    log_dir = tmp_path / "logs" / "costs" / "date=2026-02-09" / "asset=BTC"
    log_dir.mkdir(parents=True)
    
    record = {
        "ts": "2026-02-09T10:00:00+00:00",
        "symbol": "BTC",
        "asset": "BTC-PERP",
        "notional_usd": 10000,
        "fee_bps": 75.0,  # Too high!
        "impact_bps": 15.0,
        "cost_bps": 90.0,
        "total_cost_usd": 90.0,
        "cost_gt_notional": False,
        "is_forced": False,
        "is_synthetic": False
    }
    
    with open(log_dir / "costs.jsonl", "w") as f:
        f.write(json.dumps(record) + "\n")
    
    validator = LogValidator(str(tmp_path))
    success = validator.validate_all()
    assert not success, "Expected validation to catch high fee"
    assert any("fee_bps out of range" in err for err in validator.errors), \
        f"Expected fee_bps error, got: {validator.errors}"


def test_cost_bounds_impact_critical(tmp_path: Path):
    """Impact > 500 bps should fail"""
    log_dir = tmp_path / "logs" / "costs" / "date=2026-02-09" / "asset=BTC"
    log_dir.mkdir(parents=True)
    
    record = {
        "ts": "2026-02-09T10:00:00+00:00",
        "symbol": "BTC",
        "asset": "BTC-PERP",
        "notional_usd": 10000,
        "fee_bps": 5.0,
        "impact_bps": 600.0,  # Critical!
        "cost_bps": 605.0,
        "total_cost_usd": 605.0,
        "cost_gt_notional": False,
        "is_forced": False,
        "is_synthetic": False
    }
    
    with open(log_dir / "costs.jsonl", "w") as f:
        f.write(json.dumps(record) + "\n")
    
    validator = LogValidator(str(tmp_path))
    success = validator.validate_all()
    assert not success, "Expected validation to catch critical impact"
    assert any("impact_bps exceeds 500" in err for err in validator.errors), \
        f"Expected impact_bps error, got: {validator.errors}"


def test_signals_probability_sum_valid(tmp_path: Path):
    """Valid probability sum passes"""
    log_dir = tmp_path / "logs" / "signals" / "date=2026-02-09" / "asset=BTC"
    log_dir.mkdir(parents=True)
    
    record = {
        "ts": "2026-02-09T10:00:00+00:00",
        "symbol": "BTC",
        "asset": "BTC-PERP",
        "p_up": 0.4,
        "p_down": 0.3,
        "p_neutral": 0.3,
        "selected_arm": "model_meta",
        "final_action": "BUY",
        "is_forced": False,
        "is_synthetic": False
    }
    
    with open(log_dir / "signals.jsonl", "w") as f:
        f.write(json.dumps(record) + "\n")
    
    validator = LogValidator(str(tmp_path))
    success = validator.validate_all()
    assert success, f"Expected validation to pass, got {len(validator.errors)} errors: {validator.errors}"


def test_signals_probability_sum_invalid(tmp_path: Path):
    """Invalid probability sum should fail"""
    log_dir = tmp_path / "logs" / "signals" / "date=2026-02-09" / "asset=BTC"
    log_dir.mkdir(parents=True)
    
    record = {
        "ts": "2026-02-09T10:00:00+00:00",
        "symbol": "BTC",
        "asset": "BTC-PERP",
        "p_up": 0.5,
        "p_down": 0.5,
        "p_neutral": 0.5,  # Sum = 1.5, not 1.0!
        "selected_arm": "model_meta",
        "final_action": "BUY",
        "is_forced": False,
        "is_synthetic": False
    }
    
    with open(log_dir / "signals.jsonl", "w") as f:
        f.write(json.dumps(record) + "\n")
    
    validator = LogValidator(str(tmp_path))
    success = validator.validate_all()
    assert not success, "Expected validation to catch invalid probability sum"
    assert any("probability sum" in err for err in validator.errors), \
        f"Expected probability sum error, got: {validator.errors}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
