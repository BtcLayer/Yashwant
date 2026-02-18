"""
PHASE 2 A/B TESTING COMPARISON
=================================

Compare Phase 1 (raw accumulation) vs Phase 2 (ADV20 normalization) performance.

This script runs both configurations side-by-side on historical data to validate
that Phase 2 improvements maintain or improve profitability while fixing the
mathematical incoherence identified in the audit.

Test Setup:
- Period: Last 7 days of 1h data (168 bars)
- Configurations: Phase 1 (raw) vs Phase 2 (normalized)
- Metrics: Sharpe ratio, PnL, Win rate, Signal correlations

Expected Outcomes:
- Phase 2 should match or exceed Phase 1 PnL
- Phase 2 signals should have higher correlation with returns
- Phase 2 should be more stable across different volume regimes

Usage:
    python ab_test_phase1_vs_phase2.py
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from collections import deque
from typing import Dict, List, Tuple
import requests
import time

# Add live_demo to path
sys.path.insert(0, str(Path(__file__).parent / "live_demo"))
from cohort_signals import CohortState

HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"

def fetch_btc_1h_data(days: int = 7) -> pd.DataFrame:
    """Fetch BTC 1h price data from Hyperliquid"""
    import datetime
    
    # Calculate timestamps
    end_time = int(time.time() * 1000)
    start_time = end_time - (days * 24 * 3600 * 1000)
    
    # Fetch candles from Hyperliquid
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "1h",
            "startTime": start_time,
            "endTime": end_time
        }
    }
    
    response = requests.post(HYPERLIQUID_API, json=payload, timeout=30)
    data = response.json()
    
    # Parse candles
    candles = []
    for candle in data:
        candles.append({
            'timestamp': pd.to_datetime(int(candle['t']), unit='ms'),
            'open': float(candle['o']),
            'high': float(candle['h']),
            'low': float(candle['l']),
            'close': float(candle['c']),
            'volume': float(candle['v'])
        })
    
    df = pd.DataFrame(candles)
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['returns'] = df['close'].pct_change()
    
    return df

def load_cohort_addresses() -> Tuple[set, set]:
    """Load top and bottom cohort addresses"""
    top_df = pd.read_csv("live_demo_1h/top_cohort.csv")
    bottom_df = pd.read_csv("live_demo_1h/bottom_cohort.csv")
    
    top_addresses = set(top_df['Account'].str.lower())
    bottom_addresses = set(bottom_df['Account'].str.lower())
    
    print(f"Loaded {len(top_addresses)} top traders, {len(bottom_addresses)} bottom traders")
    return top_addresses, bottom_addresses

def fetch_fills_for_period(addresses: List[str], start_ts: int, end_ts: int) -> List[Dict]:
    """Fetch all fills for given addresses in time period"""
    all_fills = []
    
    for i, addr in enumerate(addresses):
        if i % 50 == 0:
            print(f"  Fetching fills {i+1}/{len(addresses)}...")
        
        try:
            payload = {
                "type": "userFillsByTime",
                "user": addr,
                "startTime": start_ts,
                "endTime": end_ts
            }
            response = requests.post(HYPERLIQUID_API, json=payload, timeout=10)
            data = response.json()
            
            if isinstance(data, list):
                for fill in data:
                    if fill.get('coin') == 'BTC':
                        all_fills.append({
                            'address': addr,
                            'side': fill.get('side'),
                            'size': float(fill.get('sz', 0)),
                            'price': float(fill.get('px', 0)),
                            'ts': int(fill.get('time', 0))
                        })
            
            time.sleep(0.1)  # Rate limit
        except Exception as e:
            print(f"    Error fetching {addr}: {e}")
            continue
    
    return all_fills

def reconstruct_signals_phase1(
    fills: List[Dict], 
    price_df: pd.DataFrame,
    top_addresses: set,
    bottom_addresses: set,
    window: int = 100
) -> pd.DataFrame:
    """Reconstruct signals using Phase 1 logic (raw accumulation)"""
    signals = []
    
    for idx, row in price_df.iterrows():
        bar_start = int(row['timestamp'].timestamp() * 1000)
        bar_end = bar_start + 3600000  # 1 hour
        
        # Filter fills in this bar
        bar_fills = [f for f in fills if bar_start <= f['ts'] < bar_end]
        
        # Create CohortState for this bar
        state = CohortState(
            window=window,
            use_adv20_normalization=False,  # Phase 1: Raw accumulation
            use_signal_decay=False
        )
        state.set_adv20(row['volume'])
        
        # Process fills
        for fill in bar_fills:
            weights = {
                'pros': 1.0 if fill['address'] in top_addresses else 0.0,
                'amateurs': 1.0 if fill['address'] in bottom_addresses else 0.0,
                'mood': 1.0
            }
            state.update_from_fill(fill, weights)
        
        signals.append({
            'timestamp': row['timestamp'],
            'S_top': state.pros,
            'S_bot': state.amateurs,
            'S_mood': state.mood,
            'fills_count': len(bar_fills)
        })
    
    return pd.DataFrame(signals)

def reconstruct_signals_phase2(
    fills: List[Dict], 
    price_df: pd.DataFrame,
    top_addresses: set,
    bottom_addresses: set,
    window: int = 100
) -> pd.DataFrame:
    """Reconstruct signals using Phase 2 logic (ADV20 normalized)"""
    signals = []
    
    for idx, row in price_df.iterrows():
        bar_start = int(row['timestamp'].timestamp() * 1000)
        bar_end = bar_start + 3600000  # 1 hour
        
        # Filter fills in this bar
        bar_fills = [f for f in fills if bar_start <= f['ts'] < bar_end]
        
        # Create CohortState for this bar
        state = CohortState(
            window=window,
            use_adv20_normalization=True,  # Phase 2: ADV20 normalized
            use_signal_decay=True,  # Phase 2: Exponential decay
            timeframe_hours=1.0,
            signal_half_life_minutes=10.0
        )
        state.set_adv20(row['volume'])
        
        # Process fills
        for fill in bar_fills:
            weights = {
                'pros': 1.0 if fill['address'] in top_addresses else 0.0,
                'amateurs': 1.0 if fill['address'] in bottom_addresses else 0.0,
                'mood': 1.0
            }
            state.update_from_fill(fill, weights)
        
        signals.append({
            'timestamp': row['timestamp'],
            'S_top': state.pros,
            'S_bot': state.amateurs,
            'S_mood': state.mood,
            'fills_count': len(bar_fills)
        })
    
    return pd.DataFrame(signals)

def compute_signal_correlations(signals_df: pd.DataFrame, price_df: pd.DataFrame) -> Dict:
    """Compute correlations between signals and forward returns"""
    merged = signals_df.merge(price_df[['timestamp', 'returns']], on='timestamp')
    
    # Forward returns
    for lag in [1, 2, 3, 6, 12, 24]:
        merged[f'ret_{lag}h'] = merged['returns'].shift(-lag)
    
    correlations = {}
    for signal in ['S_top', 'S_bot', 'S_mood']:
        correlations[signal] = {}
        for lag in [1, 2, 3, 6, 12, 24]:
            corr = merged[[signal, f'ret_{lag}h']].corr().iloc[0, 1]
            correlations[signal][f'{lag}h'] = corr
    
    return correlations

def simulate_trading(signals_df: pd.DataFrame, price_df: pd.DataFrame, config: Dict) -> Dict:
    """Simple trading simulation"""
    merged = signals_df.merge(price_df[['timestamp', 'close', 'returns']], on='timestamp')
    
    positions = []
    pnl_series = []
    equity = 10000
    
    # Handle nested config structure
    thresholds = config.get('thresholds', config)
    S_MIN = thresholds.get('S_MIN', 0.05)
    M_MIN = thresholds.get('M_MIN', 0.06)
    position = 0  # -1, 0, 1
    
    for idx, row in merged.iterrows():
        # Decision logic
        signal = row['S_top'] - row['S_bot']
        
        if abs(signal) > S_MIN or abs(row['S_mood']) > M_MIN:
            target_position = 1 if signal > 0 else -1
        else:
            target_position = 0
        
        # Update PnL if position changed
        if position != 0:
            pnl = position * row['returns'] * equity
            equity += pnl
            pnl_series.append(pnl)
        
        # Update position
        if target_position != position:
            positions.append({
                'timestamp': row['timestamp'],
                'from': position,
                'to': target_position,
                'signal': signal
            })
            position = target_position
    
    # Metrics
    pnl_series = pd.Series(pnl_series)
    sharpe = (pnl_series.mean() / pnl_series.std()) * np.sqrt(24 * 365) if len(pnl_series) > 0 else 0
    total_pnl = equity - 10000
    win_rate = (pnl_series > 0).sum() / len(pnl_series) if len(pnl_series) > 0 else 0
    
    return {
        'total_pnl': total_pnl,
        'final_equity': equity,
        'sharpe': sharpe,
        'win_rate': win_rate,
        'num_trades': len(positions),
        'num_bars': len(merged)
    }

def main():
    print("=" * 80)
    print("PHASE 2 A/B TESTING: Raw Accumulation vs ADV20 Normalization")
    print("=" * 80)
    print()
    
    # Load data
    print("📊 Fetching BTC 1h price data from Hyperliquid (last 7 days)...")
    price_df = fetch_btc_1h_data(days=7)
    print(f"  Loaded {len(price_df)} bars")
    print()
    
    # Load cohorts
    print("👥 Loading cohort addresses...")
    top_addresses, bottom_addresses = load_cohort_addresses()
    all_addresses = list(top_addresses | bottom_addresses)
    print()
    
    # Fetch fills
    print("📡 Fetching historical fills from Hyperliquid...")
    start_ts = int(price_df['timestamp'].min().timestamp() * 1000)
    end_ts = int(price_df['timestamp'].max().timestamp() * 1000)
    fills = fetch_fills_for_period(all_addresses, start_ts, end_ts)
    print(f"  Fetched {len(fills)} BTC fills")
    print()
    
    # Phase 1: Raw accumulation
    print("🔬 Phase 1: Reconstructing signals (raw accumulation)...")
    signals_phase1 = reconstruct_signals_phase1(fills, price_df, top_addresses, bottom_addresses)
    corr_phase1 = compute_signal_correlations(signals_phase1, price_df)
    
    # Load Phase 1 config
    with open("live_demo_1h/config.json", "r") as f:
        config_phase1 = json.load(f)
    
    sim_phase1 = simulate_trading(signals_phase1, price_df, config_phase1)
    print()
    
    # Phase 2: ADV20 normalized
    print("🔬 Phase 2: Reconstructing signals (ADV20 normalized)...")
    signals_phase2 = reconstruct_signals_phase2(fills, price_df, top_addresses, bottom_addresses)
    corr_phase2 = compute_signal_correlations(signals_phase2, price_df)
    
    # Load Phase 2 config
    with open("live_demo_1h/config_phase2.json", "r") as f:
        config_phase2 = json.load(f)
    
    sim_phase2 = simulate_trading(signals_phase2, price_df, config_phase2)
    print()
    
    # Report
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    
    print("PHASE 1 (Raw Accumulation):")
    print(f"  Signal ranges:")
    print(f"    S_top: {signals_phase1['S_top'].min():.4f} to {signals_phase1['S_top'].max():.4f}")
    print(f"    S_bot: {signals_phase1['S_bot'].min():.4f} to {signals_phase1['S_bot'].max():.4f}")
    print(f"    S_mood: {signals_phase1['S_mood'].min():.4f} to {signals_phase1['S_mood'].max():.4f}")
    print(f"  Correlations (S_top vs forward returns):")
    for lag, corr in corr_phase1['S_top'].items():
        print(f"    {lag}: {corr:.4f}")
    print(f"  Trading simulation:")
    print(f"    PnL: ${sim_phase1['total_pnl']:.2f}")
    print(f"    Sharpe: {sim_phase1['sharpe']:.2f}")
    print(f"    Win rate: {sim_phase1['win_rate']:.1%}")
    print(f"    Trades: {sim_phase1['num_trades']}")
    print()
    
    print("PHASE 2 (ADV20 Normalized + Decay):")
    print(f"  Signal ranges:")
    print(f"    S_top: {signals_phase2['S_top'].min():.6f} to {signals_phase2['S_top'].max():.6f}")
    print(f"    S_bot: {signals_phase2['S_bot'].min():.6f} to {signals_phase2['S_bot'].max():.6f}")
    print(f"    S_mood: {signals_phase2['S_mood'].min():.6f} to {signals_phase2['S_mood'].max():.6f}")
    print(f"  Correlations (S_top vs forward returns):")
    for lag, corr in corr_phase2['S_top'].items():
        print(f"    {lag}: {corr:.4f}")
    print(f"  Trading simulation:")
    print(f"    PnL: ${sim_phase2['total_pnl']:.2f}")
    print(f"    Sharpe: {sim_phase2['sharpe']:.2f}")
    print(f"    Win rate: {sim_phase2['win_rate']:.1%}")
    print(f"    Trades: {sim_phase2['num_trades']}")
    print()
    
    # Verdict
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)
    
    delta_sharpe = sim_phase2['sharpe'] - sim_phase1['sharpe']
    delta_corr = corr_phase2['S_top']['1h'] - corr_phase1['S_top']['1h']
    
    if delta_sharpe > 0.2 and delta_corr > 0.01:
        print("✅ Phase 2 APPROVED: Higher Sharpe and better correlations")
        recommendation = "DEPLOY Phase 2"
    elif delta_sharpe < -0.2:
        print("❌ Phase 2 REJECTED: Worse Sharpe ratio")
        recommendation = "KEEP Phase 1"
    else:
        print("⚠️ Phase 2 MARGINAL: Similar performance")
        recommendation = "RUN LONGER TEST"
    
    print(f"  Sharpe delta: {delta_sharpe:+.2f}")
    print(f"  Correlation delta (1h): {delta_corr:+.4f}")
    print(f"  Recommendation: {recommendation}")
    print()
    
    # Save results
    results = {
        'phase1': {
            'signals': signals_phase1.describe().to_dict(),
            'correlations': corr_phase1,
            'simulation': sim_phase1
        },
        'phase2': {
            'signals': signals_phase2.describe().to_dict(),
            'correlations': corr_phase2,
            'simulation': sim_phase2
        },
        'verdict': {
            'delta_sharpe': delta_sharpe,
            'delta_corr_1h': delta_corr,
            'recommendation': recommendation
        }
    }
    
    with open("ab_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print("Results saved to: ab_test_results.json")

if __name__ == "__main__":
    main()
