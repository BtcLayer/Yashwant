"""
Custom ensemble wrapper for 1h model
Makes ensemble compatible with sklearn interface expected by ModelRuntime
"""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

class EnsembleWrapper(BaseEstimator, ClassifierMixin):
    """
    Wrapper to make ensemble dict compatible with sklearn interface
    Expected by ModelRuntime in live_demo/model_runtime.py
    """
    def __init__(self, base_models=None, meta_clf=None, feature_cols=None, schema_hash=None):
        self.base_models = base_models or []
        self.meta_clf = meta_clf
        self.feature_cols = feature_cols or []
        self.schema_hash = schema_hash
        self.classes_ = np.array([0, 1, 2])  # DOWN, NEUTRAL, UP
    
    def predict_proba(self, X):
        """
        Predict class probabilities using stacked ensemble
        
        Args:
            X: numpy array of shape (n_samples, n_features)
        
        Returns:
            probabilities: array of shape (n_samples, 3)
        """
        # Stack base model predictions
        base_probas = []
        for name, model in self.base_models:
            proba = model.predict_proba(X)
            base_probas.append(proba)
        
        # Concatenate to form meta-features (n_samples, n_base_models * 3)
        stacked = np.hstack(base_probas)
        
        # Meta-classifier prediction
        final_proba = self.meta_clf.predict_proba(stacked)
        
        return final_proba
    
    def predict(self, X):
        """Predict class labels"""
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)
