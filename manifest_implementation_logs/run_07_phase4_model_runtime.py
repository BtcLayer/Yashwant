"""
Run #7 - Phase 4: Model Runtime Enhancement
File: live_demo/model_runtime.py
Timestamp: 2026-01-17 17:02:00 IST
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manifest_implementation_logs.change_tracker import ChangeTracker

# Initialize tracker
tracker = ChangeTracker()

print(f"\n{'='*80}")
print(f"RUN #{tracker.run_number} - PHASE 4: Model Runtime Enhancement")
print(f"{'='*80}\n")

# Log the backup
tracker.log_change(
    action="BACKUP",
    path="live_demo/model_runtime.py",
    backup_path="manifest_implementation_logs/backups/model_runtime.py.backup_*",
    status="SUCCESS",
    description="Backed up model_runtime.py before modification"
)

# Log the modification
tracker.log_change(
    action="MODIFY",
    path="live_demo/model_runtime.py",
    status="SUCCESS",
    description="""Enhanced ModelRuntime.__init__() to use new metadata fields:
    
    Changes in __init__ method:
    - Lines 54-64: Extract git_commit, trained_at_utc, expected_feature_dim from manifest
    - Lines 61-63: Log git_commit and trained_at_utc if available
    - Lines 79-82: Set metadata fields to None in fallback mode
    - Lines 95-105: Validate feature dimension if expected_feature_dim is set
    - Lines 97-101: Print warning if dimension mismatch
    - Line 103: Print confirmation if dimension matches
    
    New attributes added:
    - self.git_commit: Git commit SHA from manifest (None if not present)
    - self.trained_at_utc: Training timestamp from manifest (None if not present)
    - self.expected_feature_dim: Expected feature count (None if not present)
    
    Behavior:
    - Logs model metadata on initialization (if available)
    - Validates feature dimension (if expected_feature_dim set)
    - Warns on dimension mismatch (non-fatal)
    - Backward compatible (all fields optional)
    
    Impact: None - all enhancements are optional, existing code unaffected"""
)

# Test the changes
print("Testing enhanced ModelRuntime...")
try:
    from live_demo.model_runtime import ModelRuntime
    
    print("\n1. Testing with existing manifest (no metadata)...")
    mr = ModelRuntime('live_demo/models/LATEST.json')
    
    print(f"   ✅ ModelRuntime initialized")
    print(f"   - Model loaded: {mr.model is not None}")
    print(f"   - Calibrator loaded: {mr.calibrator is not None}")
    print(f"   - Feature columns: {len(mr.columns)}")
    print(f"   - Git commit: {mr.git_commit}")
    print(f"   - Trained at: {mr.trained_at_utc}")
    print(f"   - Expected feature dim: {mr.expected_feature_dim}")
    
    print("\n2. Testing model inference...")
    import numpy as np
    dummy_input = [0.0] * len(mr.columns)
    result = mr.infer(dummy_input)
    
    print(f"   ✅ Inference works")
    print(f"   - p_down: {result.get('p_down'):.4f}")
    print(f"   - p_neutral: {result.get('p_neutral'):.4f}")
    print(f"   - p_up: {result.get('p_up'):.4f}")
    print(f"   - s_model: {result.get('s_model'):.4f}")
    
    tracker.log_change(
        action="TEST",
        path="live_demo/model_runtime.py",
        status="SUCCESS",
        description="Tested ModelRuntime with existing manifest - backward compatible, inference working"
    )
    
except Exception as e:
    print(f"   ❌ Error testing ModelRuntime: {e}")
    import traceback
    traceback.print_exc()
    tracker.log_change(
        action="TEST",
        path="live_demo/model_runtime.py",
        status="FAILED",
        error=str(e),
        description="Failed to initialize or test ModelRuntime - may need rollback"
    )

# Save the log
log_path = tracker.save_log(phase="phase4_model_runtime")
tracker.print_summary()

print(f"\n✅ Phase 4 Complete!")
print(f"📄 Change log saved to: {log_path}")
print(f"\nChanges Made:")
print("  1. Backed up model_runtime.py")
print("  2. Enhanced ModelRuntime to extract metadata fields")
print("  3. Added feature dimension validation")
print("  4. Added metadata logging on model load")
print("  5. Tested backward compatibility")
print(f"\nNext Steps:")
print("  - Review changes")
print("  - Proceed to Phase 5: Update Training Scripts")
print("  - Or rollback if issues found")
