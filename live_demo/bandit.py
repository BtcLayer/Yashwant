from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

try:
    # Prefer local JSONState for simple persistence
    from .state import JSONState  # type: ignore
except ImportError:  # pragma: no cover
    JSONState = None  # type: ignore

logger = logging.getLogger(__name__)


class SimpleThompsonBandit:
    """Online Gaussian Thompson Sampling over fixed arms.

    State per arm: counts, means, vars. Sampling: N(mean, sqrt(var)).
    Ineligibles are masked by -inf samples. Variances are floored for stability.
    
    Ensemble 1.1 enhancements:
    - Reward normalization (z-score with ±3σ clipping)
    - Freeze guards (drawdown-based protection)
    - Comprehensive debug logging
    """

    def __init__(
        self,
        n_arms: int,
        counts: Optional[np.ndarray] = None,
        means: Optional[np.ndarray] = None,
        variances: Optional[np.ndarray] = None,
        # Ensemble 1.1: Normalization statistics
        reward_history: Optional[list] = None,
        global_reward_mean: Optional[float] = None,
        global_reward_std: Optional[float] = None,
        # Ensemble 1.1: Freeze guards
        frozen: bool = False,
        freeze_reason: Optional[str] = None,
        cumulative_pnl: float = 0.0,
        peak_pnl: float = 0.0,
        drawdown_threshold: float = 0.10,  # 10% drawdown triggers freeze
    ) -> None:
        self.n_arms = int(n_arms)
        self.counts = (
            np.array(counts, dtype=float)
            if counts is not None
            else np.zeros(self.n_arms, dtype=float)
        )
        self.means = (
            np.array(means, dtype=float)
            if means is not None
            else np.zeros(self.n_arms, dtype=float)
        )
        self.variances = (
            np.array(variances, dtype=float)
            if variances is not None
            else np.ones(self.n_arms, dtype=float)
        )
        # Shape guards
        if self.counts.shape[0] != self.n_arms:
            self.counts = np.zeros(self.n_arms, dtype=float)
        if self.means.shape[0] != self.n_arms:
            self.means = np.zeros(self.n_arms, dtype=float)
        if self.variances.shape[0] != self.n_arms:
            self.variances = np.ones(self.n_arms, dtype=float)
        
        # Ensemble 1.1: Reward normalization tracking
        self.reward_history = reward_history if reward_history is not None else []
        self.global_reward_mean = global_reward_mean if global_reward_mean is not None else 0.0
        self.global_reward_std = global_reward_std if global_reward_std is not None else 1.0
        self.reward_history_max = 1000  # Rolling window size
        
        # Ensemble 1.1: Freeze guard state
        self.frozen = frozen
        self.freeze_reason = freeze_reason
        self.cumulative_pnl = cumulative_pnl
        self.peak_pnl = peak_pnl
        self.drawdown_threshold = drawdown_threshold
        self.freeze_recovery_threshold = 0.08  # Unfreeze at 8% drawdown

    def select(self, eligible_mask: np.ndarray) -> int:
        """Select arm via Thompson sampling.
        
        Ensemble 1.1: If frozen, log warning and return safe default.
        """
        em = np.asarray(eligible_mask, dtype=bool)
        if em.shape[0] != self.n_arms:
            raise ValueError("eligible_mask shape mismatch")
        
        # Ensemble 1.1: Check freeze state
        if self.frozen:
            logger.warning(
                f"[BANDIT_FROZEN] Cannot select arm - frozen due to: {self.freeze_reason}"
            )
            # Return first eligible arm as safe default
            if np.any(em):
                return int(np.argmax(em))
            return 0
        
        # Sample from current posterior (Gaussian heuristic)
        std = np.sqrt(np.maximum(self.variances, 1e-9))
        samples = np.random.normal(self.means, std)
        # Mask ineligible
        samples[~em] = -math.inf
        # If all are ineligible, return a safe default (0)
        if not np.any(em):
            return 0
        return int(np.argmax(samples))

    def update(self, arm: int, reward: float) -> None:
        """Update arm statistics with reward.
        
        Ensemble 1.1 enhancements:
        - Normalize rewards via z-score with ±3σ clipping
        - Track cumulative PnL and drawdown
        - Trigger freeze if drawdown exceeds threshold
        - Comprehensive debug logging
        """
        a = int(arm)
        if a < 0 or a >= self.n_arms:
            return
        
        reward_raw = float(reward)
        
        # Ensemble 1.1: Update global reward statistics
        self.reward_history.append(reward_raw)
        if len(self.reward_history) > self.reward_history_max:
            self.reward_history.pop(0)
        
        if len(self.reward_history) >= 2:
            self.global_reward_mean = float(np.mean(self.reward_history))
            self.global_reward_std = float(np.std(self.reward_history))
        
        # Ensemble 1.1: Normalize reward (z-score)
        if self.global_reward_std > 1e-9 and len(self.reward_history) >= 10:
            reward_normalized = (reward_raw - self.global_reward_mean) / self.global_reward_std
            
            # Clip to ±3σ to prevent extreme values from dominating
            clip_applied = False
            if reward_normalized > 3.0:
                reward_normalized = 3.0
                clip_applied = True
            elif reward_normalized < -3.0:
                reward_normalized = -3.0
                clip_applied = True
            
            # Log extreme rewards
            if clip_applied or abs(reward_normalized) > 2.5:
                logger.warning(
                    f"[BANDIT_REWARD] arm={a} reward_raw={reward_raw:.4f} "
                    f"reward_normalized={reward_normalized:.4f} clip_applied={clip_applied} "
                    f"global_mean={self.global_reward_mean:.4f} global_std={self.global_reward_std:.4f}"
                )
        else:
            # Use raw reward if insufficient history
            reward_normalized = reward_raw
        
        # Ensemble 1.1: Update drawdown tracking
        self.cumulative_pnl += reward_raw
        if self.cumulative_pnl > self.peak_pnl:
            self.peak_pnl = self.cumulative_pnl
        
        drawdown = 0.0
        if self.peak_pnl > 0:
            drawdown = (self.peak_pnl - self.cumulative_pnl) / self.peak_pnl
        
        # Ensemble 1.1: Check freeze conditions
        if not self.frozen and drawdown > self.drawdown_threshold:
            self.frozen = True
            self.freeze_reason = f"drawdown_exceeded_{self.drawdown_threshold*100:.0f}pct"
            logger.error(
                f"[BANDIT_FREEZE] Bandit frozen! drawdown={drawdown*100:.2f}% "
                f"threshold={self.drawdown_threshold*100:.0f}% "
                f"cumulative_pnl={self.cumulative_pnl:.2f} peak_pnl={self.peak_pnl:.2f}"
            )
        
        # Ensemble 1.1: Check unfreeze conditions (recovery)
        if self.frozen and drawdown < self.freeze_recovery_threshold:
            logger.info(
                f"[BANDIT_UNFREEZE] Bandit unfrozen - drawdown recovered to {drawdown*100:.2f}%"
            )
            self.frozen = False
            self.freeze_reason = None
        
        # Skip update if frozen (prevents further divergence)
        if self.frozen:
            logger.debug(f"[BANDIT_FROZEN] Skipping update for arm={a} - bandit is frozen")
            return
        
        # Standard Thompson sampling update with normalized reward
        c_prev = self.counts[a]
        c = c_prev + 1.0
        mu_prev = self.means[a]
        # Online mean
        mu_new = mu_prev + (reward_normalized - mu_prev) / c
        # Welford-style variance update (population variance heuristic)
        delta = reward_normalized - mu_prev
        delta2 = reward_normalized - mu_new
        var_prev = self.variances[a]
        var_new = var_prev + (delta * delta2 - var_prev) / c
        self.counts[a] = c
        self.means[a] = mu_new
        self.variances[a] = max(float(var_new), 1e-6)

    # -------- Persistence helpers --------
    def to_state(self) -> dict:
        """Serialize bandit state including Ensemble 1.1 enhancements."""
        return {
            "n_arms": int(self.n_arms),
            "counts": self.counts.tolist(),
            "means": self.means.tolist(),
            "variances": self.variances.tolist(),
            # Ensemble 1.1: Normalization state
            "reward_history": self.reward_history[-100:],  # Keep last 100 for persistence
            "global_reward_mean": float(self.global_reward_mean),
            "global_reward_std": float(self.global_reward_std),
            # Ensemble 1.1: Freeze state
            "frozen": bool(self.frozen),
            "freeze_reason": self.freeze_reason,
            "cumulative_pnl": float(self.cumulative_pnl),
            "peak_pnl": float(self.peak_pnl),
            "drawdown_threshold": float(self.drawdown_threshold),
        }

    @classmethod
    def from_state(cls, d: dict) -> "SimpleThompsonBandit":
        """Deserialize bandit state including Ensemble 1.1 enhancements."""
        return cls(
            n_arms=int(d.get("n_arms", 0)),
            counts=np.array(d.get("counts", []), dtype=float),
            means=np.array(d.get("means", []), dtype=float),
            variances=np.array(d.get("variances", d.get("vars", [])), dtype=float),
            # Ensemble 1.1: Normalization state
            reward_history=d.get("reward_history", []),
            global_reward_mean=d.get("global_reward_mean"),
            global_reward_std=d.get("global_reward_std"),
            # Ensemble 1.1: Freeze state
            frozen=d.get("frozen", False),
            freeze_reason=d.get("freeze_reason"),
            cumulative_pnl=d.get("cumulative_pnl", 0.0),
            peak_pnl=d.get("peak_pnl", 0.0),
            drawdown_threshold=d.get("drawdown_threshold", 0.10),
        )


@dataclass
class BanditStateIO:
    """Best-effort JSON persistence for bandit state.

    If JSONState is available, use it; otherwise write/read a standalone JSON.
    """

    path: str

    def load(self, n_arms: int) -> SimpleThompsonBandit:
        if JSONState is not None:
            try:
                st = JSONState(self.path)
                d = st.get("bandit_state")
                if isinstance(d, dict) and d.get("n_arms") == n_arms:
                    return SimpleThompsonBandit.from_state(d)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass
        # Fallback plain JSON
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                d = raw.get("bandit_state") if isinstance(raw, dict) else raw
                if isinstance(d, dict) and int(d.get("n_arms", -1)) == n_arms:
                    return SimpleThompsonBandit.from_state(d)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        return SimpleThompsonBandit(n_arms=n_arms)

    def save(self, bandit: SimpleThompsonBandit) -> None:
        d = {"bandit_state": bandit.to_state()}
        if JSONState is not None:
            try:
                st = JSONState(self.path)
                st.set("bandit_state", d["bandit_state"])
                return
            except (OSError, ValueError, TypeError):
                pass
        # Fallback plain JSON
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=2)
        except OSError:
            pass
