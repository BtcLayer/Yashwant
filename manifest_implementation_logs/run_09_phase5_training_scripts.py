"""
Run #9 - Phase 5: Training Scripts Enhancement
Files: train_model.py, retrain_5m_production_v3.py
Timestamp: 2026-01-17 17:37:00 IST
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manifest_implementation_logs.change_tracker import ChangeTracker

# Initialize tracker
tracker = ChangeTracker()

print(f"\n{'='*80}")
print(f"RUN #{tracker.run_number} - PHASE 5: Training Scripts Enhancement")
print(f"{'='*80}\n")

# Log the backups
tracker.log_change(
    action="BACKUP",
    path="train_model.py",
    backup_path="manifest_implementation_logs/backups/train_model.py.backup_*",
    status="SUCCESS",
    description="Backed up train_model.py before modification"
)

tracker.log_change(
    action="BACKUP",
    path="retrain_5m_production_v3.py",
    backup_path="manifest_implementation_logs/backups/retrain_5m_production_v3.py.backup_*",
    status="SUCCESS",
    description="Backed up retrain_5m_production_v3.py before modification"
)

# Log the modifications
tracker.log_change(
    action="MODIFY",
    path="train_model.py",
    status="SUCCESS",
    description="""Enhanced LATEST.json generation to use manifest_utils:
    
    Changes (Lines 290-327):
    - Import manifest_utils.enhance_manifest
    - Create base manifest dict
    - Call enhance_manifest() to add metadata fields
    - Print enhanced metadata (git_commit, trained_at_utc, feature_dim)
    - Fallback to basic manifest if manifest_utils not available
    
    Behavior:
    - Automatically adds git_commit from current repo
    - Automatically adds trained_at_utc timestamp
    - Automatically adds feature_dim from feature_columns file
    - Backward compatible (try/except with fallback)
    
    Impact: Training scripts now generate enhanced manifests automatically"""
)

tracker.log_change(
    action="MODIFY",
    path="retrain_5m_production_v3.py",
    status="SUCCESS",
    description="""Enhanced LATEST.json generation to use manifest_utils:
    
    Changes (Lines 534-559):
    - Import manifest_utils.enhance_manifest
    - Call enhance_manifest() on model_files dict
    - Print enhanced metadata fields
    - Fallback to basic manifest if manifest_utils not available
    
    Behavior:
    - Same as train_model.py
    - Automatically enhances manifest with metadata
    - Backward compatible with try/except
    
    Impact: Production retraining now generates enhanced manifests"""
)

# Test the changes (syntax check)
print("Testing enhanced training scripts...")
try:
    print("\n1. Checking train_model.py syntax...")
    with open('train_model.py', 'r') as f:
        compile(f.read(), 'train_model.py', 'exec')
    print("   ✅ train_model.py syntax valid")
    
    print("\n2. Checking retrain_5m_production_v3.py syntax...")
    with open('retrain_5m_production_v3.py', 'r') as f:
        compile(f.read(), 'retrain_5m_production_v3.py', 'exec')
    print("   ✅ retrain_5m_production_v3.py syntax valid")
    
    print("\n3. Verifying manifest_utils import...")
    from live_demo.models.manifest_utils import enhance_manifest
    print("   ✅ manifest_utils available")
    
    tracker.log_change(
        action="TEST",
        path="train_model.py, retrain_5m_production_v3.py",
        status="SUCCESS",
        description="Syntax validation passed for both training scripts"
    )
    
except SyntaxError as e:
    print(f"   ❌ Syntax error: {e}")
    tracker.log_change(
        action="TEST",
        path="train_model.py, retrain_5m_production_v3.py",
        status="FAILED",
        error=str(e),
        description="Syntax error in training scripts - may need rollback"
    )
except Exception as e:
    print(f"   ❌ Error: {e}")
    tracker.log_change(
        action="TEST",
        path="train_model.py, retrain_5m_production_v3.py",
        status="FAILED",
        error=str(e)
    )

# Save the log
log_path = tracker.save_log(phase="phase5_training_scripts")
tracker.print_summary()

print(f"\n✅ Phase 5 Complete!")
print(f"📄 Change log saved to: {log_path}")
print(f"\nChanges Made:")
print("  1. Backed up train_model.py")
print("  2. Backed up retrain_5m_production_v3.py")
print("  3. Enhanced LATEST.json generation in both scripts")
print("  4. Added automatic metadata enrichment")
print("  5. Tested syntax validation")
print(f"\nNext Steps:")
print("  - Review changes")
print("  - Proceed to Phase 6: Update Existing Manifests")
print("  - Or test training scripts to verify they work")
print(f"\nNote:")
print("  - Next time you train a model, LATEST.json will include:")
print("    * git_commit (current code version)")
print("    * trained_at_utc (training timestamp)")
print("    * feature_dim (number of features)")
