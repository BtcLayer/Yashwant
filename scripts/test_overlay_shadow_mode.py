#!/usr/bin/env python3
"""
Quick test to demonstrate overlay shadow mode veto checking.

Tests:
1. Low confidence veto (confidence < threshold)
2. Timeframe conflict veto (5m vs 15m disagree)
3. No veto (normal case)
"""

import sys
from pathlib import Path

# Add live_demo to path
sys.path.insert(0, str(Path(__file__).parent.parent / "live_demo"))

from unified_overlay_system import (
    UnifiedOverlaySystem,
    OverlaySystemConfig,
    CombinedSignal,
    PerTimeframePrediction
)


def test_low_confidence_veto():
    """Test that low confidence triggers veto."""
    print("\n🧪 Test 1: Low Confidence Veto")
    print("-" * 50)
    
    config = OverlaySystemConfig(
        timeframes=['5m', '15m'],
        rollup_windows={'5m': 1, '15m': 3},
        weights={'5m': 0.6, '15m': 0.4},
        shadow_mode=True,
        veto_confidence_threshold=0.20,  # Threshold: 20%
        veto_on_timeframe_conflict=False,
        alignment_rules={
            'min_confidence': 0.10,
            'min_alpha': 0.05,
            'neutral_band': 0.03
        }
    )
    
    overlay = UnifiedOverlaySystem(config)
    
    # Create signal with low confidence (0.12 < 0.20)
    combined = CombinedSignal(
        asset='BTCUSDT',
        bar_id='2026-02-13T00:00:00',
        signals={
            '5m': PerTimeframePrediction(
                direction=1,  # Long
                alpha=0.08,
                confidence=0.12,  # LOW CONFIDENCE
                timestamp='2026-02-13T00:00:00'
            ),
            '15m': PerTimeframePrediction(
                direction=1,  # Long
                alpha=0.08,
                confidence=0.12,  # LOW CONFIDENCE
                timestamp='2026-02-13T00:00:00'
            )
        }
    )
    
    decision = overlay.generate_decision(combined)
    
    print(f"   Direction: {decision.direction}")
    print(f"   Confidence: {decision.confidence:.3f}")
    print(f"   Would veto: {decision.overlay_would_veto}")
    print(f"   Veto reason: {decision.overlay_veto_reason}")
    
    assert decision.overlay_would_veto == True, "Should veto low confidence"
    assert "low_overlay_confidence" in decision.overlay_veto_reason, "Reason should mention low confidence"
    print("   ✅ PASS - Low confidence correctly triggers veto")


def test_timeframe_conflict_veto():
    """Test that 5m vs 15m conflict triggers veto."""
    print("\n🧪 Test 2: Timeframe Conflict Veto")
    print("-" * 50)
    
    config = OverlaySystemConfig(
        timeframes=['5m', '15m'],
        rollup_windows={'5m': 1, '15m': 3},
        weights={'5m': 0.6, '15m': 0.4},
        shadow_mode=True,
        veto_confidence_threshold=0.15,
        veto_on_timeframe_conflict=True,  # Enable conflict checking
        alignment_rules={
            'min_confidence': 0.10,
            'min_alpha': 0.05,
            'neutral_band': 0.03
        }
    )
    
    overlay = UnifiedOverlaySystem(config)
    
    # Create signal with 5m LONG vs 15m SHORT conflict
    combined = CombinedSignal(
        asset='ETHUSDT',
        bar_id='2026-02-13T00:05:00',
        signals={
            '5m': PerTimeframePrediction(
                direction=1,  # LONG
                alpha=0.10,
                confidence=0.65,  # High confidence
                timestamp='2026-02-13T00:05:00'
            ),
            '15m': PerTimeframePrediction(
                direction=-1,  # SHORT (CONFLICT!)
                alpha=0.10,
                confidence=0.65,  # High confidence
                timestamp='2026-02-13T00:00:00'
            )
        }
    )
    
    decision = overlay.generate_decision(combined)
    
    print(f"   5m direction: {combined.signals['5m'].direction}")
    print(f"   15m direction: {combined.signals['15m'].direction}")
    print(f"   Overlay direction: {decision.direction}")
    print(f"   Would veto: {decision.overlay_would_veto}")
    print(f"   Veto reason: {decision.overlay_veto_reason}")
    
    assert decision.overlay_would_veto == True, "Should veto timeframe conflict"
    assert "timeframe_conflict" in decision.overlay_veto_reason, "Reason should mention conflict"
    print("   ✅ PASS - Timeframe conflict correctly triggers veto")


def test_no_veto():
    """Test that normal high-confidence aligned signal does NOT trigger veto."""
    print("\n🧪 Test 3: No Veto (Normal Case)")
    print("-" * 50)
    
    config = OverlaySystemConfig(
        timeframes=['5m', '15m'],
        rollup_windows={'5m': 1, '15m': 3},
        weights={'5m': 0.6, '15m': 0.4},
        shadow_mode=True,
        veto_confidence_threshold=0.15,
        veto_on_timeframe_conflict=True,
        alignment_rules={
            'min_confidence': 0.10,
            'min_alpha': 0.05,
            'neutral_band': 0.03
        }
    )
    
    overlay = UnifiedOverlaySystem(config)
    
    # Create strong, aligned signal
    combined = CombinedSignal(
        asset='SOLUSDT',
        bar_id='2026-02-13T00:10:00',
        signals={
            '5m': PerTimeframePrediction(
                direction=1,  # Long
                alpha=0.15,
                confidence=0.75,  # High confidence
                timestamp='2026-02-13T00:10:00'
            ),
            '15m': PerTimeframePrediction(
                direction=1,  # Long (ALIGNED)
                alpha=0.12,
                confidence=0.70,  # High confidence
                timestamp='2026-02-13T00:00:00'
            )
        }
    )
    
    decision = overlay.generate_decision(combined)
    
    print(f"   Direction: {decision.direction}")
    print(f"   Confidence: {decision.confidence:.3f}")
    print(f"   Would veto: {decision.overlay_would_veto}")
    print(f"   Veto reason: {decision.overlay_veto_reason}")
    
    assert decision.overlay_would_veto == False, "Should NOT veto strong aligned signal"
    assert decision.overlay_veto_reason is None, "Should have no veto reason"
    assert decision.direction != 0, "Should have non-neutral direction"
    print("   ✅ PASS - Strong aligned signal correctly passes through")


def main():
    print("\n" + "="*70)
    print("OVERLAY SHADOW MODE VETO CHECKING - VALIDATION TESTS")
    print("="*70)
    
    try:
        test_low_confidence_veto()
        test_timeframe_conflict_veto()
        test_no_veto()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED - Shadow mode implementation validated")
        print("="*70)
        print("\nNext steps:")
        print("1. Enable shadow_mode in all bot configs (✅ DONE)")
        print("2. Run bots to collect shadow mode data")
        print("3. Analyze with: python scripts/analyze_overlay_shadow.py")
        print("4. If cost savings > $0.50/trade, set shadow_mode=false")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
