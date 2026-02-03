from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict
import numpy as np
import time


@dataclass
class CohortState:
    window: int = 12  # 1h at 5m bars
    adv20: float = 1.0
    pros: float = 0.0
    amateurs: float = 0.0
    mood: float = 0.0
    _pros_q: Deque[float] = None
    _am_q: Deque[float] = None
    _mood_q: Deque[float] = None
    # Feature flags for Phase 2 fixes
    use_adv20_normalization: bool = True  # Set to False to revert to raw accumulation
    use_signal_decay: bool = True  # Set to False to disable exponential decay
    timeframe_hours: float = 1.0  # Timeframe in hours (1.0 for 1h, 0.083 for 5m)
    signal_half_life_minutes: float = 10.0  # Half-life for exponential decay
    
    # Per-bar accumulation (FIX for S_top=0 bug)
    bar_interval_ms: int = 300000  # 5m = 300000ms, 1h = 3600000ms
    current_bar_ts: int = 0  # Current bar timestamp
    current_pros_accum: float = 0.0  # Accumulate pros fills for current bar
    current_amateurs_accum: float = 0.0  # Accumulate amateurs fills
    current_mood_accum: float = 0.0  # Accumulate mood fills
    max_buffer_bars: int = 3  # Maximum bars to buffer (handles late fills)

    def __post_init__(self):
        self._pros_q = deque(maxlen=self.window)
        self._am_q = deque(maxlen=self.window)
        self._mood_q = deque(maxlen=self.window)

    def update_from_fill(self, fill: Dict, weights: Dict[str, float]):
        """Update rolling cohort signals based on a single fill.
        
        PER-BAR ACCUMULATION FIX:
        - Accumulates fills within same bar before flushing to deque
        - Prevents mood fills from pushing out cohort fills
        - Each deque entry = 1 bar's total, not individual fills
        
        fill: {ts, address, coin, side('A'/'B' or 'buy'/'sell'), price, size}
        weights: {'pros': rho_p, 'amateurs': rho_a, 'mood': rho_m}
        """
        # Extract fill timestamp and round to bar boundary
        fill_ts = int(fill.get('ts', time.time() * 1000))
        fill_bar_ts = (fill_ts // self.bar_interval_ms) * self.bar_interval_ms
        
        # Detect bar boundary - flush previous bar if new bar started
        if self.current_bar_ts == 0:
            # First fill ever - initialize current bar
            self.current_bar_ts = fill_bar_ts
        elif fill_bar_ts > self.current_bar_ts:
            # New bar started - flush previous bar to deque
            self._flush_current_bar()
            self.current_bar_ts = fill_bar_ts
        
        # Compute fill impact
        side = fill.get("side", "").lower()
        signed = 0.0
        if side in ("buy", "a", "bid"):
            signed = 1.0
        elif side in ("sell", "b", "ask"):
            signed = -1.0
        
        size = float(fill.get("size", 0.0))
        
        # Apply normalization if enabled
        if self.use_adv20_normalization and fill.get('pre_normalized') != True:
            adv_timeframe = self.adv20 / (24.0 / self.timeframe_hours)
            impact = (signed * size) / max(1e-6, adv_timeframe)
        else:
            impact = signed * size
        
        # Apply decay if enabled
        decay_weight = 1.0
        if self.use_signal_decay and 'ts' in fill:
            try:
                current_ts = time.time() * 1000
                fill_ts = int(fill.get('ts', current_ts))
                age_ms = max(0, current_ts - fill_ts)
                half_life_ms = self.signal_half_life_minutes * 60 * 1000
                decay_weight = np.exp(-age_ms / half_life_ms) if half_life_ms > 0 else 1.0
            except Exception:
                decay_weight = 1.0
        
        final_impact = impact * decay_weight
        
        # Accumulate in current bar (NOT appending to deque yet)
        self.current_pros_accum += final_impact * weights.get("pros", 0.0)
        self.current_amateurs_accum += final_impact * weights.get("amateurs", 0.0)
        self.current_mood_accum += final_impact * weights.get("mood", 0.0)
        
        # Update signals immediately (includes current bar + deque)
        self._update_signals()
    
    def _flush_current_bar(self):
        """Flush current bar's accumulated fills to deque."""
        self._pros_q.append(self.current_pros_accum)
        self._am_q.append(self.current_amateurs_accum)
        self._mood_q.append(self.current_mood_accum)
        
        # Reset accumulators for new bar
        self.current_pros_accum = 0.0
        self.current_amateurs_accum = 0.0
        self.current_mood_accum = 0.0
    
    def _update_signals(self):
        """Compute signals from deque + current bar accumulator."""
        # Sum from flushed bars in deque
        pros_sum = sum(self._pros_q)
        am_sum = sum(self._am_q)
        mood_sum = sum(self._mood_q)
        count = len(self._pros_q)
        
        # Add current bar (not yet flushed)
        if self.current_bar_ts > 0:
            pros_sum += self.current_pros_accum
            am_sum += self.current_amateurs_accum
            mood_sum += self.current_mood_accum
            count += 1
        
        # Compute averages
        self.pros = pros_sum / max(1, count)
        self.amateurs = am_sum / max(1, count)
        self.mood = mood_sum / max(1, count)

    def set_adv20(self, adv20: float):
        self.adv20 = max(adv20, 1e-6)

    def snapshot(self) -> Dict:
        return {
            "pros": self.pros,
            "amateurs": self.amateurs,
            "mood": self.mood,
        }
