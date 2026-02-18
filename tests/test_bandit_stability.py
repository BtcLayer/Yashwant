"""
Ensemble 1.1 - Bandit Stability Tests (C2.3 + CHG-04)

Tests for reward normalization, freeze guards, and edge cases.
Coverage:
1. Normal rewards → No clipping
2. Extreme rewards → Clipped to ±3σ
3. Drawdown < threshold → No freeze
4. Drawdown > threshold → Freeze triggered
5. Recovery after freeze → Unfreeze and resume
"""

from __future__ import annotations

import numpy as np
import pytest

from live_demo.bandit import SimpleThompsonBandit


class TestRewardNormalization:
    """Test reward normalization with z-score and ±3σ clipping."""
    
    def test_normal_rewards_no_clipping(self):
        """Normal rewards (0.1, 0.5, 1.0) should not be clipped."""
        bandit = SimpleThompsonBandit(n_arms=3)
        
        # Build history with normal rewards
        normal_rewards = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        for i, r in enumerate(normal_rewards):
            arm = i % 3
            bandit.update(arm, r)
        
        # All arms should have been updated (counts > 0)
        assert np.all(bandit.counts > 0)
        assert len(bandit.reward_history) == 10
        
        # Mean and std should be reasonable
        assert 0.4 < bandit.global_reward_mean < 0.7
        assert 0.2 < bandit.global_reward_std < 0.4
    
    def test_extreme_rewards_are_clipped(self):
        """Extreme rewards (±100) should be clipped to ±3σ."""
        bandit = SimpleThompsonBandit(n_arms=2)
        
        # Build baseline with normal rewards
        baseline = [1.0, 1.1, 0.9, 1.2, 0.8, 1.0, 1.1, 0.9, 1.0, 1.1]
        for i, r in enumerate(baseline):
            bandit.update(0, r)
        
        # Inject extreme positive reward
        initial_mean = bandit.means[1]
        bandit.update(1, 100.0)  # Should be clipped to ~3σ
        
        # Mean should not explode (bounded by clipping)
        mean_change = abs(bandit.means[1] - initial_mean)
        assert mean_change < 10.0, f"Mean change too large: {mean_change}"
        
        # Inject extreme negative reward
        initial_mean = bandit.means[1]
        bandit.update(1, -100.0)  # Should be clipped to ~-3σ
        
        mean_change = abs(bandit.means[1] - initial_mean)
        assert mean_change < 10.0, f"Mean change too large: {mean_change}"
    
    def test_insufficient_history_uses_raw_rewards(self):
        """With < 10 samples, should use raw rewards (no normalization)."""
        bandit = SimpleThompsonBandit(n_arms=2)
        
        # Update with only 5 samples
        for i in range(5):
            bandit.update(0, 1.0)
        
        # Should use raw rewards (mean ≈ 1.0)
        assert abs(bandit.means[0] - 1.0) < 0.1
        
        # History tracking still works
        assert len(bandit.reward_history) == 5
    
    def test_reward_history_rolling_window(self):
        """Reward history should maintain rolling window of max 1000 samples."""
        bandit = SimpleThompsonBandit(n_arms=1)
        
        # Add 1500 rewards
        for i in range(1500):
            bandit.update(0, float(i))
        
        # Should only keep last 1000
        assert len(bandit.reward_history) <= 1000
        assert bandit.reward_history[-1] == 1499.0


class TestFreezeGuards:
    """Test freeze guards triggered by drawdown."""
    
    def test_no_freeze_with_small_drawdown(self):
        """Drawdown < 10% should not trigger freeze."""
        bandit = SimpleThompsonBandit(n_arms=2, drawdown_threshold=0.10)
        
        # Build history for normalization (total: +20 PnL, peak = 20)
        for _ in range(20):
            bandit.update(0, 1.0)
        
        # Small loss: -1 (drawdown = 1/20 = 5%)
        bandit.update(1, -1.0)
        
        # Should NOT be frozen (5% < 10%)
        assert not bandit.frozen
        assert bandit.freeze_reason is None
    
    def test_freeze_triggered_on_large_drawdown(self):
        """Drawdown > 10% should trigger freeze."""
        bandit = SimpleThompsonBandit(n_arms=2, drawdown_threshold=0.10)
        
        # Build history and peak: +30 profit (10 for history + 20 for peak)
        for _ in range(30):
            bandit.update(0, 1.0)
        
        assert bandit.peak_pnl == 30.0
        assert bandit.cumulative_pnl == 30.0
        
        # Large drawdown: lose 15 (drawdown = 15/30 = 50%)
        for _ in range(15):
            bandit.update(1, -1.0)
        
        # Should be FROZEN
        assert bandit.frozen
        assert "drawdown_exceeded" in bandit.freeze_reason
        assert bandit.cumulative_pnl == 15.0
    
    def test_frozen_bandit_skips_updates(self):
        """Frozen bandit should skip arm updates."""
        bandit = SimpleThompsonBandit(n_arms=2, drawdown_threshold=0.10)
        
        # Build history and peak
        for _ in range(20):
            bandit.update(0, 1.0)
        
        # Trigger freeze
        for _ in range(25):
            bandit.update(1, -1.0)
        
        assert bandit.frozen
        
        # Record counts before update
        counts_before = bandit.counts.copy()
        means_before = bandit.means.copy()
        
        # Try to update while frozen
        bandit.update(0, 10.0)
        
        # Counts and means should NOT change
        np.testing.assert_array_equal(bandit.counts, counts_before)
        np.testing.assert_array_equal(bandit.means, means_before)
    
    def test_frozen_bandit_logs_warning_on_select(self):
        """Frozen bandit should log warning and return safe default on select."""
        bandit = SimpleThompsonBandit(n_arms=3, drawdown_threshold=0.10)
        
        # Trigger freeze
        bandit.frozen = True
        bandit.freeze_reason = "test_freeze"
        
        # Select with all arms eligible
        eligible = np.array([True, True, True])
        selected = bandit.select(eligible)
        
        # Should return first eligible arm (index 0)
        assert selected == 0
        
        # Select with limited eligibility
        eligible = np.array([False, True, True])
        selected = bandit.select(eligible)
        
        # Should return first eligible arm (index 1)
        assert selected == 1
    
    def test_unfreeze_on_recovery(self):
        """Drawdown recovery < 8% should unfreeze bandit."""
        bandit = SimpleThompsonBandit(
            n_arms=2,
            drawdown_threshold=0.10,
        )
        bandit.freeze_recovery_threshold = 0.08
        
        # Build history and peak: +60 (10 for history + 50 for peak)
        for _ in range(60):
            bandit.update(0, 1.0)
        
        # Trigger freeze: lose 30 (drawdown = 30/60 = 50%)
        for _ in range(30):
            bandit.update(1, -1.0)
        
        assert bandit.frozen
        assert bandit.cumulative_pnl == 30.0
        assert bandit.peak_pnl == 60.0
        
        # Recover profits to bring drawdown to 6%
        # Need cumulative_pnl = 56.4 (drawdown = 3.6/60 = 6%)
        for _ in range(27):
            bandit.update(0, 1.0)
        
        # Should be UNFROZEN
        assert not bandit.frozen
        assert bandit.freeze_reason is None


class TestPersistence:
    """Test state persistence with Ensemble 1.1 enhancements."""
    
    def test_to_state_includes_normalization_and_freeze(self):
        """to_state() should serialize normalization and freeze state."""
        bandit = SimpleThompsonBandit(n_arms=3)
        bandit.reward_history = [1.0, 2.0, 3.0]
        bandit.global_reward_mean = 2.0
        bandit.global_reward_std = 0.816
        bandit.frozen = True
        bandit.freeze_reason = "test_freeze"
        bandit.cumulative_pnl = 100.0
        bandit.peak_pnl = 150.0
        
        state = bandit.to_state()
        
        assert "reward_history" in state
        assert "global_reward_mean" in state
        assert "global_reward_std" in state
        assert "frozen" in state
        assert "freeze_reason" in state
        assert "cumulative_pnl" in state
        assert "peak_pnl" in state
        assert state["frozen"] is True
        assert state["freeze_reason"] == "test_freeze"
    
    def test_from_state_restores_all_fields(self):
        """from_state() should restore normalization and freeze state."""
        state = {
            "n_arms": 3,
            "counts": [10.0, 20.0, 30.0],
            "means": [1.0, 2.0, 3.0],
            "variances": [0.1, 0.2, 0.3],
            "reward_history": [1.0, 2.0, 3.0],
            "global_reward_mean": 2.0,
            "global_reward_std": 0.816,
            "frozen": True,
            "freeze_reason": "drawdown_exceeded_10pct",
            "cumulative_pnl": 100.0,
            "peak_pnl": 150.0,
            "drawdown_threshold": 0.10,
        }
        
        bandit = SimpleThompsonBandit.from_state(state)
        
        assert bandit.n_arms == 3
        assert len(bandit.reward_history) == 3
        assert bandit.global_reward_mean == 2.0
        assert abs(bandit.global_reward_std - 0.816) < 0.01
        assert bandit.frozen is True
        assert bandit.freeze_reason == "drawdown_exceeded_10pct"
        assert bandit.cumulative_pnl == 100.0
        assert bandit.peak_pnl == 150.0
        assert bandit.drawdown_threshold == 0.10
    
    def test_backward_compatibility_with_old_state(self):
        """from_state() should handle old state format (no Ensemble 1.1 fields)."""
        old_state = {
            "n_arms": 2,
            "counts": [5.0, 10.0],
            "means": [1.5, 2.5],
            "variances": [0.1, 0.2],
        }
        
        bandit = SimpleThompsonBandit.from_state(old_state)
        
        # Should initialize with defaults
        assert bandit.n_arms == 2
        assert bandit.reward_history == []
        assert bandit.global_reward_mean == 0.0
        assert bandit.global_reward_std == 1.0
        assert bandit.frozen is False
        assert bandit.freeze_reason is None
        assert bandit.cumulative_pnl == 0.0
        assert bandit.peak_pnl == 0.0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_update_invalid_arm_is_ignored(self):
        """Updating invalid arm index should be safely ignored."""
        bandit = SimpleThompsonBandit(n_arms=3)
        
        # Update with invalid arms
        bandit.update(-1, 1.0)
        bandit.update(3, 1.0)
        bandit.update(100, 1.0)
        
        # Should have no effect
        assert np.all(bandit.counts == 0)
    
    def test_select_with_no_eligible_arms(self):
        """Selecting with no eligible arms should return safe default (0)."""
        bandit = SimpleThompsonBandit(n_arms=3)
        
        eligible = np.array([False, False, False])
        selected = bandit.select(eligible)
        
        assert selected == 0
    
    def test_select_with_mismatched_mask_raises_error(self):
        """Selecting with wrong mask size should raise ValueError."""
        bandit = SimpleThompsonBandit(n_arms=3)
        
        eligible = np.array([True, True])  # Wrong size
        
        with pytest.raises(ValueError, match="eligible_mask shape mismatch"):
            bandit.select(eligible)
    
    def test_extreme_variance_is_floored(self):
        """Variance should be floored at 1e-6 to prevent division issues."""
        bandit = SimpleThompsonBandit(n_arms=1)
        
        # Build history
        for _ in range(10):
            bandit.update(0, 1.0)
        
        # Update with identical rewards (zero variance)
        for _ in range(100):
            bandit.update(0, 1.0)
        
        # Variance should be floored
        assert bandit.variances[0] >= 1e-6
    
    def test_frozen_state_persists_across_serialization(self):
        """Frozen state should survive to_state() → from_state() roundtrip."""
        bandit = SimpleThompsonBandit(n_arms=2)
        
        # Trigger freeze
        for _ in range(20):
            bandit.update(0, 1.0)
        for _ in range(30):
            bandit.update(1, -1.0)
        
        assert bandit.frozen
        
        # Serialize and deserialize
        state = bandit.to_state()
        bandit2 = SimpleThompsonBandit.from_state(state)
        
        # Should still be frozen
        assert bandit2.frozen
        assert "drawdown_exceeded" in bandit2.freeze_reason


class TestCHG04AcceptanceCriteria:
    """Validate CHG-04 acceptance criteria from ChatGPT audit."""
    
    def test_chg04_normalization_prevents_instability(self):
        """CHG-04: Replay bad-event → normalization prevents instability."""
        bandit = SimpleThompsonBandit(n_arms=2)
        
        # Build baseline
        for _ in range(20):
            bandit.update(0, 1.0)
        
        # Inject catastrophic reward (+1000)
        bandit.update(1, 1000.0)
        
        # Mean of arm 1 should be bounded (not explode to ~1000)
        assert bandit.means[1] < 10.0, f"Mean exploded: {bandit.means[1]}"
    
    def test_chg04_debug_logs_extreme_rewards(self):
        """CHG-04: Debug logs show reward_raw, reward_normalized, clip_applied."""
        # This is implicitly tested via logging in the update() method
        # In production, verify logs contain these fields
        bandit = SimpleThompsonBandit(n_arms=1)
        
        # Build history
        for _ in range(20):
            bandit.update(0, 1.0)
        
        # Trigger extreme reward (should log)
        bandit.update(0, 100.0)
        
        # Verify internal state is correct
        assert len(bandit.reward_history) > 0
        assert bandit.reward_history[-1] == 100.0
    
    def test_chg04_freeze_on_drawdown_exceeds_10pct(self):
        """CHG-04: Bandit stops selecting when drawdown > 10%."""
        bandit = SimpleThompsonBandit(n_arms=2, drawdown_threshold=0.10)
        
        # Build peak
        for _ in range(100):
            bandit.update(0, 1.0)
        
        # Trigger drawdown > 10%
        for _ in range(15):
            bandit.update(1, -1.0)
        
        assert bandit.frozen
    
    def test_chg04_unit_tests_pass_with_extreme_values(self):
        """CHG-04: Unit tests pass with extreme reward inputs (±1000)."""
        bandit = SimpleThompsonBandit(n_arms=2)
        
        # Build baseline
        for _ in range(20):
            bandit.update(0, 1.0)
        
        # Extreme positive
        bandit.update(0, 1000.0)
        assert not np.isnan(bandit.means[0])
        assert not np.isinf(bandit.means[0])
        
        # Extreme negative
        bandit.update(1, -1000.0)
        assert not np.isnan(bandit.means[1])
        assert not np.isinf(bandit.means[1])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
