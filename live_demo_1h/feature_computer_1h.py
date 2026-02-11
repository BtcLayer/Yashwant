"""
1h-specific feature computer that matches training features
"""
from collections import deque
from typing import List, Dict
import numpy as np
import pandas as pd

class LiveFeatureComputer1h:
    """
    Feature computer for 1h bot matching train_1h_model_oct_approach.py
    
    Expected features (15 total):
    ret_1, ret_12, ret_24, volume_ratio, volatility_12, rsi, bb_position,
    macd, macd_signal, macd_hist, momentum_24, hl_range, S_top, S_bot, flow_diff
    """
    
    def __init__(self, max_history=200):
        self.max_history = max_history
        self.history = deque(maxlen=max_history)
        
    def update_and_compute(self, bar_row: Dict, cohort: Dict) -> List[float]:
        """
        Update history and compute features
        
        Args:
            bar_row: {'open', 'high', 'low', 'close', 'volume'}
            cohort: {'pros', 'amateurs'}
        
        Returns:
            List of 15 features in correct order
        """
        # Add current bar to history
        self.history.append({
            'open': float(bar_row.get('open', 0)),
            'high': float(bar_row.get('high', 0)),
            'low': float(bar_row.get('low', 0)),
            'close': float(bar_row.get('close', 0)),
            'volume': float(bar_row.get('volume', 0)),
        })
        
        # Need at least 26 bars for MACD
        if len(self.history) < 26:
            # Return zeros during warmup
            return [0.0] * 15
        
        # Convert to pandas for easier calculation
        df = pd.DataFrame(list(self.history))
        
        # Calculate features (matching training exactly)
        ret_1 = df['close'].pct_change(1).iloc[-1] if len(df) > 1 else 0.0
        ret_12 = df['close'].pct_change(12).iloc[-1] if len(df) > 12 else 0.0
        ret_24 = df['close'].pct_change(24).iloc[-1] if len(df) > 24 else 0.0
        
        # Volume ratio (current vs mean of last 20)
        vol_mean = df['volume'].rolling(20).mean().iloc[-1] if len(df) > 20 else df['volume'].mean()
        volume_ratio = (df['volume'].iloc[-1] / vol_mean) - 1 if vol_mean > 0 else 0.0
        
        # Volatility (12-bar rolling std of returns)
        volatility_12 = df['close'].pct_change(1).rolling(12).std().iloc[-1] if len(df) > 12 else 0.0
        
        # RSI (14-period)
        rsi = self._calculate_rsi(df['close'], 14)
        
        # Bollinger Bands
        bb_position = self._calculate_bb_position(df['close'], 20, 2)
        
        # MACD
        macd, macd_signal, macd_hist = self._calculate_macd(df['close'])
        
        # Momentum (24-bar)
        momentum_24 = df['close'].pct_change(24).iloc[-1] if len(df) > 24 else 0.0
        
        # High-Low range
        hl_range = (df['high'].iloc[-1] - df['low'].iloc[-1]) / df['close'].iloc[-1] if df['close'].iloc[-1] > 0 else 0.0
        
        # Cohort signals
        S_top = float(cohort.get('pros', 0.0))
        S_bot = float(cohort.get('amateurs', 0.0))
        flow_diff = S_top - S_bot
        
        return [
            ret_1, ret_12, ret_24, volume_ratio, volatility_12,
            rsi, bb_position, macd, macd_signal, macd_hist,
            momentum_24, hl_range, S_top, S_bot, flow_diff
        ]
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 0.5  # Neutral during warmup
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        rsi_val = rsi.iloc[-1]
        return (rsi_val / 100.0) if not pd.isna(rsi_val) else 0.5
    
    def _calculate_bb_position(self, prices, period=20, num_std=2):
        """Calculate position within Bollinger Bands (0-1)"""
        if len(prices) < period:
            return 0.5
        
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        
        current = prices.iloc[-1]
        upper_val = upper.iloc[-1]
        lower_val = lower.iloc[-1]
        
        if pd.isna(upper_val) or pd.isna(lower_val) or upper_val == lower_val:
            return 0.5
        
        # Position within bands (0 = lower, 1 = upper)
        position = (current - lower_val) / (upper_val - lower_val)
        return np.clip(position, 0, 1)
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD indicators"""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
        
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        macd_val = macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0.0
        signal_val = signal_line.iloc[-1] if not pd.isna(signal_line.iloc[-1]) else 0.0
        hist_val = histogram.iloc[-1] if not pd.isna(histogram.iloc[-1]) else 0.0
        
        # Normalize by current price to keep values reasonable
        current_price = prices.iloc[-1]
        if current_price > 0:
            macd_val /= current_price
            signal_val /= current_price
            hist_val /= current_price
        
        return macd_val, signal_val, hist_val
