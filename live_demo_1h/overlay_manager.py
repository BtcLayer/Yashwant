"""
Overlay Manager for Multi-Timeframe Trading System

This module provides the core infrastructure for managing multiple timeframes
using rollup overlays from a base 5-minute timeframe.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Deque
from collections import deque
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")

@dataclass
class OverlayConfig:
    """Configuration for overlay timeframes"""
    base_timeframe: str = "5m"
    overlay_timeframes: List[str] = None
    rollup_windows: Dict[str, int] = None
    alignment_rules: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.overlay_timeframes is None:
            self.overlay_timeframes = ["15m", "1h"]
        if self.rollup_windows is None:
            self.rollup_windows = {"15m": 3, "1h": 12}  # 3x5m=15m, 12x5m=1h
        if self.alignment_rules is None:
            self.alignment_rules = {
                "require_5m_15m_agreement": True,
                "allow_1h_override": True,
                "neutral_1h_override": True
            }

@dataclass
class BarData:
    """Represents a single bar of market data"""
    timestamp: datetime
    bar_id: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    funding: float = 0.0
    spread_bps: float = 0.0
    rv_1h: float = 0.0

class OverlayManager:
    """Manages rollup overlays for multiple timeframes"""
    
    def __init__(self, config: OverlayConfig):
        self.config = config
        self.base_bars: Deque[BarData] = deque(maxlen=1000)
        self.overlay_bars: Dict[str, Deque[BarData]] = {
            timeframe: deque(maxlen=1000) 
            for timeframe in self.config.overlay_timeframes
        }
        self.last_bar_ids: Dict[str, int] = {
            timeframe: 0 for timeframe in ["5m"] + self.config.overlay_timeframes
        }
    
    def add_bar(self, bar: BarData) -> Dict[str, Optional[BarData]]:
        """Add a new 5m bar and generate overlay bars"""
        self.base_bars.append(bar)
        
        # Generate overlay bars
        overlay_bars = {}
        
        for timeframe in self.config.overlay_timeframes:
            window = self.config.rollup_windows[timeframe]
            
            # Check if we have enough bars for rollup
            if len(self.base_bars) >= window:
                # Get the last 'window' bars
                recent_bars = list(self.base_bars)[-window:]
                
                # Create rollup bar
                rollup_bar = self._create_rollup_bar(recent_bars, timeframe)
                
                if rollup_bar:
                    self.overlay_bars[timeframe].append(rollup_bar)
                    overlay_bars[timeframe] = rollup_bar
                    
                    # Update bar ID
                    self.last_bar_ids[timeframe] += 1
                    rollup_bar.bar_id = self.last_bar_ids[timeframe]
        
        return overlay_bars
    
    def _create_rollup_bar(self, bars: List[BarData], timeframe: str) -> Optional[BarData]:
        """Create a rollup bar from multiple base bars"""
        if not bars:
            return None
        
        # Calculate rollup values
        open_price = bars[0].open
        close_price = bars[-1].close
        high_price = max(bar.high for bar in bars)
        low_price = min(bar.low for bar in bars)
        # Coerce any None values to 0.0 to avoid arithmetic errors
        def _nz(x, default=0.0):
            try:
                return default if x is None else float(x)
            except (TypeError, ValueError):
                return default
        total_volume = float(sum(_nz(bar.volume) for bar in bars))
        avg_funding = float(np.mean([_nz(bar.funding) for bar in bars]))
        avg_spread = float(np.mean([_nz(bar.spread_bps) for bar in bars]))
        avg_rv = float(np.mean([_nz(bar.rv_1h) for bar in bars]))
        
        # Use the timestamp of the last bar
        timestamp = bars[-1].timestamp
        
        return BarData(
            timestamp=timestamp,
            bar_id=0,  # Will be set by caller
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=total_volume,
            funding=avg_funding,
            spread_bps=avg_spread,
            rv_1h=avg_rv
        )
    
    def get_latest_bars(self, timeframe: str) -> List[BarData]:
        """Get the latest bars for a specific timeframe"""
        if timeframe == "5m":
            return list(self.base_bars)
        elif timeframe in self.overlay_bars:
            return list(self.overlay_bars[timeframe])
        else:
            return []
    
    def get_bar_count(self, timeframe: str) -> int:
        """Get the number of bars available for a timeframe"""
        if timeframe == "5m":
            return len(self.base_bars)
        elif timeframe in self.overlay_bars:
            return len(self.overlay_bars[timeframe])
        else:
            return 0
    
    def get_timeframe_weights(self) -> Dict[str, float]:
        """Get default weights for different timeframes"""
        return {
            "5m": 0.5,
            "15m": 0.3,
            "1h": 0.2
        }
    
    def is_timeframe_ready(self, timeframe: str, min_bars: int = 50) -> bool:
        """Check if a timeframe has enough bars for analysis"""
        return self.get_bar_count(timeframe) >= min_bars
