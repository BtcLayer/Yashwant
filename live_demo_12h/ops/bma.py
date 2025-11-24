"""Bayesian Model Averaging helpers (rolling IC-based).

Lightweight utilities to compute rolling information coefficients (IC),
estimate per-model volatility, and derive BMA weights.
"""
from typing import Iterable, List
import numpy as np


def rolling_ic(pred_bps: Iterable[float], realized_bps: Iterable[float], window: int = 200) -> float:
    """Compute rolling IC (Pearson correlation) over the last `window` samples.

    Guards against degenerate windows:
    - require >1 finite samples after alignment
    - require non-zero std for both series
    Returns 0.0 when insufficient data or NaNs occur.
    """
    try:
        p = np.array(list(pred_bps)[-window:], dtype=float)
        r = np.array(list(realized_bps)[-window:], dtype=float)
        # Basic length checks
        min_needed = max(10, min(window, 200))
        if len(p) < min_needed or len(r) < min_needed:
            return 0.0
        # Align finite elements only
        mask = np.isfinite(p) & np.isfinite(r)
        if mask.sum() <= 1:
            return 0.0
        p2 = p[mask]
        r2 = r[mask]
        # Non-zero std guards
        sp = np.std(p2)
        sr = np.std(r2)
        if not np.isfinite(sp) or not np.isfinite(sr) or sp <= 0.0 or sr <= 0.0:
            return 0.0
        c = np.corrcoef(p2, r2)[0, 1]
        return 0.0 if (not np.isfinite(c)) else float(c)
    except Exception:
        return 0.0


def series_vol(x: Iterable[float], window: int = 200, eps: float = 1e-9) -> float:
    """Rolling standard deviation (bps units).

    Uses finite values only and falls back to 1.0 for degenerate/short windows.
    """
    try:
        arr = np.array(list(x)[-window:], dtype=float)
        if arr.size == 0:
            return 1.0
        # Keep only finite
        arr = arr[np.isfinite(arr)]
        if arr.size < max(10, min(window, 200)):
            return 1.0  # neutral vol to avoid division by zero
        v = float(np.std(arr))
        if not np.isfinite(v):
            return 1.0
        return max(v, eps)
    except Exception:
        return 1.0


def bma_weights(ic_vec: List[float], vol_vec: List[float], kappa: float = 8.0, eps: float = 1e-9) -> List[float]:
    """Compute BMA weights: w ∝ exp(kappa*IC)/vol.

    Args:
        ic_vec: per-model ICs
        vol_vec: per-model prediction std (bps)
        kappa: IC scaling factor
    Returns: list of weights summing to 1.0
    """
    try:
        ic = np.array(ic_vec, dtype=float)
        vol = np.array(vol_vec, dtype=float)
        z = np.exp(kappa * ic) / np.maximum(vol, eps)
        s = z.sum()
        if not np.isfinite(s) or s <= 0:
            n = max(1, len(ic))
            return [1.0 / n] * n
        return (z / s).astype(float).tolist()
    except Exception:
        n = max(1, len(ic_vec))
        return [1.0 / n] * n
