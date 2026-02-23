"""
Test script for Edge Gating (Ensemble 1.1 B2.3)

This script validates the compute_edge_after_costs function 
and demonstrates example outputs for various scenarios.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from live_demo.decision import compute_edge_after_costs


def test_edge_gating():
    """Test edge gating with various scenarios"""
    
    print("=" * 80)
    print("EDGE GATING TESTS - Ensemble 1.1 B2.3")
    print("=" * 80)
    print()
    
    # Test 1: Strong bullish signal with edge > costs
    print("Test 1: Strong bullish signal (p_up=0.60, p_down=0.05, p_neutral=0.35)")
    print("-" * 80)
    model_out = {
        'p_up': 0.60,
        'p_down': 0.05,
        'p_neutral': 0.35,
        's_model': 0.55
    }
    result = compute_edge_after_costs(model_out, cost_bps=5.0, expected_move_bps=50.0)
    print(f"  Expected return (LONG): {result['expected_return_bps']:.2f} bps")
    print(f"  Transaction costs:      {result['cost_bps']:.2f} bps")
    print(f"  Edge after costs:       {result['edge_after_costs_bps']:.2f} bps")
    print(f"  Recommended direction:  {result['direction']} (1=LONG, -1=SHORT, 0=NEUTRAL)")
    print(f"  Should trade:           {result['should_trade']}")
    assert result['should_trade'] == True, "Strong bullish signal should pass edge gate"
    assert result['direction'] == 1, "Should recommend LONG"
    print("  ✅ PASS: Trade allowed (positive edge)")
    print()
    
    # Test 2: Weak bullish signal with edge < costs
    print("Test 2: Weak bullish signal (p_up=0.45, p_down=0.40, p_neutral=0.15)")
    print("-" * 80)
    model_out = {
        'p_up': 0.45,
        'p_down': 0.40,
        'p_neutral': 0.15,
        's_model': 0.05
    }
    result = compute_edge_after_costs(model_out, cost_bps=5.0, expected_move_bps=50.0)
    print(f"  Expected return (LONG): {result['expected_return_bps']:.2f} bps")
    print(f"  Transaction costs:      {result['cost_bps']:.2f} bps")
    print(f"  Edge after costs:       {result['edge_after_costs_bps']:.2f} bps")
    print(f"  Recommended direction:  {result['direction']} (1=LONG, -1=SHORT, 0=NEUTRAL)")
    print(f"  Should trade:           {result['should_trade']}")
    assert result['should_trade'] == False, "Weak signal should fail edge gate"
    print("  ✅ PASS: Trade blocked (negative edge)")
    print()
    
    # Test 3: Strong bearish signal with edge > costs
    print("Test 3: Strong bearish signal (p_up=0.10, p_down=0.65, p_neutral=0.25)")
    print("-" * 80)
    model_out = {
        'p_up': 0.10,
        'p_down': 0.65,
        'p_neutral': 0.25,
        's_model': -0.55
    }
    result = compute_edge_after_costs(model_out, cost_bps=5.0, expected_move_bps=50.0)
    print(f"  Expected return (SHORT): {result['expected_return_bps']:.2f} bps")
    print(f"  Transaction costs:       {result['cost_bps']:.2f} bps")
    print(f"  Edge after costs:        {result['edge_after_costs_bps']:.2f} bps")
    print(f"  Recommended direction:   {result['direction']} (1=LONG, -1=SHORT, 0=NEUTRAL)")
    print(f"  Should trade:            {result['should_trade']}")
    assert result['should_trade'] == True, "Strong bearish signal should pass edge gate"
    assert result['direction'] == -1, "Should recommend SHORT"
    print("  ✅ PASS: Trade allowed (positive edge)")
    print()
    
    # Test 4: Neutral signal
    print("Test 4: Neutral signal (p_up=0.30, p_down=0.30, p_neutral=0.40)")
    print("-" * 80)
    model_out = {
        'p_up': 0.30,
        'p_down': 0.30,
        'p_neutral': 0.40,
        's_model': 0.0
    }
    result = compute_edge_after_costs(model_out, cost_bps=5.0, expected_move_bps=50.0)
    print(f"  Expected return:        {result['expected_return_bps']:.2f} bps")
    print(f"  Transaction costs:      {result['cost_bps']:.2f} bps")
    print(f"  Edge after costs:       {result['edge_after_costs_bps']:.2f} bps")
    print(f"  Recommended direction:  {result['direction']} (1=LONG, -1=SHORT, 0=NEUTRAL)")
    print(f"  Should trade:           {result['should_trade']}")
    assert result['should_trade'] == False, "Neutral signal should fail edge gate"
    assert result['direction'] == 0, "Should recommend NEUTRAL"
    print("  ✅ PASS: Trade blocked (no edge)")
    print()
    
    # Test 5: High costs scenario
    print("Test 5: Moderate signal with high costs (cost_bps=20.0)")
    print("-" * 80)
    model_out = {
        'p_up': 0.55,
        'p_down': 0.25,
        'p_neutral': 0.20,
        's_model': 0.30
    }
    result = compute_edge_after_costs(model_out, cost_bps=20.0, expected_move_bps=50.0)
    print(f"  Expected return (LONG): {result['expected_return_bps']:.2f} bps")
    print(f"  Transaction costs:      {result['cost_bps']:.2f} bps")
    print(f"  Edge after costs:       {result['edge_after_costs_bps']:.2f} bps")
    print(f"  Recommended direction:  {result['direction']} (1=LONG, -1=SHORT, 0=NEUTRAL)")
    print(f"  Should trade:           {result['should_trade']}")
    assert result['should_trade'] == False, "Signal should fail edge gate when costs exceed returns"
    print("  ✅ PASS: Trade blocked (costs exceed expected returns)")
    print()
    
    # Test 6: Large expected move
    print("Test 6: Stronger signal with large expected move (expected_move_bps=100.0)")
    print("-" * 80)
    model_out = {
        'p_up': 0.48,
        'p_down': 0.40,
        'p_neutral': 0.12,
        's_model': 0.08
    }
    result = compute_edge_after_costs(model_out, cost_bps=5.0, expected_move_bps=100.0)
    print(f"  Expected return (LONG): {result['expected_return_bps']:.2f} bps")
    print(f"  Transaction costs:      {result['cost_bps']:.2f} bps")
    print(f"  Edge after costs:       {result['edge_after_costs_bps']:.2f} bps")
    print(f"  Recommended direction:  {result['direction']} (1=LONG, -1=SHORT, 0=NEUTRAL)")
    print(f"  Should trade:           {result['should_trade']}")
    assert result['should_trade'] == True, "Large expected move should make signal profitable"
    print("  ✅ PASS: Trade allowed (large move compensates for weak signal)")
    print()
    
    print("=" * 80)
    print("ALL TESTS PASSED ✅")
    print("=" * 80)
    print()
    print("Summary:")
    print("  - Edge gating correctly filters unprofitable trades")
    print("  - Both bullish and bearish edges are computed correctly")
    print("  - Transaction costs are properly subtracted from expected returns")
    print("  - Function handles neutral, high-cost, and large-move scenarios")
    print()


def test_integration_example():
    """Show example of how edge gating integrates with decision flow"""
    
    print()
    print("=" * 80)
    print("INTEGRATION EXAMPLE")
    print("=" * 80)
    print()
    print("Example workflow with edge gating:")
    print()
    print("  1. Model outputs probabilities: p_up=0.52, p_down=0.28, p_neutral=0.20")
    print("  2. Overlay system generates decision: direction=1 (LONG), alpha=0.7")
    print("  3. Edge gating evaluates trade:")
    print()
    
    model_out = {
        'p_up': 0.52,
        'p_down': 0.28,
        'p_neutral': 0.20,
        's_model': 0.24
    }
    result = compute_edge_after_costs(model_out, cost_bps=5.0, expected_move_bps=50.0)
    
    print(f"     Expected return: {result['expected_return_bps']:.2f} bps")
    print(f"                      = 0.52 * 50 - 0.28 * 50")
    print(f"                      = 26.00 - 14.00")
    print(f"                      = 12.00 bps")
    print()
    print(f"     Transaction cost: {result['cost_bps']:.2f} bps")
    print()
    print(f"     Edge after costs: {result['edge_after_costs_bps']:.2f} bps")
    print(f"                       = 12.00 - 5.00")
    print(f"                       = 7.00 bps")
    print()
    
    if result['should_trade']:
        print("  4. ✅ Edge is positive → Trade executes")
        print(f"     Final decision: LONG with alpha={0.7}")
    else:
        print("  4. ❌ Edge is negative → Trade vetoed")
        print("     Final decision: NEUTRAL (direction=0, alpha=0)")
    
    print()
    print("Edge metrics added to decision['details']['edge']:")
    print(f"  - edge_after_costs_bps: {result['edge_after_costs_bps']:.2f}")
    print(f"  - expected_return_bps:  {result['expected_return_bps']:.2f}")
    print(f"  - cost_bps:             {result['cost_bps']:.2f}")
    print(f"  - should_trade:         {result['should_trade']}")
    print()
    print("These metrics are logged to paper_trading_outputs/logs/signals/*.jsonl")
    print()


if __name__ == '__main__':
    test_edge_gating()
    test_integration_example()
    print("Edge gating implementation validated! ✅")
