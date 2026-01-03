# FIX FOR retrain_5m_automated.py
# ===================================
#
# PROBLEM: Line 396 saves only the meta_classifier (LogisticRegression)
# which expects 18 features (stacked probabilities from base models).
#
# SOLUTION: Create and save a wrapper class that includes both base models
# and meta-classifier, matching the EnhancedMetaClassifier structure.

# Add this class definition after the imports (around line 33):

class SimpleMetaClassifier:
    """
    Wrapper for base models + meta-classifier
    Matches the interface expected by model_runtime.py
    """
    def __init__(self, base_models, meta_model, feature_columns):
        self.base_models = base_models
        self.meta_model = meta_model
        self.feature_columns = feature_columns
        self.is_fitted = True
        
    def predict_proba(self, X):
        """
        Takes raw features (17), generates base model predictions,
        stacks them, and feeds to meta-classifier
        """
        # Get predictions from each base model
        meta_features = []
        for name, model in self.base_models.items():
            pred = model.predict_proba(X)
            meta_features.append(pred)
        
        # Stack all predictions
        X_meta = np.hstack(meta_features)
        
        # Meta-classifier prediction
        return self.meta_model.predict_proba(X_meta)
    
    def predict(self, X):
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)


# Then REPLACE lines 394-397 with:

# Create wrapper that includes base models
print("Creating model wrapper...")
full_model = SimpleMetaClassifier(
    base_models=trained_models,
    meta_model=meta_classifier,
    feature_columns=feature_columns
)

# Save the FULL model (not just meta_classifier)
meta_file = f'meta_classifier_{timestamp}_{schema_hash}.joblib'
joblib.dump(full_model, f"{MODEL_DIR}/{meta_file}")
print(f"✅ Saved: {meta_file} (full model with base estimators)")
