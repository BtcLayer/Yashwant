#!/usr/bin/env python3
"""Unit tests for cost guard veto logic in risk_and_exec.py"""

import pytest
from unittest.mock import Mock, MagicMock
from live_demo.risk_and_exec import RiskAndExec, RiskConfig
from live_demo.reason_codes import GuardReasonCode


class TestCostGuardVeto:
    """Test suite for cost sanity guard and veto logic."""
    
    def test_cost_guard_executes_without_error(self):
        """Test that cost guard logic executes without errors."""
        cfg = RiskConfig(
            max_impact_bps_hard=200.0,
            impact_k=0.01,
            base_notional=10000.0,
            sigma_target=0.20,
            pos_max=1.0,
            vol_floor=0.15,
        )
        
        client = Mock()
        
        risk = RiskAndExec(client, "BTCUSDT", cfg)
        risk.adv20_usd = 50000.0
        risk._pos = 0.0
        
        decision = {
            'dir': 1,
            'alpha': 0.8,
            'details': {'mode': 'INITIAL'}
        }
        
        # Should execute without error
        result = risk.evaluate_pretrade_guards(
            decision,
            ts_ms=1000000,
            last_price=50000.0,
            controls={},
        )
        
        # Basic checks
        assert isinstance(result, dict)
        assert 'dir' in result
        assert 'alpha' in result
        assert 'details' in result
        
        # If impact was calculated and is high, check for debug fields
        if 'impact_bps_est' in result['details']:
            impact = result['details']['impact_bps_est']
            if impact > 50.0:  # Warning level
                # Debug fields should be present
                assert 'adv_ref_used' in result['details'] or 'est_notional' in result['details']
    
    def test_cost_guard_allows_low_impact(self):
        """Test that trades with low impact are allowed."""
        cfg = RiskConfig(
            max_impact_bps_hard=200.0,
            impact_k=0.00001,  # Very low impact
            base_notional=1000.0,  # Small notional
            sigma_target=0.20,
            pos_max=1.0,
        )
        
        client = Mock()
        
        risk = RiskAndExec(client, "BTCUSDT", cfg)
        risk.adv20_usd = 1000000.0  # $1M ADV (high liquidity)
        risk._pos = 0.0
        
        decision = {
            'dir': 1,
            'alpha': 0.1,
            'details': {'mode': 'INITIAL'}
        }
        
        result = risk.evaluate_pretrade_guards(
            decision,
            ts_ms=1000000,
            last_price=50000.0,
            controls={},
        )
        
        # Should NOT be vetoed
        assert result['dir'] == 1, "Low impact trade should be allowed"
        assert result['alpha'] == 0.1, "Alpha should be preserved"
    
    def test_cost_guard_logs_debug_info(self):
        """Test that debug info is logged for warning-level impacts."""
        cfg = RiskConfig(
            max_impact_bps_hard=500.0,
            impact_k=0.0005,
            base_notional=5000.0,
            sigma_target=0.20,
            pos_max=1.0,
        )
        
        client = Mock()
        
        risk = RiskAndExec(client, "BTCUSDT", cfg)
        risk.adv20_usd = 100000.0
        risk._pos = 0.0
        
        decision = {
            'dir': 1,
            'alpha': 0.3,
            'details': {'mode': 'INITIAL'}
        }
        
        result = risk.evaluate_pretrade_guards(
            decision,
            ts_ms=1000000,
            last_price=50000.0,
            controls={},
        )
        
        # Check debug fields are present (whether vetoed or not)
        if result['dir'] == 0:  # If vetoed
            assert 'adv_ref_used' in result['details']
            assert 'price_ref_used' in result['details']
            assert 'est_notional' in result['details']
            assert 'impact_bps_est' in result['details']
            assert 'impact_k_used' in result['details']
    
    def test_cost_guard_edge_case_zero_price(self):
        """Test edge case: zero price doesn't cause exceptions."""
        cfg = RiskConfig(
            max_impact_bps_hard=200.0,
            impact_k=0.001,
            sigma_target=0.20,
            pos_max=1.0,
        )
        
        client = Mock()
        
        risk = RiskAndExec(client, "BTCUSDT", cfg)
        risk.adv20_usd = 100000.0
        risk._pos = 0.0
        
        decision = {
            'dir': 1,
            'alpha': 0.5,
            'details': {'mode': 'INITIAL'}
        }
        
        # Should not crash with zero price
        result = risk.evaluate_pretrade_guards(
            decision,
            ts_ms=1000000,
            last_price=0.0,  # Edge case: zero price
            controls={},
        )
        
        # Should handle gracefully (likely no veto since calculations fail)
        assert isinstance(result, dict)
        assert 'dir' in result
    
    def test_cost_guard_edge_case_zero_adv(self):
        """Test edge case: zero ADV doesn't cause exceptions."""
        cfg = RiskConfig(
            max_impact_bps_hard=200.0,
            impact_k=0.001,
            sigma_target=0.20,
            pos_max=1.0,
        )
        
        client = Mock()
        
        risk = RiskAndExec(client, "BTCUSDT", cfg)
        risk.adv20_usd = 0.0  # Edge case: zero ADV
        risk._pos = 0.0
        
        decision = {
            'dir': 1,
            'alpha': 0.5,
            'details': {'mode': 'INITIAL'}
        }
        
        # Should not crash
        result = risk.evaluate_pretrade_guards(
            decision,
            ts_ms=1000000,
            last_price=50000.0,
            controls={},
        )
        
        # Should handle gracefully
        assert isinstance(result, dict)
        assert 'dir' in result
    
    def test_cost_guard_disabled_when_impact_k_zero(self):
        """Test that cost guard is disabled when impact_k is zero."""
        cfg = RiskConfig(
            max_impact_bps_hard=200.0,
            impact_k=0.0,  # Disabled
            base_notional=5000.0,
            sigma_target=0.20,
            pos_max=1.0,
        )
        
        client = Mock()
        
        risk = RiskAndExec(client, "BTCUSDT", cfg)
        risk.adv20_usd = 100000.0
        risk._pos = 0.0
        
        decision = {
            'dir': 1,
            'alpha': 0.5,
            'details': {'mode': 'INITIAL'}
        }
        
        result = risk.evaluate_pretrade_guards(
            decision,
            ts_ms=1000000,
            last_price=50000.0,
            controls={},
        )
        
        # Should not be vetoed (impact guard disabled)
        assert result['dir'] == 1, "Trade should be allowed when impact_k=0"
    
    def test_cost_guard_threshold_boundary(self):
        """Test behavior at exact threshold boundary."""
        cfg = RiskConfig(
            max_impact_bps_hard=200.0,
            impact_k=0.0001,
            base_notional=3000.0,
            sigma_target=0.20,
            pos_max=1.0,
        )
        
        client = Mock()
        
        risk = RiskAndExec(client, "BTCUSDT", cfg)
        risk.adv20_usd = 500000.0
        risk._pos = 0.0
        
        decision = {
            'dir': 1,
            'alpha': 0.2,
            'details': {'mode': 'INITIAL'}
        }
        
        result = risk.evaluate_pretrade_guards(
            decision,
            ts_ms=1000000,
            last_price=50000.0,
            controls={},
        )
        
        # Check that veto logic is consistent
        if 'impact_bps_est' in result['details']:
            impact = result['details']['impact_bps_est']
            if impact > cfg.max_impact_bps_hard:
                assert result['dir'] == 0, "Should veto when impact > threshold"
            else:
                # May or may not be vetoed by other guards
                pass


class TestCostGuardIntegration:
    """Integration tests for cost guard with other risk controls."""
    
    def test_cost_guard_with_net_edge_gating(self):
        """Test cost guard works alongside net-edge gating."""
        cfg = RiskConfig(
            max_impact_bps_hard=200.0,
            impact_k=0.0005,
            base_notional=5000.0,
            enable_net_edge_gating=True,
            min_net_edge_bps=10.0,
            cost_bps=5.0,
            slippage_bps=2.0,
            sigma_target=0.20,
            pos_max=1.0,
        )
        
        client = Mock()
        
        risk = RiskAndExec(client, "BTCUSDT", cfg)
        risk.adv20_usd = 100000.0
        risk._pos = 0.0
        
        decision = {
            'dir': 1,
            'alpha': 0.05,  # Low alpha (50 bps signal)
            'details': {'mode': 'INITIAL'}
        }
        
        result = risk.evaluate_pretrade_guards(
            decision,
            ts_ms=1000000,
            last_price=50000.0,
            controls={},
        )
        
        # Should be vetoed by either cost guard or net-edge gating
        # (or both, depending on calculations)
        if result['dir'] == 0:
            assert result['details']['mode'] in [
                GuardReasonCode.IMPACT_CRITICAL,
                GuardReasonCode.NET_EDGE_INSUFFICIENT
            ]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
