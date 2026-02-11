"""
Feature computer for 1h bot - matches training features exactly
"""
import numpy as np
import pandas as pd
from collections import deque

class H1FeatureComputer:
    """
    Computes features for 1h timeframe matching the training script:
    - ret_1, ret_12, ret_24: returns over 1, 12, 24 hours
    - volume_ratio: volume / 20-hour MA
    - volatility_12: 12-hour rolling std of returns
    - rsi: 14-period RSI
    - bb_position: position within 20-period Bollinger Bands
    - macd, macd_signal, macd_hist: MACD(12, 26, 9)
    - momentum_24: 24-hour price change
    - hl_range: (high - low) / close
    """
    
    def __init__(self, warmup_bars=200):
        self.warmup_bars = warmup_bars
        self.bars = deque(maxlen=warmup_bars)
        
    def add_bar(self, ts, open_price, high, low, close, volume):
        """Add new OHLCV bar to history"""
        self.bars.append({
            'ts': ts,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    def compute_features(self):
        """
        Compute all 15 features from bar history
        Returns dict with feature names matching training
        """
        if len(self.bars) < 30:  # Need minimum history
            return None
        
        # Convert to DataFrame for easier calculations
        df = pd.DataFrame(list(self.bars))
        
        # Returns
        df['ret_1'] = df['close'].pct_change(1)
        df['ret_12'] = df['close'].pct_change(12)
        df['ret_24'] = df['close'].pct_change(24)
        
        # Volume ratio
        df['volume_ma20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / (df['volume_ma20'] + 1e-8)
        
        # Volatility (12-hour rolling std)
        df['volatility_12'] = df['ret_1'].rolling(12).std()
        
        # RSI (14-period)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-8)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands (20-period, 2 std)
        sma = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        bb_upper = sma + (2 * std)
        bb_lower = sma - (2 * std)
        df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower + 1e-8)
        
        # MACD (12, 26, 9)
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Momentum (24-hour price change)
        df['momentum_24'] = df['close'] - df['close'].shift(24)
        
        # High-Low range
        df['hl_range'] = (df['high'] - df['low']) / (df['close'] + 1e-8)
        
        # Get last row (most recent)
        latest = df.iloc[-1]
        
        # Return features (cohort signals will be added separately)
        features = {
            'ret_1': latest['ret_1'] if not pd.isna(latest['ret_1']) else 0.0,
            'ret_12': latest['ret_12'] if not pd.isna(latest['ret_12']) else 0.0,
            'ret_24': latest['ret_24'] if not pd.isna(latest['ret_24']) else 0.0,
            'volume_ratio': latest['volume_ratio'] if not pd.isna(latest['volume_ratio']) else 1.0,
            'volatility_12': latest['volatility_12'] if not pd.isna(latest['volatility_12']) else 0.0,
            'rsi': latest['rsi'] if not pd.isna(latest['rsi']) else 50.0,
            'bb_position': latest['bb_position'] if not pd.isna(latest['bb_position']) else 0.5,
            'macd': latest['macd'] if not pd.isna(latest['macd']) else 0.0,
            'macd_signal': latest['macd_signal'] if not pd.isna(latest['macd_signal']) else 0.0,
            'macd_hist': latest['macd_hist'] if not pd.isna(latest['macd_hist']) else 0.0,
            'momentum_24': latest['momentum_24'] if not pd.isna(latest['momentum_24']) else 0.0,
            'hl_range': latest['hl_range'] if not pd.isna(latest['hl_range']) else 0.0,
        }
        
        return features
