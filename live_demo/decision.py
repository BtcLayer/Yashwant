from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np


@dataclass
class Thresholds:
    S_MIN: float = 0.12
    M_MIN: float = 0.12
    CONF_MIN: float = 0.60
    ALPHA_MIN: float = 0.10
    # Tri-class gating thresholds (Ensemble 1.1) - Tuned Feb 16 for eligibility
    PNN_MIN: float = 0.10          # Min non-neutral probability (was 0.20)
    CONF_DIR_MIN: float = 0.40     # Min directional confidence given non-neutral (was 0.60)
    STRENGTH_MIN: float = 0.03     # Min signal strength (abs(p_up - p_down)) (was 0.07)
    flip_mood: bool = True
    flip_model: bool = True
    # Optional separate flip for BMA arm (defaults to same behavior as model when not set)
    flip_model_bma: bool = True
    # If true, allow trading on model signal alone when cohort mood is neutral (< M_MIN)
    allow_model_only_when_mood_neutral: bool = True
    # Exit-specific thresholds (lower than entry thresholds)
    exit_conf_min: float = 0.40
    exit_alpha_min: float = 0.30
    max_position_duration_bars: int = 288


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def gate_and_score(cohort_snapshot: Dict, model_out: Dict, th: Thresholds) -> Dict:
    """
    Inputs:
      - cohort_snapshot: {'pros','amateurs','mood'}
      - model_out: {'s_model', 'p_up','p_down','p_neutral'}
      - th: thresholds config
    Output:
      - {'dir': -1|0|1, 'alpha': [0,1], 'details': {...}}
    """
    s_pros = float(cohort_snapshot.get("pros", 0.0))
    s_am = float(cohort_snapshot.get("amateurs", 0.0))
    s_mood = float(cohort_snapshot.get("mood", 0.0))
    s_model = float(model_out.get("s_model", 0.0))

    if th.flip_mood:
        s_mood = -s_mood
    # Apply optional flip to model sign to match offline flip-map convention
    if th.flip_model:
        s_model = -s_model

    # Basic gating
    mood_ok = abs(s_mood) >= th.M_MIN
    model_ok = abs(s_model) >= th.S_MIN

    if not (mood_ok and model_ok):
        # Optional: allow model-only trading when mood is neutral and model is strong
        if (not mood_ok) and model_ok and th.allow_model_only_when_mood_neutral:
            conf_model = clamp(abs(s_model), 0.0, 1.0)
            if conf_model < th.CONF_MIN:
                return {
                    "dir": 0,
                    "alpha": 0.0,
                    "details": {
                        "s_pros": s_pros,
                        "s_amateurs": s_am,
                        "s_mood": s_mood,
                        "s_model": s_model,
                        "mood_ok": mood_ok,
                        "model_ok": model_ok,
                        "conf": conf_model,
                        "mode": "model_only_rejected",
                    },
                }
            alpha = clamp(conf_model, th.ALPHA_MIN, 1.0)
            direction = 1 if s_model > 0 else -1
            return {
                "dir": direction,
                "alpha": alpha,
                "details": {
                    "s_pros": s_pros,
                    "s_amateurs": s_am,
                    "s_mood": s_mood,
                    "s_model": s_model,
                    "conf": conf_model,
                    "mood_ok": mood_ok,
                    "model_ok": model_ok,
                    "mode": "model_only",
                },
            }
        return {
            "dir": 0,
            "alpha": 0.0,
            "details": {
                "s_pros": s_pros,
                "s_amateurs": s_am,
                "s_mood": s_mood,
                "s_model": s_model,
                "mood_ok": mood_ok,
                "model_ok": model_ok,
            },
        }

    # Consensus requirement
    sign_mood = 1 if s_mood > 0 else -1
    sign_model = 1 if s_model > 0 else -1
    consensus = sign_mood == sign_model
    if not consensus:
        return {
            "dir": 0,
            "alpha": 0.0,
            "details": {
                "s_pros": s_pros,
                "s_amateurs": s_am,
                "s_mood": s_mood,
                "s_model": s_model,
                "consensus": False,
            },
        }

    # Confidence: blend of magnitudes (cap to [0,1])
    conf = clamp(0.5 * (abs(s_mood) + abs(s_model)), 0.0, 1.0)
    if conf < th.CONF_MIN:
        return {
            "dir": 0,
            "alpha": 0.0,
            "details": {
                "s_pros": s_pros,
                "s_amateurs": s_am,
                "s_mood": s_mood,
                "s_model": s_model,
                "conf": conf,
            },
        }

    alpha = clamp(conf, th.ALPHA_MIN, 1.0)
    direction = 1 if s_model > 0 else -1

    return {
        "dir": direction,
        "alpha": alpha,
        "details": {
            "s_pros": s_pros,
            "s_amateurs": s_am,
            "s_mood": s_mood,
            "s_model": s_model,
            "conf": conf,
            "consensus": True,
        },
    }


# ---------------- Bandit integration utilities ----------------
def compute_signals_and_eligibility(
    cohort_snapshot: Dict,
    model_out: Dict,
    th: Thresholds,
) -> Tuple[
    Dict[str, float],
    Dict[str, bool],
    Tuple[float, float, float, float],
    Dict[str, float],
]:
    """Build per-arm signals and eligibility consistent with the notebook.

        Returns:
            signals: {
                'S_top','S_bot','S_mood',
                'S_model_meta','S_model_bma'
            }
            eligible: {'pros','amateurs','model_meta','model_bma'} (bools)
            side_eps_vec: (S_MIN, S_MIN, ALPHA_MIN, ALPHA_MIN)  # per-arm thresholds
            extras: {'conf_model','alpha_model'} for downstream alpha mapping (shared by model arms)
    """
    # Extract and apply flips
    s_top = float(cohort_snapshot.get('pros', 0.0))
    s_bot = float(cohort_snapshot.get('amateurs', 0.0))
    s_mood = float(cohort_snapshot.get('mood', 0.0))
    # Meta/stacked model score
    s_model_meta = float(model_out.get('s_model_meta', model_out.get('s_model', 0.0)))
    # BMA score; if absent, default to meta for back-compat (keeps arm eligible/consistent)
    s_model_bma = float(model_out.get('s_model_bma', model_out.get('s_model', 0.0)))
    if th.flip_mood:
        s_mood = -s_mood
    if th.flip_model:
        s_model_meta = -s_model_meta
    # Allow independent flip for BMA arm; default to same as model via dataclass default
    if th.flip_model_bma:
        s_model_bma = -s_model_bma

    # --- TRI-CLASS aware gating (p_non_neutral + conf_dir + strength)
    # Ensemble 1.1: Use tri-class thresholds from config
    PNN_MIN = th.PNN_MIN           # min non-neutral prob
    CONF_DIR_MIN = th.CONF_DIR_MIN  # directional confidence given non-neutral
    STRENGTH_MIN = th.STRENGTH_MIN  # signal strength
    EPS = 1e-12

    p_down = float(model_out.get("p_down", 0.0))
    p_up = float(model_out.get("p_up", 0.0))
    p_neutral = float(model_out.get("p_neutral", 1.0))

    p_dir = p_up + p_down
    p_non_neutral = max(0.0, 1.0 - p_neutral)
    
    # directional confidence conditional on being non-neutral; safe if p_dir==0
    if p_dir > 0:
        conf_dir = max(p_up, p_down) / (p_dir + EPS)
    else:
        conf_dir = 0.0

    strength = abs(p_up - p_down)  # same as |s_model|

    model_ok = (
        (p_non_neutral >= PNN_MIN)
        and (conf_dir >= CONF_DIR_MIN)
        and (strength >= STRENGTH_MIN)
    )

    signals = {
        'S_top': s_top,
        'S_bot': s_bot,
        'S_mood': s_mood,
        'S_model_meta': s_model_meta,
        'S_model_bma': s_model_bma,
    }
    eligible = {
        'pros': abs(s_top) >= th.S_MIN,
        'amateurs': abs(s_bot) >= th.S_MIN,
        'model_meta': model_ok,
        'model_bma': model_ok,
    }
    # Per-arm thresholds: pros, amateurs use S_MIN; model arms use ALPHA_MIN
    side_eps_vec = (th.S_MIN, th.S_MIN, th.ALPHA_MIN, th.ALPHA_MIN)
    
    extras = {
        'p_up': p_up, 
        'p_down': p_down, 
        'p_neutral': p_neutral,
        'p_non_neutral': p_non_neutral,
        'conf_dir': conf_dir,
        'strength': strength,
        # conf_model and alpha_model are used by decide_bandit for alpha sizing
        # conf_dir = directional confidence (max(p_up,p_down)/(p_up+p_down))
        # strength = signal magnitude (abs(p_up - p_down))
        'conf_model': conf_dir,
        'alpha_model': strength,
    }
    return signals, eligible, side_eps_vec, extras


def decide_bandit(
    signals: Dict[str, float],
    eligible: Dict[str, bool],
    side_eps_vec: Tuple[float, float, float, float],
    extras: Dict[str, float],
    bandit,
    *,
    epsilon: float = 0.0,
    model_optimism: float = 0.0,
) -> Dict:
    """Bandit-driven decision with 4 arms (mood removed).

    Arm order: ['pros','amateurs','model_meta','model_bma'] maps to
               ['S_top','S_bot','S_model_meta','S_model_bma'].
    """
    arm_order = ['pros', 'amateurs', 'model_meta', 'model_bma']
    sig_order = ['S_top', 'S_bot', 'S_model_meta', 'S_model_bma']
    emask = np.array([bool(eligible[a]) for a in arm_order], dtype=bool)
    # Fast exit: no arms eligible
    if not np.any(emask):
        return {
            "dir": 0,
            "alpha": 0.0,
            "details": {"chosen": None, "eligible": eligible, "signals": signals},
        }
    # Select arm with optional epsilon exploration and temporary optimism for model arm
    chosen_idx: int
    if float(epsilon) > 0.0 and np.random.rand() < float(epsilon):
        # Random explore among eligible arms
        choices = np.where(emask)[0]
        chosen_idx = int(np.random.choice(choices)) if choices.size > 0 else 0
    else:
        # Temporary optimism: bump model arm mean only for selection
        bumped = False
        try:
            if float(model_optimism) != 0.0 and hasattr(bandit, 'means'):
                mlen = len(getattr(bandit, 'means', []))
                # Apply optimism to model arms (indices 2 and 3 for 4-arm setup)
                if mlen >= 4:
                    bandit.means[2] = float(bandit.means[2]) + float(model_optimism)
                    bandit.means[3] = float(bandit.means[3]) + float(model_optimism)
                    bumped = True
            chosen_idx = int(bandit.select(emask))
        finally:
            if bumped and hasattr(bandit, 'means'):
                try:
                    mlen = len(getattr(bandit, 'means', []))
                    if mlen >= 4:
                        bandit.means[2] = float(bandit.means[2]) - float(model_optimism)
                        bandit.means[3] = float(bandit.means[3]) - float(model_optimism)
                except (AttributeError, TypeError, ValueError, IndexError):
                    pass
    chosen_arm = arm_order[chosen_idx] if 0 <= chosen_idx < len(arm_order) else arm_order[0]
    raw_val = float(signals[sig_order[chosen_idx]])
    th = float(side_eps_vec[chosen_idx])
    if abs(raw_val) < th:
        direction = 0
        alpha = 0.0
    else:
        direction = 1 if raw_val > 0 else -1
        if chosen_arm.startswith('model'):
            # Prefer model confidence; fallback to magnitude
            alpha_base = max(
                extras.get("conf_model", 0.0), extras.get("alpha_model", 0.0)
            )
        else:
            alpha_base = abs(raw_val)
        # use ALPHA_MIN (index 3) as floor for both model arms
        alpha = max(side_eps_vec[3], min(1.0, alpha_base))
    return {
        "dir": direction,
        "alpha": alpha,
        "details": {
            "chosen": chosen_arm,
            "raw_val": raw_val,
            "signals": signals,
            "eligible": eligible,
        },
    }


def decide(
    cohort_snapshot: Dict,
    model_out: Dict,
    th: Thresholds,
    bandit: object,
    *,
    epsilon: float = 0.0,
    model_optimism: float = 0.0,
) -> Dict:
    """Bandit-only decision: requires a bandit instance.

    Builds shared signals/eligibility and delegates to decide_bandit.
    """
    if bandit is None:
        raise RuntimeError("Bandit-only mode: 'bandit' must be provided to decide()")
    signals, eligible, side_eps_vec, extras = compute_signals_and_eligibility(
        cohort_snapshot, model_out, th
    )
    return decide_bandit(
        signals,
        eligible,
        side_eps_vec,
        extras,
        bandit,
        epsilon=epsilon,
        model_optimism=model_optimism,
    )


def compute_edge_after_costs(
    model_out: Dict,
    cost_bps: float,
    expected_move_bps: float = 50.0,
) -> Dict:
    """
    Compute expected edge after transaction costs.
    
    Ensemble 1.1 B2.3: Edge gating to filter unprofitable trades.
    
    Args:
        model_out: Model predictions containing p_up, p_down, p_neutral
        cost_bps: Transaction cost in basis points (roundtrip)
        expected_move_bps: Expected price move magnitude in basis points when directional
    
    Returns:
        Dict with:
            - edge_after_costs_bps: Net edge after costs (positive = profitable)
            - expected_return_bps: Expected return before costs
            - cost_bps: Transaction costs
            - direction: Recommended direction (-1, 0, 1)
            - should_trade: Boolean, True if edge_after_costs > 0
    """
    p_up = float(model_out.get('p_up', 0.0))
    p_down = float(model_out.get('p_down', 0.0))
    p_neutral = float(model_out.get('p_neutral', 1.0))
    
    # Expected return calculation
    # Assume symmetric moves: up move = +expected_move_bps, down move = -expected_move_bps
    # For a LONG position:
    #   - If market goes up: profit = +expected_move_bps
    #   - If market goes down: loss = -expected_move_bps
    #   - If neutral: profit = 0
    # Expected return = p_up * (+move) + p_down * (-move) + p_neutral * 0
    expected_return_long_bps = p_up * expected_move_bps - p_down * expected_move_bps
    
    # For a SHORT position (flip signs):
    expected_return_short_bps = p_down * expected_move_bps - p_up * expected_move_bps
    
    # Determine best direction
    if expected_return_long_bps > 0 and expected_return_long_bps >= expected_return_short_bps:
        direction = 1
        expected_return_bps = expected_return_long_bps
    elif expected_return_short_bps > 0:
        direction = -1
        expected_return_bps = expected_return_short_bps
    else:
        direction = 0
        expected_return_bps = 0.0
    
    # Edge after costs
    edge_after_costs_bps = expected_return_bps - cost_bps
    should_trade = edge_after_costs_bps > 0
    
    return {
        'edge_after_costs_bps': round(edge_after_costs_bps, 2),
        'expected_return_bps': round(expected_return_bps, 2),
        'cost_bps': round(cost_bps, 2),
        'direction': direction,
        'should_trade': should_trade,
        'p_up': p_up,
        'p_down': p_down,
        'p_neutral': p_neutral,
    }
