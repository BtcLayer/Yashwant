"""
Example: How to Use the Backtesting Engine
"""

import pandas as pd
import numpy as np
from backtest_engine import run_allocator_backtest, run_simple_backtest, SimpleThompsonBandit


def example_multi_arm_backtest():
    """Example of multi-arm bandit backtest"""
    
    print("="*80)
    print("EXAMPLE: Multi-Arm Bandit Backtest")
    print("="*80)
    
    # Load your data
    signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
    signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'])
    signals_df = signals_df.set_index('timestamp')
    
    # Calculate returns
    signals_df['returns'] = signals_df['close'].pct_change()
    
    # Prepare arm signals (4 arms: S_top, S_bot, S_mood, model)
    arm_signals = signals_df[['S_top', 'S_bot', 'S_mood', 'dir']].fillna(0).values
    
    # Prepare eligibility (all arms eligible when signal != 0)
    arm_eligible = np.abs(arm_signals) > 0.001
    
    # ADV series (average daily volume)
    adv_series = pd.Series(25000000.0, index=signals_df.index)  # $25M ADV
    
    # Backtest parameters
    params = {
        'cooldown_bars': 12,  # 1 hour cooldown (12 * 5min)
        'cost_bps': 5.0,  # 5 bps transaction cost
        'impact_k': 0.1,  # Market impact coefficient
        'side_eps_vec': np.array([0.001, 0.001, 0.001, 0.3]),  # Thresholds for each arm
        'sigma_target': 0.20,  # 20% target volatility
        'pos_max': 1.0,  # Max position size
        'dd_stop': 0.05,  # 5% drawdown stop
    }
    
    # Run backtest
    print("\nRunning backtest...")
    Eq_df, Tr_df, Bu_df, metrics = run_allocator_backtest(
        bt_df=signals_df,
        arm_signals=arm_signals,
        arm_eligible=arm_eligible,
        adv_series=adv_series,
        **params
    )
    
    # Display results
    print("\n" + "="*80)
    print("BACKTEST RESULTS")
    print("="*80)
    print(f"Final Equity: {metrics['final_equity']:.4f}")
    print(f"Total Return: {(metrics['final_equity'] - 1.0) * 100:.2f}%")
    print(f"Number of Trades: {metrics['n_trades']}")
    print(f"Sharpe Ratio: {metrics['sharpe']:.4f}")
    print(f"Sortino Ratio: {metrics['sortino']:.4f}")
    print(f"Max Drawdown: {metrics['maxDD']*100:.2f}%")
    print(f"Turnover: {metrics['turnover']:.2f}")
    print(f"Hit Rate: {metrics['hit_rate']*100:.2f}%")
    
    # Show sample trades
    print("\n" + "="*80)
    print("SAMPLE TRADES (First 10)")
    print("="*80)
    print(Tr_df.head(10))
    
    # Show bandit arm selection
    print("\n" + "="*80)
    print("ARM SELECTION DISTRIBUTION")
    print("="*80)
    arm_names = ['S_top', 'S_bot', 'S_mood', 'model']
    arm_counts = Bu_df['chosen'].value_counts().sort_index()
    for arm_idx, count in arm_counts.items():
        print(f"{arm_names[arm_idx]}: {count} times ({count/len(Bu_df)*100:.1f}%)")
    
    # Save results
    Eq_df.to_csv('backtest_equity.csv')
    Tr_df.to_csv('backtest_trades.csv')
    Bu_df.to_csv('backtest_bandit_updates.csv')
    print("\nResults saved to CSV files")
    
    return Eq_df, Tr_df, Bu_df, metrics


def example_simple_backtest():
    """Example of simple single-signal backtest"""
    
    print("\n" + "="*80)
    print("EXAMPLE: Simple Single-Signal Backtest")
    print("="*80)
    
    # Load data
    signals_df = pd.read_csv('paper_trading_outputs/5m/sheets_fallback/signals.csv')
    signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'])
    signals_df = signals_df.set_index('timestamp')
    
    # Calculate returns
    returns = signals_df['close'].pct_change()
    
    # Test S_top signal
    print("\nTesting S_top signal...")
    metrics_top = run_simple_backtest(
        signals_df=signals_df,
        returns_series=returns,
        signal_col='S_top',
        threshold=0.001,
        cost_bps=5.0,
        pos_max=1.0
    )
    
    print(f"\nS_top Results:")
    print(f"  Final Equity: {metrics_top['final_equity']:.4f}")
    print(f"  Total Return: {metrics_top['total_return']*100:.2f}%")
    print(f"  Sharpe: {metrics_top['sharpe']:.4f}")
    print(f"  Max DD: {metrics_top['max_dd']*100:.2f}%")
    print(f"  Trades: {metrics_top['n_trades']}")
    print(f"  Win Rate: {metrics_top['win_rate']*100:.2f}%")
    
    # Test S_mood signal
    print("\nTesting S_mood signal...")
    metrics_mood = run_simple_backtest(
        signals_df=signals_df,
        returns_series=returns,
        signal_col='S_mood',
        threshold=0.001,
        cost_bps=5.0,
        pos_max=1.0
    )
    
    print(f"\nS_mood Results:")
    print(f"  Final Equity: {metrics_mood['final_equity']:.4f}")
    print(f"  Total Return: {metrics_mood['total_return']*100:.2f}%")
    print(f"  Sharpe: {metrics_mood['sharpe']:.4f}")
    print(f"  Max DD: {metrics_mood['max_dd']*100:.2f}%")
    print(f"  Trades: {metrics_mood['n_trades']}")
    print(f"  Win Rate: {metrics_mood['win_rate']*100:.2f}%")
    
    return metrics_top, metrics_mood


if __name__ == "__main__":
    print("Backtesting Engine Examples")
    print("="*80)
    
    # Run multi-arm backtest
    try:
        Eq, Tr, Bu, metrics = example_multi_arm_backtest()
    except Exception as e:
        print(f"\nMulti-arm backtest failed: {e}")
    
    # Run simple backtest
    try:
        metrics_top, metrics_mood = example_simple_backtest()
    except Exception as e:
        print(f"\nSimple backtest failed: {e}")
    
    print("\n" + "="*80)
    print("Examples complete!")
    print("="*80)
