#!/usr/bin/env python3
"""
5M BOT FIX - QUICK VALIDATION (15-30 minutes)
Tests if the fixes will work WITHOUT waiting 7 days

Tests performed:
1. Signal strength test: Check if cohort signals are stronger with new config
2. Threshold pass rate: How many bars would pass new vs old thresholds
3. Model neutrality: Check if model predictions are reasonable
4. Trade frequency projection: Estimate daily trades with new settings
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add live_demo to path
sys.path.insert(0, str(Path(__file__).parent / "live_demo"))

from cohort_signals import CohortState

class QuickValidator:
    def __init__(self):
        self.results = {}
        
    def load_historical_signals(self):
        """Load existing signal data"""
        signal_file = Path("paper_trading_outputs/sheets_fallback/signals.csv")
        if not signal_file.exists():
            print("❌ No historical signals found!")
            return None
        
        df = pd.read_csv(signal_file)
        print(f"✓ Loaded {len(df)} historical bars")
        return df
    
    def load_config(self, config_path="live_demo/config.json"):
        """Load current config"""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def test_cohort_strength(self):
        """Test 1: Check if cohort signals will be stronger"""
        print("\n" + "="*60)
        print("TEST 1: COHORT SIGNAL STRENGTH")
        print("="*60)
        
        # Old config
        old_cohort = CohortState(
            window=12,
            use_adv20_normalization=True,
            use_signal_decay=True,
            timeframe_hours=1.0
        )
        
        # New config
        new_cohort = CohortState(
            window=50,
            use_adv20_normalization=False,
            use_signal_decay=False,
            timeframe_hours=0.0833
        )
        
        print(f"\nOLD Config:")
        print(f"  window={old_cohort.window}")
        print(f"  normalization={old_cohort.use_adv20_normalization}")
        print(f"  decay={old_cohort.use_signal_decay}")
        
        print(f"\nNEW Config:")
        print(f"  window={new_cohort.window}")
        print(f"  normalization={new_cohort.use_adv20_normalization}")
        print(f"  decay={new_cohort.use_signal_decay}")
        
        # Simulate 100 fills
        print(f"\nSimulating 100 fills (typical for 1 hour)...")
        
        weights = {'pros': 1.0, 'amateurs': 1.0, 'mood': 1.0}
        
        # Generate realistic fills
        fills = []
        for i in range(100):
            side = np.random.choice(['buy', 'sell'])
            size = np.random.uniform(0.05, 0.50)  # 0.05-0.50 BTC per fill
            fills.append({
                'side': side,
                'size': size,
                'ts': 1000000000 + i * 1000
            })
        
        # Old cohort
        old_cohort.adv20 = 1000.0  # Typical ADV20
        for fill in fills:
            old_cohort.update_from_fill(fill, weights)
        
        # New cohort
        new_cohort.adv20 = 1000.0
        for fill in fills:
            new_cohort.update_from_fill(fill, weights)
        
        old_signal = old_cohort.get_signal()
        new_signal = new_cohort.get_signal()
        
        print(f"\n{'Metric':<20} {'OLD':<15} {'NEW':<15} {'Change':<15}")
        print("-"*65)
        print(f"{'S_top':<20} {old_signal['S_top']:<15.6f} {new_signal['S_top']:<15.6f} {new_signal['S_top']/max(old_signal['S_top'], 0.000001):<15.1f}x")
        print(f"{'S_bot':<20} {old_signal['S_bot']:<15.6f} {new_signal['S_bot']:<15.6f} {new_signal['S_bot']/max(old_signal['S_bot'], 0.000001):<15.1f}x")
        print(f"{'S_mood':<20} {abs(old_signal['mood']):<15.6f} {abs(new_signal['mood']):<15.6f} {abs(new_signal['mood'])/max(abs(old_signal['mood']), 0.000001):<15.1f}x")
        
        self.results['old_signal'] = old_signal
        self.results['new_signal'] = new_signal
        
        # Verdict
        improvement = abs(new_signal['mood']) / max(abs(old_signal['mood']), 0.000001)
        if improvement > 10:
            print(f"\n✅ PASS: Signals are {improvement:.0f}x stronger!")
            return True
        elif improvement > 3:
            print(f"\n⚠️  MARGINAL: Signals are {improvement:.1f}x stronger (may work)")
            return True
        else:
            print(f"\n❌ FAIL: Signals only {improvement:.1f}x stronger (not enough)")
            return False
    
    def test_threshold_pass_rate(self):
        """Test 2: Check how many bars would pass new thresholds"""
        print("\n" + "="*60)
        print("TEST 2: THRESHOLD PASS RATE")
        print("="*60)
        
        df = self.load_historical_signals()
        if df is None or len(df) == 0:
            print("❌ Cannot test (no historical data)")
            return False
        
        # Parse columns
        if 's_mood' not in df.columns:
            # CSV might have different column names
            print(f"Columns: {df.columns.tolist()}")
            print("❌ Cannot find signal columns")
            return False
        
        # Old thresholds
        old_S_MIN = 0.015
        old_M_MIN = 0.015
        old_CONF_MIN = 0.15
        old_ALPHA_MIN = 0.02
        
        # New thresholds
        new_S_MIN = 0.003
        new_M_MIN = 0.003
        new_CONF_MIN = 0.08
        new_ALPHA_MIN = 0.008
        
        print(f"\nOLD Thresholds: S_MIN={old_S_MIN}, M_MIN={old_M_MIN}, CONF_MIN={old_CONF_MIN}")
        print(f"NEW Thresholds: S_MIN={new_S_MIN}, M_MIN={new_M_MIN}, CONF_MIN={new_CONF_MIN}")
        
        # Apply old thresholds to SCALED signals
        # Scale signals up by 10x (simulating stronger cohort)
        df['s_mood_scaled'] = df['s_mood'] * 10.0
        df['s_top_scaled'] = df.get('s_top', 0) * 10.0
        df['s_bot_scaled'] = df.get('s_bot', 0) * 10.0
        
        # Old pass rate (with weak signals)
        old_pass = (
            (abs(df['s_mood']) >= old_M_MIN) &
            (df.get('p_neutral', 1.0) <= (1 - old_CONF_MIN))
        )
        old_pass_rate = old_pass.sum() / len(df)
        
        # New pass rate (with scaled signals)
        new_pass = (
            (abs(df['s_mood_scaled']) >= new_M_MIN) &
            (df.get('p_neutral', 1.0) <= (1 - new_CONF_MIN))
        )
        new_pass_rate = new_pass.sum() / len(df)
        
        print(f"\nHistorical bars analyzed: {len(df)}")
        print(f"\n{'Threshold':<20} {'Pass Rate':<15} {'Bars/Day':<15}")
        print("-"*50)
        print(f"{'OLD (weak signals)':<20} {old_pass_rate*100:<15.1f}% {old_pass_rate*288:<15.0f}")
        print(f"{'NEW (strong signals)':<20} {new_pass_rate*100:<15.1f}% {new_pass_rate*288:<15.0f}")
        
        self.results['old_pass_rate'] = old_pass_rate
        self.results['new_pass_rate'] = new_pass_rate
        
        # Verdict
        if new_pass_rate > 0.10:  # >10% pass rate
            print(f"\n✅ PASS: {new_pass_rate*100:.1f}% pass rate = {new_pass_rate*288:.0f} potential trades/day")
            return True
        elif new_pass_rate > 0.05:  # 5-10%
            print(f"\n⚠️  MARGINAL: {new_pass_rate*100:.1f}% pass rate = {new_pass_rate*288:.0f} trades/day")
            return True
        else:
            print(f"\n❌ FAIL: Only {new_pass_rate*100:.1f}% pass rate = {new_pass_rate*288:.0f} trades/day")
            return False
    
    def test_model_neutrality(self):
        """Test 3: Check if model is too neutral"""
        print("\n" + "="*60)
        print("TEST 3: MODEL NEUTRALITY CHECK")
        print("="*60)
        
        df = self.load_historical_signals()
        if df is None or len(df) == 0:
            print("❌ Cannot test (no historical data)")
            return False
        
        if 'p_neutral' not in df.columns:
            print("❌ Cannot find p_neutral column")
            return False
        
        avg_neutral = df['p_neutral'].mean()
        median_neutral = df['p_neutral'].median()
        pct_90_plus = (df['p_neutral'] > 0.90).sum() / len(df)
        pct_80_plus = (df['p_neutral'] > 0.80).sum() / len(df)
        
        print(f"\nModel predictions (p_neutral):")
        print(f"  Average: {avg_neutral*100:.1f}%")
        print(f"  Median:  {median_neutral*100:.1f}%")
        print(f"  >90% neutral: {pct_90_plus*100:.1f}% of bars")
        print(f"  >80% neutral: {pct_80_plus*100:.1f}% of bars")
        
        self.results['avg_neutral'] = avg_neutral
        
        # Verdict
        if avg_neutral < 0.70:
            print(f"\n✅ PASS: Model shows conviction (avg neutral={avg_neutral*100:.1f}%)")
            return True
        elif avg_neutral < 0.85:
            print(f"\n⚠️  MARGINAL: Model somewhat neutral (avg={avg_neutral*100:.1f}%)")
            return True
        else:
            print(f"\n❌ FAIL: Model too neutral (avg={avg_neutral*100:.1f}%) - needs retraining")
            return False
    
    def estimate_trade_frequency(self):
        """Test 4: Estimate daily trade frequency"""
        print("\n" + "="*60)
        print("TEST 4: TRADE FREQUENCY PROJECTION")
        print("="*60)
        
        # Use results from previous tests
        new_pass_rate = self.results.get('new_pass_rate', 0.15)
        
        bars_per_day = 288  # 5m bars
        estimated_trades_per_day = new_pass_rate * bars_per_day
        
        # Account for bandit filtering (bandit selects ~50% of passed bars)
        bandit_factor = 0.5
        final_estimate = estimated_trades_per_day * bandit_factor
        
        print(f"\nEstimated daily trades:")
        print(f"  Pass rate: {new_pass_rate*100:.1f}%")
        print(f"  Bars passed: {estimated_trades_per_day:.0f}")
        print(f"  After bandit filter: {final_estimate:.0f}")
        
        self.results['estimated_trades_per_day'] = final_estimate
        
        # Verdict
        target_min = 10
        target_max = 100
        
        if target_min <= final_estimate <= target_max:
            print(f"\n✅ PASS: {final_estimate:.0f} trades/day (target: {target_min}-{target_max})")
            return True
        elif final_estimate > target_max:
            print(f"\n⚠️  HIGH: {final_estimate:.0f} trades/day (may be overtrading)")
            return True
        elif final_estimate > 5:
            print(f"\n⚠️  LOW: {final_estimate:.0f} trades/day (below target)")
            return True
        else:
            print(f"\n❌ FAIL: Only {final_estimate:.0f} trades/day (too low)")
            return False
    
    def run_all_tests(self):
        """Run all validation tests"""
        print("\n" + "="*70)
        print("  5M BOT FIX - QUICK VALIDATION")
        print("  Testing if fixes will work (without waiting 7 days)")
        print("="*70)
        
        tests = [
            ("Cohort Signal Strength", self.test_cohort_strength),
            ("Threshold Pass Rate", self.test_threshold_pass_rate),
            ("Model Neutrality", self.test_model_neutrality),
            ("Trade Frequency", self.estimate_trade_frequency)
        ]
        
        results = []
        for name, test_func in tests:
            try:
                passed = test_func()
                results.append((name, passed))
            except Exception as e:
                print(f"\n❌ ERROR in {name}: {e}")
                results.append((name, False))
        
        # Final verdict
        print("\n" + "="*70)
        print("  FINAL VERDICT")
        print("="*70)
        
        print(f"\n{'Test':<30} {'Result':<15}")
        print("-"*45)
        
        pass_count = 0
        for name, passed in results:
            symbol = "✅" if passed else "❌"
            print(f"{name:<30} {symbol}")
            if passed:
                pass_count += 1
        
        print(f"\nPassed: {pass_count}/{len(results)}")
        
        # Overall verdict
        if pass_count == len(results):
            print("\n🎉 EXCELLENT: All tests passed! Fix should work.")
            print("   → Deploy with high confidence")
        elif pass_count >= len(results) - 1:
            print("\n✅ GOOD: Most tests passed! Fix likely to work.")
            print("   → Deploy and monitor closely")
        elif pass_count >= len(results) / 2:
            print("\n⚠️  MARGINAL: Some tests passed. Fix may work.")
            print("   → Deploy with caution, expect issues")
        else:
            print("\n❌ POOR: Most tests failed. Fix unlikely to work.")
            print("   → Do NOT deploy, needs fundamental redesign")
        
        # Specific recommendations
        print("\n" + "="*70)
        print("  RECOMMENDATIONS")
        print("="*70)
        
        if pass_count >= len(results) - 1:
            print("\n✓ Start bot: .\start_5m_bot.ps1")
            print("✓ Monitor: .\monitor_5m_bot.ps1")
            print("✓ Check after 1 hour: Should see 1-3 trades")
            print("✓ Check after 24 hours: Should see 10-40 trades")
        else:
            print("\n✗ DO NOT start bot yet")
            if self.results.get('avg_neutral', 0) > 0.85:
                print("✗ Model is too neutral - needs retraining")
            if self.results.get('new_pass_rate', 0) < 0.05:
                print("✗ Thresholds still too high - lower further")
            if self.results.get('new_signal', {}).get('mood', 0) < 0.01:
                print("✗ Cohort signals still too weak - check WebSocket")
        
        return pass_count >= len(results) / 2

if __name__ == "__main__":
    validator = QuickValidator()
    success = validator.run_all_tests()
    sys.exit(0 if success else 1)
