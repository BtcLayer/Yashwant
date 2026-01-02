from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np


@dataclass
class Thresholds:
    S_MIN: float = 0.12
    M_MIN: float = 0.12
    CONF_MIN: float = 0.60
    ALPHA_MIN: float = 0.10
    flip_mood: bool = True
    flip_model: bool = True
    # Optional separate flip for BMA arm (defaults to same behavior as model when not set)
    flip_model_bma: bool = True
    # If true, allow trading on model signal alone when cohort mood is neutral (<M_MIN)
    allow_model_only_when_mood_neutral: bool = True
    # If true, require consensus between mood and model (can block SELL trades)
    require_consensus: bool = True
