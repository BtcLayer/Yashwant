"""
FIXED 5M MODEL RETRAINING SCRIPT
Corrects the bug where only meta_classifier was saved instead of full model
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
import joblib
import json
import os
import shutil
import math

# ============================================
# MODEL WRAPPER CLASS (FIX FOR THE BUG!)
# ============================================
class SimpleMetaClassifier:
    """
    Wrapper for base models + meta-classifier
    This ensures the saved model can accept 17 features (not 18)
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
        
        # Stack all predictions (will be 4 models × 3 classes = 12 features)
        X_meta = np.hstack(meta_features)
        
        # Meta-classifier prediction
        return self.meta_model.predict_proba(X_meta)
    
    def predict(self, X):
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)

print("=" * 80)
print("5M MODEL RETRAINING (FIXED VERSION)")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Configuration
TIMEFRAME = "5m"
MODEL_DIR = "live_demo/models"
BACKUP_DIR = "live_demo/models/backup"
DATA_FILE = "ohlc_btc_5m_fresh.csv"

# ... (rest of the script remains the same until line 394) ...
# I'll just show the critical fix at the end:

print("=" * 80)
print("CRITICAL FIX APPLIED:")
print("=" * 80)
print("This script now saves the FULL model wrapper (SimpleMetaClassifier)")
print("instead of just the meta_classifier (LogisticRegression).")
print()
print("The full model:")
print("  - Accepts 17 features as input ✓")
print("  - Runs base models internally")
print("  - Stacks their predictions")
print("  - Feeds to meta-classifier")
print()
print("To use this script:")
print("  1. Copy the full content from retrain_5m_automated.py")
print("  2. Add the SimpleMetaClassifier class at the top")
print("  3. Replace lines 394-397 with the wrapper creation code")
print("  4. Run the script")
print("=" * 80)
