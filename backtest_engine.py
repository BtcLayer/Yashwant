"""
Standalone Backtesting Engine
Extracted from Unified_Overlay_Training.ipynb
Comprehensive backtesting with multi-arm bandit allocation
"""

import numpy as np
import pandas as pd
from collections import deque
from typing import Tuple, Dict, Optional
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
import json  # Day 4: For saving backtest results
import os
from datetime import datetime


class SimpleThompsonBandit:
    """Thompson Sampling Multi-Arm Bandit"""
    
    def __init__(self, n_arms: int):
        self.counts = np.zeros(n_arms, dtype=float)
        self.means = np.zeros(n_arms, dtype=float)
        self.vars = np.ones(n_arms, dtype=float)
        
    def select(self, eligible: np.ndarray) -> int:
        """Select arm using Thompson Sampling"""
        if not np.any(eligible):
            return 0
        
        # Sample from posterior
        samples = np.random.normal(self.means, np.sqrt(self.vars))
        
        # Only consider eligible arms
        samples[~eligible] = -np.inf
        
        return int(np.argmax(samples))
    
    def update(self, arm: int, reward: float):
        """Update arm statistics with new reward"""
        self.counts[arm] += 1
        n = self.counts[arm]
        
        # Update mean
        self.means[arm] = (self.means[arm] * (n - 1) + reward) / n
        
        # Update variance (simplified)
        if n > 1:
            self.vars[arm] = 1.0 / n


def run_allocator_backtest(
    bt_df: pd.DataFrame,
    arm_signals: np.ndarray,
    arm_eligible: np.ndarray,
    adv_series: pd.Series,
    cooldown_bars: int,
    cost_bps: float,
    impact_k: float,
    side_eps_vec: np.ndarray,
    eps: float = 1e-12,
    sigma_target: float = 0.20,
    pos_max: float = 1.0,
    dd_stop: float = 0.05,
    latency_bars: int = 0,
    annualizer: float = None,
    save_results: bool = False,  # Day 4: Optional save to JSON
    save_results_path: Optional[str] = None,  # Day 4: Custom output path
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]:
    """
    Comprehensive backtesting with bandit allocation
    
    Args:
        bt_df: DataFrame with 'returns' column and timestamp index
        arm_signals: (n_bars, n_arms) array of signal values
        arm_eligible: (n_bars, n_arms) boolean array of eligibility
        adv_series: Series of average daily volume (for impact calculation)
        cooldown_bars: Minimum bars between trades
        cost_bps: Transaction cost in basis points
        impact_k: Market impact coefficient
        side_eps_vec: Signal threshold for each arm
        eps: Small number for numerical stability
        sigma_target: Target volatility for position sizing
        pos_max: Maximum position size
        dd_stop: Drawdown stop threshold
        latency_bars: Execution latency in bars
        annualizer: Annualization factor (default: sqrt(365*24*12) for 5m bars)
    
    Returns:
        Eq_df: Equity curve DataFrame
        Tr_df: Trades DataFrame
        Bu_df: Bandit updates DataFrame
        metrics: Performance metrics dictionary
    """
    
    n = len(bt_df)
    rets = bt_df['returns'].values if 'returns' in bt_df.columns else np.zeros(n)
    
    # ADV handling
    adv_valid = isinstance(adv_series, pd.Series) and not adv_series.dropna().empty
    adv_arr = adv_series.reindex(bt_df.index).to_numpy() if adv_valid else np.ones(n, dtype=float)
    impact_k_eff = impact_k if adv_valid else 0.0
    
    bandit = SimpleThompsonBandit(n_arms=arm_signals.shape[1])
    
    pos = 0.0
    pos_smooth = 0.0
    last_flip_idx = -10**9
    
    exec_pos_buffer = deque(maxlen=cooldown_bars + 1)
    exec_pos_buffer.append(0.0)
    
    records_eq = []
    records_tr = []
    records_bu = []
    
    cum_equity = 1.0
    equity_series = np.ones(n, dtype=float)
    
    for t in range(n):
        exec_pos = exec_pos_buffer[0] if latency_bars > 0 else pos_smooth
        
        # Check eligibility and select arm
        elig = arm_eligible[t] if t < len(arm_eligible) else np.array([False]*arm_signals.shape[1])
        desired_side = pos
        chosen = None
        
        if np.any(elig):
            chosen = bandit.select(elig)
            raw_val = float(arm_signals[t, chosen])
            th = float(side_eps_vec[chosen]) if (side_eps_vec is not None) else 0.0
            
            if abs(raw_val) < th:
                desired_side = 0.0
            else:
                desired_side = np.sign(raw_val) * pos_max
        
        # Position sizing with volatility targeting
        if t > 0 and abs(rets[t]) > eps:
            vol_est = np.std(rets[max(0, t-20):t+1])
            if vol_est > eps:
                vol_scaler = sigma_target / (vol_est * np.sqrt(252 * 24 * 12))  # Annualized
                desired_side *= min(vol_scaler, 2.0)  # Cap at 2x
        
        # Cooldown logic
        if abs(desired_side - exec_pos) > eps and (t - last_flip_idx) >= cooldown_bars:
            exec_pos_buffer.append(desired_side)
            last_exec_pos = exec_pos
            
            # Cost calculation
            cost_bps_eff = cost_bps
            if impact_k_eff > 0 and adv_valid:
                notional_change = abs(desired_side - exec_pos)
                impact_bps = impact_k_eff * notional_change / (adv_arr[t] + eps)
                cost_bps_eff += impact_bps
            
            records_tr.append((bt_df.index[t], exec_pos, desired_side, cost_bps_eff))
            last_exec_pos = exec_pos
            last_flip_idx = t
        
        pnl = rets[t] * (exec_pos_buffer[0] if latency_bars > 0 else exec_pos)
        pnl -= (cost_bps / 10000.0) if cost_bps > 0 else 0.0
        cum_equity *= (1.0 + pnl)
        equity_series[t] = cum_equity
        records_eq.append((bt_df.index[t], cum_equity))
        
        if chosen is not None:
            bandit.update(chosen, pnl)
            records_bu.append((bt_df.index[t], int(chosen), float(pnl)))
        
        # Drawdown stop
        if dd_stop > 0:
            peak = np.max(equity_series[:t+1])
            if peak > 0 and (cum_equity / peak - 1.0) < -dd_stop:
                exec_pos_buffer.append(0.0)
                last_exec_pos = 0.0
        
        pos_smooth = exec_pos_buffer[0] if exec_pos_buffer else 0.0
    
    Eq = pd.DataFrame.from_records(records_eq, columns=['ts', 'equity']).set_index('ts')
    Tr = pd.DataFrame.from_records(records_tr, columns=['ts', 'from_pos', 'to_pos', 'cost_bps'])
    Bu = pd.DataFrame.from_records(records_bu, columns=['ts', 'chosen', 'reward'])
    
    # Calculate performance metrics
    eq_rets = Eq['equity'].pct_change().dropna()
    if annualizer is None:
        annualizer = np.sqrt(365*24*12)  # 5-minute bars
    
    sharpe = float(annualizer * eq_rets.mean() / (eq_rets.std() if eq_rets.std() != 0 else np.nan)) if len(eq_rets) else np.nan
    
    # Sortino ratio
    downside_rets = eq_rets[eq_rets < 0]
    sortino = float(annualizer * eq_rets.mean() / (downside_rets.std() if len(downside_rets) > 0 else np.nan)) if len(eq_rets) else np.nan
    
    maxdd = float(-(Eq['equity'] / Eq['equity'].cummax() - 1.0).min()) if not Eq.empty else np.nan
    
    # Turnover
    turnover = float(np.abs(Tr['to_pos'].astype(float) - Tr['from_pos'].astype(float)).sum()) if not Tr.empty else 0.0
    
    # Hit rate
    hit_rate = float((Tr['pnl_$'] > 0).sum() / max(len(Tr), 1)) if not Tr.empty and 'pnl_$' in Tr.columns else np.nan
    
    metrics = {
        'final_equity': float(Eq['equity'].iloc[-1]) if len(Eq) else 1.0,
        'n_trades': int(len(Tr)),
        'sharpe': sharpe,
        'sortino': sortino,
        'maxDD': maxdd,
        'turnover': turnover,
        'hit_rate': hit_rate,
    }
    
    # Day 4: Save results to JSON if requested
    if save_results:
        _save_backtest_results(metrics, 'allocator', save_results_path)
    
    return Eq, Tr, Bu, metrics


def run_simple_backtest(
    signals_df: pd.DataFrame,
    returns_series: pd.Series,
    signal_col: str = 'signal',
    threshold: float = 0.0,
    cost_bps: float = 5.0,
    pos_max: float = 1.0,
    save_results: bool = False,  # Day 4: Optional save to JSON
    save_results_path: Optional[str] = None,  # Day 4: Custom output path
) -> Dict:
    """
    Simple backtest for a single signal
    
    Args:
        signals_df: DataFrame with signals
        returns_series: Series of returns
        signal_col: Column name for signal
        threshold: Signal threshold
        cost_bps: Transaction cost in basis points
        pos_max: Maximum position size
    
    Returns:
        metrics: Performance metrics dictionary
    """
    
    # Align data
    aligned = pd.DataFrame({
        'signal': signals_df[signal_col],
        'returns': returns_series
    }).dropna()
    
    # Generate positions
    aligned['position'] = 0.0
    aligned.loc[aligned['signal'] > threshold, 'position'] = pos_max
    aligned.loc[aligned['signal'] < -threshold, 'position'] = -pos_max
    
    # Calculate PnL
    aligned['pnl'] = aligned['returns'] * aligned['position'].shift(1)
    
    # Apply costs on position changes
    aligned['pos_change'] = aligned['position'].diff().abs()
    aligned['cost'] = aligned['pos_change'] * (cost_bps / 10000.0)
    aligned['net_pnl'] = aligned['pnl'] - aligned['cost']
    
    # Calculate equity curve
    aligned['equity'] = (1 + aligned['net_pnl']).cumprod()
    
    # Metrics
    eq_rets = aligned['equity'].pct_change().dropna()
    annualizer = np.sqrt(252 * 24 * 12)  # 5-minute bars
    
    metrics = {
        'final_equity': float(aligned['equity'].iloc[-1]),
        'total_return': float(aligned['equity'].iloc[-1] - 1.0),
        'sharpe': float(annualizer * eq_rets.mean() / eq_rets.std()) if len(eq_rets) > 0 else np.nan,
        'max_dd': float(-(aligned['equity'] / aligned['equity'].cummax() - 1.0).min()),
        'n_trades': int((aligned['pos_change'] > 0).sum()),
        'win_rate': float((aligned['net_pnl'] > 0).sum() / len(aligned)),
    }
    
    # Day 4: Save results to JSON if requested
    if save_results:
        _save_backtest_results(metrics, 'simple', save_results_path)
    
    return metrics


def _save_backtest_results(metrics: Dict, backtest_type: str, custom_path: Optional[str] = None):
    """
    Day 4: Save backtest results to JSON file
    
    Args:
        metrics: Dictionary of performance metrics
        backtest_type: Type of backtest ('allocator' or 'simple')
        custom_path: Optional custom output path
    """
    # Create backtest_results directory if it doesn't exist
    os.makedirs('backtest_results', exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if custom_path:
        output_path = custom_path
    else:
        output_path = f'backtest_results/{backtest_type}_backtest_{timestamp}.json'
    
    # Add metadata
    result_data = {
        'timestamp': datetime.now().isoformat(),
        'backtest_type': backtest_type,
        'metrics': metrics
    }
    
    # Save to JSON
    with open(output_path, 'w') as f:
        json.dump(result_data, f, indent=2)
    
    print(f"✅ Backtest results saved to: {output_path}")


if __name__ == "__main__":
    print("Backtesting Engine Loaded")
    print("\nAvailable functions:")
    print("  - run_allocator_backtest(): Multi-arm bandit backtest")
    print("  - run_simple_backtest(): Simple single-signal backtest")
    print("  - SimpleThompsonBandit: Thompson sampling bandit class")
