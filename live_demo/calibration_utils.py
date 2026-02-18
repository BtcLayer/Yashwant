"""Calibration utilities for MetaStackerBandit.

Provides portable calibration wrappers that can be pickled and loaded
across different modules without class dependency issues.
"""

import numpy as np
from scipy.special import expit


class CalibrationWrapper:
    """Portable calibrator wrapper for sklearn CalibratedClassifierCV.
    
    Extracts just the calibration transformers to avoid base estimator
    pickling dependencies. Can be loaded in any module without issues.
    
    Usage:
        # After training CalibratedClassifierCV
        wrapper = CalibrationWrapper(
            calibrated_classifiers=calibrator.calibrated_classifiers_,
            classes=calibrator.classes_
        )
        joblib.dump(wrapper, 'calibrator.pkl')
        
        # Later, in different module
        wrapper = joblib.load('calibrator.pkl')
        calibrated_probs = wrapper.predict_proba(raw_probs)
    """
    
    def __init__(self, calibrated_classifiers, classes):
        """
        Args:
            calibrated_classifiers: List of (estimator, transformer) tuples from sklearn
            classes: np.array of class labels [0, 1, 2] for down/neutral/up
        """
        self.calibrated_classifiers_ = calibrated_classifiers
        self.classes_ = classes
    
    def predict_proba(self, X):
        """Apply calibration to input probabilities.
        
        Args:
            X: (N, 3) array of [p_down, p_neutral, p_up] probabilities
        
        Returns:
            (N, 3) array of calibrated probabilities summing to 1
        """
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        # Apply each calibration transformer and average
        # (CalibratedClassifierCV can have multiple transformers from CV folds)
        calibrated_probas = [
            self._predict_proba_single(X, calibrated_classifier)
            for calibrated_classifier in self.calibrated_classifiers_
        ]
        
        return np.mean(calibrated_probas, axis=0)
    
    def _predict_proba_single(self, X, calibrated_classifier):
        """Apply single calibration transformer.
        
        Args:
            X: (N, 3) array of raw probabilities
            calibrated_classifier: Dict with 'calibrators' and 'classes' keys
        
        Returns:
            (N, 3) array of calibrated probabilities
        """
        n_samples = X.shape[0]
        n_classes = len(self.classes_)
        calibrated = np.zeros((n_samples, n_classes))
        
        # Get calibration transformers for each class
        # calibrated_classifier is now a dict to avoid sklearn internal dependencies
        calibrators = calibrated_classifier['calibrators']
        
        for i, class_label in enumerate(self.classes_):
            # Get raw probability for this class
            raw_proba = X[:, i]
            
            # Apply per-class calibration transformer
            calibrator = calibrators[i] if i < len(calibrators) else None
            
            if calibrator is None:
                # No calibrator for this class - keep raw
                calibrated[:, i] = raw_proba
            elif hasattr(calibrator, 'predict'):
                # Isotonic regression or similar - expects reshaped input
                calibrated[:, i] = calibrator.predict(raw_proba.reshape(-1, 1)).ravel()
            elif hasattr(calibrator, 'transform'):
                # Transformer interface
                calibrated[:, i] = calibrator.transform(raw_proba.reshape(-1, 1)).ravel()
            else:
                # Fallback
                calibrated[:, i] = raw_proba
        
        # Normalize to sum to 1
        row_sums = calibrated.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1  # Avoid division by zero
        calibrated = calibrated / row_sums
        
        return calibrated
