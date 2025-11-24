import sys
import json
from dataclasses import dataclass

# Import decision utilities from live_demo
try:
    from live_demo.decision import Thresholds, compute_signals_and_eligibility, decide_bandit
except ImportError:
    from ..decision import Thresholds, compute_signals_and_eligibility, decide_bandit  # type: ignore


@dataclass
class DummyBandit:
    means: list
    variances: list
    counts: list
    def select(self, eligible_mask):
        # Select the highest mean among eligible arms
        idxs = [i for i, e in enumerate(list(eligible_mask)) if e]
        if not idxs:
            return 0
        best = max(idxs, key=lambda i: self.means[i])
        return int(best)


def scenario(name: str, chosen_arm_index: int):
    """Run a deterministic scenario and assert expected arm name mapping."""
    # Cohort snapshot
    cohort = {
        'pros': 0.20,
        'amateurs': -0.05,
        'mood': 0.18,  # mood tracked for overlays but not a bandit arm
    }
    # Model outputs: meta slightly smaller, BMA slightly larger
    # Probabilities imply conf and alpha; both >= thresholds
    model_out = {
        'p_down': 0.10,
        'p_neutral': 0.20,
        'p_up': 0.70,
        's_model_meta': 0.22,
        's_model_bma': 0.28,
        # Fallback single signal retained (not used by bandit)
        's_model': 0.22,
    }
    th = Thresholds(
        S_MIN=0.10, M_MIN=0.10, CONF_MIN=0.55, ALPHA_MIN=0.05,
        flip_mood=True, flip_model=True, flip_model_bma=True,
    )
    signals, eligible, side_eps_vec, extras = compute_signals_and_eligibility(cohort, model_out, th)

    # Build a dummy bandit with means configured to force the chosen arm
    means = [0.1, 0.05, 0.10, 0.20]  # 4 arms: pros, amateurs, model_meta, model_bma
    # Override the targeted index to be the largest
    for i in range(len(means)):
        means[i] = -1.0
    means[chosen_arm_index] = 1.0
    bandit = DummyBandit(means=means, variances=[1e-6]*4, counts=[1]*4)

    decision = decide_bandit(signals, eligible, side_eps_vec, extras, bandit, epsilon=0.0, model_optimism=0.0)
    out = {
        'name': name,
        'chosen': decision['details']['chosen'],
        'dir': decision['dir'],
        'alpha': round(float(decision['alpha']), 4),
        'raw_val': round(float(decision['details']['raw_val']), 4),
        'eligible': eligible,
        'signals': signals,
    }
    print(json.dumps(out, indent=2))
    return decision


def main():
    # Indices mapping (4 arms): ['pros', 'amateurs', 'model_meta', 'model_bma']
    # 1) Force model_meta (index 2)
    d1 = scenario('meta_arm', 2)
    # 2) Force model_bma (index 3)
    d2 = scenario('bma_arm', 3)

    ok = True
    ok &= d1['details']['chosen'] == 'model_meta'
    ok &= d2['details']['chosen'] == 'model_bma'
    if not ok:
        print('DRY-RUN: FAIL (arm names mismatch)')
        sys.exit(2)
    print('DRY-RUN: PASS')


if __name__ == '__main__':
    main()
