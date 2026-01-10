"""
Check current model weights and configuration
"""
import joblib
import json
from pathlib import Path
import numpy as np

print("="*80)
print("CURRENT MODEL INSPECTION")
print("="*80)

# Check LATEST.json
latest_path = Path("live_demo/models/LATEST.json")
if latest_path.exists():
    with open(latest_path, 'r') as f:
        latest = json.load(f)
    
    print("\n--- LATEST.json ---")
    print(json.dumps(latest, indent=2))
    
    # Load meta-classifier
    meta_clf_path = Path("live_demo/models") / latest['meta_classifier']
    if meta_clf_path.exists():
        print(f"\n--- Loading {latest['meta_classifier']} ---")
        meta_clf_data = joblib.load(meta_clf_path)
        
        print(f"\nMeta-classifier structure:")
        print(f"  Keys: {list(meta_clf_data.keys())}")
        
        if 'base_models' in meta_clf_data:
            print(f"\n  Base models:")
            for name, model in meta_clf_data['base_models'].items():
                print(f"    {name}: {type(model).__name__}")
                
                # Check if model has class_weight
                if hasattr(model, 'class_weight'):
                    print(f"      class_weight: {model.class_weight}")
                
                # Check if model has classes_
                if hasattr(model, 'classes_'):
                    print(f"      classes_: {model.classes_}")
                
                # Check feature importances for tree models
                if hasattr(model, 'feature_importances_'):
                    importances = model.feature_importances_
                    print(f"      feature_importances shape: {importances.shape}")
                    print(f"      top 5 features: {np.argsort(importances)[-5:][::-1]}")
        
        if 'meta_model' in meta_clf_data:
            meta_model = meta_clf_data['meta_model']
            print(f"\n  Meta model: {type(meta_model).__name__}")
            
            if hasattr(meta_model, 'classes_'):
                print(f"    classes_: {meta_model.classes_}")
            
            if hasattr(meta_model, 'coef_'):
                print(f"    coef_ shape: {meta_model.coef_.shape}")
                print(f"    coef_ values:\n{meta_model.coef_}")
    
    # Load calibrator
    calibrator_path = Path("live_demo/models") / latest['calibrator']
    if calibrator_path.exists():
        print(f"\n--- Loading {latest['calibrator']} ---")
        calibrator = joblib.load(calibrator_path)
        
        print(f"\nCalibrator: {type(calibrator).__name__}")
        
        if hasattr(calibrator, 'calibrated_classifiers_'):
            print(f"  Number of calibrated classifiers: {len(calibrator.calibrated_classifiers_)}")
            
            for i, cal_clf in enumerate(calibrator.calibrated_classifiers_):
                print(f"\n  Calibrated classifier {i}:")
                print(f"    Type: {type(cal_clf).__name__}")
                
                if hasattr(cal_clf, 'calibrators'):
                    print(f"    Number of calibrators: {len(cal_clf.calibrators)}")
                    for j, cal in enumerate(cal_clf.calibrators):
                        print(f"      Calibrator {j}: {type(cal).__name__}")
    
    # Load feature columns
    feature_cols_path = Path("live_demo/models") / latest['feature_columns']
    if feature_cols_path.exists():
        with open(feature_cols_path, 'r') as f:
            feature_cols = json.load(f)
        
        print(f"\n--- Feature Columns ---")
        print(f"Number of features: {len(feature_cols)}")
        print(f"Features: {feature_cols}")
    
    # Load training metadata
    training_meta_path = Path("live_demo/models") / latest['training_meta']
    if training_meta_path.exists():
        with open(training_meta_path, 'r') as f:
            training_meta = json.load(f)
        
        print(f"\n--- Training Metadata ---")
        print(json.dumps(training_meta, indent=2))

else:
    print("\n[ERROR] LATEST.json not found")

print("\n" + "="*80)
print("INSPECTION COMPLETE")
print("="*80)
