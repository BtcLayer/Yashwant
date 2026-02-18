#!/usr/bin/env python3
"""
Train calibrators for model predictions using historical signal-outcome data.

Ensemble 1.1 - B2.1: Calibration Pipeline

This script:
1. Loads historical signals with realized outcomes (from assess_calibration_data.py)
2. Trains isotonic regression calibrator (best for large datasets)
3. Trains Platt scaling calibrator (sigmoid-based, more conservative)
4. Computes calibration quality metrics (ECE, MCE)
5. Saves calibrators to .pkl files for runtime use

Usage:
    python scripts/calibrate_model.py --logs-root paper_trading_outputs --timeframe 5m
    python scripts/calibrate_model.py --logs-root paper_trading_outputs --timeframe 1h
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple
import numpy as np
import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# Import calibration wrapper from shared module
from live_demo.calibration_utils import CalibrationWrapper

# Import data loading functions
from scripts.assess_calibration_data import (
    scan_logs_for_signals_and_outcomes,
    SignalOutcome
)


class DummyClassifier:
    """Dummy classifier wrapper for calibration.
    
    Since we already have model predictions (probabilities), we don't need
    to re-train the base model. This wrapper just passes through predictions.
    """
    def __init__(self):
        self.classes_ = np.array([0, 1, 2])  # down, neutral, up
        self._estimator_type = "classifier"  # Tell sklearn this is a classifier
    
    def predict_proba(self, X):
        """X is already probabilities [p_down, p_neutral, p_up]"""
        return np.array(X)
    
    def fit(self, X, y):
        return self


def generate_synthetic_calibration_data(n_samples: int = 500) -> Tuple[np.ndarray, np.ndarray]:
    """Generate synthetic calibration data for testing.
    
    Creates realistic-looking model predictions with known outcomes.
    Useful for testing calibration infrastructure when production data unavailable.
    """
    np.random.seed(42)
    
    X = []
    y = []
    
    for _ in range(n_samples):
        # Simulate overconfident model (common in practice)
        true_class = np.random.choice([0, 1, 2], p=[0.3, 0.4, 0.3])
        
        # Model is overconfident - assigns too much probability to predicted class
        if true_class == 0:  # Actually down
            # Model predicts down but is overconfident
            p_down = np.random.uniform(0.5, 0.9)
            p_up = np.random.uniform(0.05, (1-p_down)*0.5)
            p_neutral = 1.0 - p_down - p_up
        elif true_class == 2:  # Actually up
            # Model predicts up but is overconfident
            p_up = np.random.uniform(0.5, 0.9)
            p_down = np.random.uniform(0.05, (1-p_up)*0.5)
            p_neutral = 1.0 - p_up - p_down
        else:  # Actually neutral
            # Model unsure
            p_neutral = np.random.uniform(0.6, 0.9)
            p_down = np.random.uniform(0.05, (1-p_neutral)*0.5)
            p_up = 1.0 - p_neutral - p_down
        
        X.append([p_down, p_neutral, p_up])
        y.append(true_class)
    
    return np.array(X), np.array(y)


def load_calibration_data(logs_root: Path, min_samples: int = 100, use_synthetic: bool = False) -> Tuple[np.ndarray, np.ndarray, List[SignalOutcome]]:
    """Load historical signals with outcomes for calibration.
    
    Returns:
        X: (N, 3) array of [p_down, p_neutral, p_up] probabilities
        y: (N,) array of actual outcomes (0=down, 1=neutral, 2=up)
        samples: List of SignalOutcome objects for analysis
    """
    print(f"\n[1/5] Loading calibration data")
    
    if use_synthetic:
        print(f"   Using synthetic data (n={min_samples})")
        X, y = generate_synthetic_calibration_data(min_samples)
        return X, y, []
    
    print(f"   Scanning logs from {logs_root}")
    
    # Scan logs for signals and outcomes
    outcomes = scan_logs_for_signals_and_outcomes(logs_root)
    
    if len(outcomes) == 0:
        raise ValueError(f"No signals found in {logs_root}")
    
    print(f"   Found {len(outcomes)} total signals")
    
    # Filter to signals with realized outcomes
    labeled = [o for o in outcomes if o.realized_pnl is not None]
    
    if len(labeled) < min_samples:
        print(f"   [WARNING] Only {len(labeled)} labeled samples found (need {min_samples})")
        print(f"   [INFO] Signal-outcome matching may be failing. Common causes:")
        print(f"          - Signals and P&L logs use different ID schemes")
        print(f"          - Timestamps don't align (check timezone handling)")
        print(f"          - P&L data structure changed")
        print(f"\n   [SOLUTION] Use --synthetic flag to test calibration with synthetic data")
        raise ValueError(
            f"Insufficient labeled data: {len(labeled)} samples "
            f"(minimum {min_samples} required for calibration)"
        )
    
    print(f"   Found {len(labeled)} signals with realized outcomes")
    
    # Extract features (probabilities) and labels (outcomes)
    X = []
    y = []
    
    for outcome in labeled:
        # Get tri-class probabilities from signal
        # Note: We need to reconstruct p_down, p_neutral, p_up from available fields
        # From assess_calibration_data.py, we have confidence, p_non_neutral, conf_dir
        # But we need the original p_up, p_down, p_neutral
        
        # For now, we'll use a simplified approach:
        # If we have the outcome direction and confidence, we can infer probabilities
        # This is a placeholder - ideally we'd store raw probabilities in logs
        
        # Simplified tri-class reconstruction (TODO: enhance with raw probabilities)
        if outcome.direction == 1:  # Up signal
            p_up = outcome.confidence if outcome.confidence else 0.5
            p_down = (1.0 - p_up) * 0.2  # Assume small down prob
            p_neutral = 1.0 - p_up - p_down
        elif outcome.direction == -1:  # Down signal
            p_down = outcome.confidence if outcome.confidence else 0.5
            p_up = (1.0 - p_down) * 0.2
            p_neutral = 1.0 - p_up - p_down
        else:  # Neutral signal
            p_neutral = 0.6
            p_up = 0.2
            p_down = 0.2
        
        X.append([p_down, p_neutral, p_up])
        
        # Convert realized outcome to class label
        # win=True means profitable trade in predicted direction
        if outcome.win is True:
            # Profitable in direction - map to actual outcome
            if outcome.direction == 1:
                y.append(2)  # up
            elif outcome.direction == -1:
                y.append(0)  # down
            else:
                y.append(1)  # neutral
        elif outcome.win is False:
            # Losing trade - opposite of prediction
            if outcome.direction == 1:
                y.append(0)  # predicted up, got down
            elif outcome.direction == -1:
                y.append(2)  # predicted down, got up
            else:
                y.append(1)  # neutral
        else:
            # Unknown outcome - treat as neutral
            y.append(1)
    
    X = np.array(X)
    y = np.array(y)
    
    print(f"   Prepared {len(X)} training samples")
    print(f"   Class distribution: down={np.sum(y==0)}, neutral={np.sum(y==1)}, up={np.sum(y==2)}")
    
    return X, y, labeled


def compute_calibration_metrics(y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10) -> dict:
    """Compute Expected Calibration Error (ECE) and Maximum Calibration Error (MCE).
    
    Args:
        y_true: True class labels (0, 1, 2)
        y_proba: Predicted probabilities (N, 3)
        n_bins: Number of bins for calibration curve
    
    Returns:
        Dictionary with ECE, MCE, and bin statistics
    """
    n_samples = len(y_true)
    
    # Convert to predicted class and max confidence
    y_pred = np.argmax(y_proba, axis=1)
    confidences = np.max(y_proba, axis=1)
    accuracies = (y_pred == y_true).astype(float)
    
    # Bin confidences
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(confidences, bins[:-1]) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    
    # Compute ECE and MCE
    ece = 0.0
    mce = 0.0
    bin_stats = []
    
    for i in range(n_bins):
        mask = bin_indices == i
        if np.sum(mask) > 0:
            bin_conf = np.mean(confidences[mask])
            bin_acc = np.mean(accuracies[mask])
            bin_size = np.sum(mask)
            
            bin_error = abs(bin_conf - bin_acc)
            ece += (bin_size / n_samples) * bin_error
            mce = max(mce, bin_error)
            
            bin_stats.append({
                'bin': i,
                'conf_range': (bins[i], bins[i+1]),
                'avg_conf': bin_conf,
                'avg_acc': bin_acc,
                'count': int(bin_size),
                'error': bin_error
            })
    
    return {
        'ece': ece,
        'mce': mce,
        'accuracy': np.mean(accuracies),
        'bin_stats': bin_stats
    }


def train_isotonic_calibrator(X: np.ndarray, y: np.ndarray) -> CalibratedClassifierCV:
    """Train isotonic regression calibrator.
    
    Isotonic regression learns a monotonic mapping from predicted to calibrated
    probabilities. Best for larger datasets (500+ samples).
    """
    print("\n[2/5] Training isotonic regression calibrator")
    
    # Create dummy classifier that just passes through probabilities
    estimator = DummyClassifier()
    
    # Wrap in CalibratedClassifierCV with isotonic method
    calibrator = CalibratedClassifierCV(
        estimator=estimator,
        method='isotonic',
        cv='prefit'  # Don't split data, use all for calibration
    )
    
    # Fit calibrator
    calibrator.fit(X, y)
    
    print("   Isotonic calibrator trained")
    
    return calibrator


def train_platt_calibrator(X: np.ndarray, y: np.ndarray) -> CalibratedClassifierCV:
    """Train Platt scaling calibrator.
    
    Platt scaling applies a sigmoid function (logistic regression) to
    calibrate probabilities. More conservative, works with smaller datasets.
    """
    print("\n[3/5] Training Platt scaling calibrator")
    
    # Create dummy classifier
    estimator = DummyClassifier()
    
    # Wrap in CalibratedClassifierCV with sigmoid method
    calibrator = CalibratedClassifierCV(
        estimator=estimator,
        method='sigmoid',
        cv='prefit'
    )
    
    # Fit calibrator
    calibrator.fit(X, y)
    
    print("   Platt scaling calibrator trained")
    
    return calibrator


def evaluate_calibrator(calibrator, X: np.ndarray, y: np.ndarray, name: str):
    """Evaluate calibrator quality."""
    print(f"\n[4/5] Evaluating {name} calibrator")
    
    # Get calibrated predictions
    y_proba_cal = calibrator.predict_proba(X)
    
    # Compute metrics
    metrics = compute_calibration_metrics(y, y_proba_cal)
    
    print(f"   ECE (Expected Calibration Error): {metrics['ece']:.4f}")
    print(f"   MCE (Maximum Calibration Error): {metrics['mce']:.4f}")
    print(f"   Accuracy: {metrics['accuracy']:.4f}")
    
    # Show bin statistics
    print(f"\n   Calibration bins:")
    print(f"   {'Confidence Range':<20} {'Avg Conf':<10} {'Avg Acc':<10} {'Count':<10} {'Error':<10}")
    print(f"   {'-'*70}")
    for stat in metrics['bin_stats']:
        conf_range = f"{stat['conf_range'][0]:.2f}-{stat['conf_range'][1]:.2f}"
        print(f"   {conf_range:<20} {stat['avg_conf']:<10.3f} {stat['avg_acc']:<10.3f} "
              f"{stat['count']:<10} {stat['error']:<10.4f}")
    
    return metrics


def save_calibrator(calibrator, output_path: Path, name: str):
    """Save trained calibrator to disk.
    
    Extracts just the calibration transformers to avoid DummyClassifier
    pickling issues. Creates a portable CalibrationWrapper instead.
    """
    print(f"\n[5/5] Saving {name} calibrator to {output_path}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract ONLY the calibration transformers from CalibratedClassifierCV
    # calibrator.calibrated_classifiers_ is a list of _CalibratedClassifier objects
    # Each has a .calibrators attribute which is a list of per-class transformers
    pure_transformers = []
    for calib_clf in calibrator.calibrated_classifiers_:
        # Extract just the .calibrators list (no base estimator reference)
        # Store as dict to avoid sklearn internal class dependencies
        pure_transformers.append({
            'calibrators': calib_clf.calibrators,
            'classes': calib_clf.classes
        })
    
    # Create portable wrapper with just the transformers
    wrapper = CalibrationWrapper(
        calibrated_classifiers=pure_transformers,
        classes=calibrator.classes_
    )
    
    # Save with joblib
    joblib.dump(wrapper, output_path)
    
    print(f"   Calibrator saved ({output_path.stat().st_size / 1024:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--logs-root',
        type=Path,
        default=Path('paper_trading_outputs'),
        help='Root directory containing trading logs'
    )
    parser.add_argument(
        '--timeframe',
        default='5m',
        choices=['5m', '1h', '12h', '24h'],
        help='Timeframe to calibrate (default: 5m)'
    )
    parser.add_argument(
        '--min-samples',
        type=int,
        default=100,
        help='Minimum samples required for calibration (default: 100)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('live_demo/models'),
        help='Output directory for calibrator files'
    )
    parser.add_argument(
        '--synthetic',
        action='store_true',
        help='Use synthetic data for testing (when production data unavailable)'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("MODEL CALIBRATION - ENSEMBLE 1.1 B2.1")
    print("="*70)
    print(f"\nTimeframe: {args.timeframe}")
    print(f"Logs root: {args.logs_root}")
    print(f"Min samples: {args.min_samples}")
    print(f"Mode: {'SYNTHETIC (testing)' if args.synthetic else 'PRODUCTION (real data)'}")
    
    try:
        # Load data
        X, y, samples = load_calibration_data(args.logs_root, args.min_samples, use_synthetic=args.synthetic)
        
        # Train isotonic calibrator
        calibrator_isotonic = train_isotonic_calibrator(X, y)
        metrics_isotonic = evaluate_calibrator(calibrator_isotonic, X, y, "Isotonic")
        
        # Train Platt calibrator
        calibrator_platt = train_platt_calibrator(X, y)
        metrics_platt = evaluate_calibrator(calibrator_platt, X, y, "Platt")
        
        # Save calibrators
        output_isotonic = args.output_dir / f"calibrator_{args.timeframe}_isotonic.pkl"
        output_platt = args.output_dir / f"calibrator_{args.timeframe}_platt.pkl"
        
        save_calibrator(calibrator_isotonic, output_isotonic, "Isotonic")
        save_calibrator(calibrator_platt, output_platt, "Platt")
        
        # Summary
        print("\n" + "="*70)
        print("CALIBRATION SUMMARY")
        print("="*70)
        print(f"\nDataset:")
        print(f"  Total samples: {len(X)}")
        print(f"  Class distribution: down={np.sum(y==0)}, neutral={np.sum(y==1)}, up={np.sum(y==2)}")
        
        print(f"\nIsotonic Regression:")
        print(f"  ECE: {metrics_isotonic['ece']:.4f} {'[GOOD]' if metrics_isotonic['ece'] < 0.05 else '[NEEDS IMPROVEMENT]'}")
        print(f"  MCE: {metrics_isotonic['mce']:.4f}")
        print(f"  Accuracy: {metrics_isotonic['accuracy']:.4f}")
        print(f"  Saved: {output_isotonic}")
        
        print(f"\nPlatt Scaling:")
        print(f"  ECE: {metrics_platt['ece']:.4f} {'[GOOD]' if metrics_platt['ece'] < 0.05 else '[NEEDS IMPROVEMENT]'}")
        print(f"  MCE: {metrics_platt['mce']:.4f}")
        print(f"  Accuracy: {metrics_platt['accuracy']:.4f}")
        print(f"  Saved: {output_platt}")
        
        print(f"\nRecommendation:")
        if metrics_isotonic['ece'] < metrics_platt['ece']:
            print(f"  [OK] Use isotonic calibrator (lower ECE: {metrics_isotonic['ece']:.4f} vs {metrics_platt['ece']:.4f})")
            print(f"  Update manifest: calibrator_path = '{output_isotonic}'")
        else:
            print(f"  [OK] Use Platt calibrator (lower ECE: {metrics_platt['ece']:.4f} vs {metrics_isotonic['ece']:.4f})")
            print(f"  Update manifest: calibrator_path = '{output_platt}'")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n[ERROR] Calibration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
