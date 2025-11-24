from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict


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

    def __post_init__(self):
        self._pros_q = deque(maxlen=self.window)
        self._am_q = deque(maxlen=self.window)
        self._mood_q = deque(maxlen=self.window)

    def update_from_fill(self, fill: Dict, weights: Dict[str, float]):
        """Update rolling cohort signals based on a single fill.
        fill: {ts, address, coin, side('A'/'B' or 'buy'/'sell'), price, size}
        weights: {'pros': rho_p, 'amateurs': rho_a, 'mood': rho_m}
        """
        side = fill.get("side", "").lower()
        signed = 0.0
        if side in ("buy", "a", "bid"):
            signed = 1.0
        elif side in ("sell", "b", "ask"):
            signed = -1.0
        impact = signed * float(fill.get("size", 0.0)) / max(1e-9, self.adv20)
        # Update deques
        self._pros_q.append(impact * weights.get("pros", 1.0))
        self._am_q.append(impact * weights.get("amateurs", 1.0))
        self._mood_q.append(impact * weights.get("mood", 1.0))
        # Recompute smoothed scores
        self.pros = sum(self._pros_q) / max(1, len(self._pros_q))
        self.amateurs = sum(self._am_q) / max(1, len(self._am_q))
        self.mood = sum(self._mood_q) / max(1, len(self._mood_q))

    def set_adv20(self, adv20: float):
        self.adv20 = max(adv20, 1e-6)

    def snapshot(self) -> Dict:
        return {
            "pros": self.pros,
            "amateurs": self.amateurs,
            "mood": self.mood,
        }
