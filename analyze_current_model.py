"""
Analyze current model weights and behavior
"""
import joblib
import json
from pathlib import Path
import numpy as np

print("="*80)
print("CURRENT MODEL ANALYSIS")
print("="*80)

# Load current model
model_dir = Path("live_demo/models")

# Check LATEST.json
latest_path = model_dir / "LATEST.json"
if latest_path.exists():
    with open(latest_path, 'r') as f:
        latest = json.load(f)
    
    print("\nCurrent model manifest (LATEST.json):")
    for key, value in latest.items():
        print(f"  {key}: {value}")
    
    # Load meta-classifier
    meta_clf_path = model_dir / latest['meta_classifier']
    if meta_clf_path.exists():
        print(f"\nLoading meta-classifier from {meta_clf_path.name}...")
        meta_clf_data = joblib.load(meta_clf_path)
        
        print("\nMeta-classifier structure:")
        print(f"  Type: {type(meta_clf_data)}")
        print(f"  Keys: {list(meta_clf_data.keys()) if isinstance(meta_clf_data, dict) else 'N/A'}")
        
        if isinstance(meta_clf_data, dict):
            # Check base models
            if 'base_models' in meta_clf_data:
                print("\n  Base models:")
                for name, model in meta_clf_data['base_models'].items():
                    print(f"    {name}: {type(model).__name__}")
                    
                    # Check if model has classes_
                    if hasattr(model, 'classes_'):
                        print(f"      Classes: {model.classes_}")
                    
                    # Check feature importances for tree models
                    if hasattr(model, 'feature_importances_'):
                        importances = model.feature_importances_
                        print(f"      Feature importances shape: {importances.shape}")
                        print(f"      Top 5 features: {np.argsort(importances)[-5:][::-1]}")
            
            # Check meta model
            if 'meta_model' in meta_clf_data:
                meta_model = meta_clf_data['meta_model']
                print(f"\n  Meta model: {type(meta_model).__name__}")
                
                if hasattr(meta_model, 'classes_'):
                    print(f"    Classes: {meta_model.classes_}")
                
                if hasattr(meta_model, 'coef_'):
                    print(f"    Coefficients shape: {meta_model.coef_.shape}")
                    print(f"    Coefficients:\n{meta_model.coef_}")
                
                if hasattr(meta_model, 'intercept_'):
                    print(f"    Intercept: {meta_model.intercept_}")
    
    # Load calibrator
    calibrator_path = model_dir / latest['calibrator']
    if calibrator_path.exists():
        print(f"\nLoading calibrator from {calibrator_path.name}...")
        calibrator = joblib.load(calibrator_path)
        
        print(f"  Type: {type(calibrator).__name__}")
        
        if hasattr(calibrator, 'calibrated_classifiers_'):
            print(f"  Number of calibrated classifiers: {len(calibrator.calibrated_classifiers_)}")
            
            for i, cal_clf in enumerate(calibrator.calibrated_classifiers_):
                print(f"\n  Calibrator {i}:")
                if hasattr(cal_clf, 'calibrators'):
                    print(f"    Calibrators: {len(cal_clf.calibrators)}")
                    for j, cal in enumerate(cal_clf.calibrators):
                        print(f"      Calibrator {j}: {type(cal).__name__}")
    
    # Load feature columns
    feature_cols_path = model_dir / latest['feature_columns']
    if feature_cols_path.exists():
        with open(feature_cols_path, 'r') as f:
            feature_cols = json.load(f)
        
        print(f"\nFeature columns ({len(feature_cols)}):")
        for i, col in enumerate(feature_cols):
            print(f"  {i}: {col}")
    
    # Load training meta
    training_meta_path = model_dir / latest['training_meta']
    if training_meta_path.exists():
        with open(training_meta_path, 'r') as f:
            training_meta = json.load(f)
        
        print("\nTraining metadata:")
        for key, value in training_meta.items():
            if key != 'test_results':
                print(f"  {key}: {value}")
        
        if 'test_results' in training_meta:
            print("\n  Test results:")
            for metric, values in training_meta['test_results'].items():
                print(f"    {metric}:")
                if isinstance(values, dict):
                    for k, v in values.items():
                        print(f"      {k}: {v}")
                else:
                    print(f"      {values}")

else:
    print("\n[ERROR] LATEST.json not found!")

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)

# Check if model expects [-1, 0, 1] or [0, 1, 2]
print("\nModel expects classes:", end=" ")
if meta_clf_path.exists():
    meta_clf_data = joblib.load(meta_clf_path)
    if isinstance(meta_clf_data, dict) and 'meta_model' in meta_clf_data:
        if hasattr(meta_clf_data['meta_model'], 'classes_'):
            classes = meta_clf_data['meta_model'], 'classes_']
            print(classes)
            
            if np.array_equal(classes, [-1, 0, 1]):
                print("  Format: [-1, 0, 1] (DOWN, NEUTRAL, UP)")
            elif np.array_equal(classes, [0, 1, 2]):
                print("  Format: [0, 1, 2] (DOWN, NEUTRAL, UP)")
            else:
                print(f"  Unknown format: {classes}")

print("\n" + "="*80)
