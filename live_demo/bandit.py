from __future__ import annotations

import json
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


class SimpleThompsonBandit:
    """Online Gaussian Thompson Sampling over fixed arms.

    State per arm: counts, means, vars. Sampling: N(mean, sqrt(var)).
    Ineligibles are masked by -inf samples. Variances are floored for stability.
    """

    def __init__(
        self,
        n_arms: int,
        counts: Optional[np.ndarray] = None,
        means: Optional[np.ndarray] = None,
        variances: Optional[np.ndarray] = None,
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

    def select(self, eligible_mask: np.ndarray) -> int:
        em = np.asarray(eligible_mask, dtype=bool)
        if em.shape[0] != self.n_arms:
            raise ValueError("eligible_mask shape mismatch")
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
        a = int(arm)
        if a < 0 or a >= self.n_arms:
            return
        c_prev = self.counts[a]
        c = c_prev + 1.0
        mu_prev = self.means[a]
        # Online mean
        mu_new = mu_prev + (reward - mu_prev) / c
        # Welford-style variance update (population variance heuristic)
        delta = reward - mu_prev
        delta2 = reward - mu_new
        var_prev = self.variances[a]
        var_new = var_prev + (delta * delta2 - var_prev) / c
        self.counts[a] = c
        self.means[a] = mu_new
        self.variances[a] = max(float(var_new), 1e-6)

    # -------- Persistence helpers --------
    def to_state(self) -> dict:
        return {
            "n_arms": int(self.n_arms),
            "counts": self.counts.tolist(),
            "means": self.means.tolist(),
            "variances": self.variances.tolist(),
        }

    @classmethod
    def from_state(cls, d: dict) -> "SimpleThompsonBandit":
        return cls(
            n_arms=int(d.get("n_arms", 0)),
            counts=np.array(d.get("counts", []), dtype=float),
            means=np.array(d.get("means", []), dtype=float),
            variances=np.array(d.get("variances", d.get("vars", [])), dtype=float),
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
