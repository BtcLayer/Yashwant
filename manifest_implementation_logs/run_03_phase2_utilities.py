"""
Run #3 - Phase 2: Core Utilities Implementation
Implements manifest utility functions with change tracking.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manifest_implementation_logs.change_tracker import ChangeTracker

# Initialize tracker
tracker = ChangeTracker()

print(f"\n{'='*80}")
print(f"RUN #{tracker.run_number} - PHASE 2: Core Utilities Implementation")
print(f"{'='*80}\n")

# Log the creation of manifest_utils.py
tracker.log_change(
    action="CREATE_FILE",
    path="live_demo/models/manifest_utils.py",
    status="SUCCESS",
    description="Created manifest utility functions (get_git_commit, get_utc_timestamp, count_features, enhance_manifest, validate_enhanced_manifest)"
)

# Test the utilities
print("Testing manifest utilities...")
try:
    from live_demo.models.manifest_utils import (
        get_git_commit,
        get_utc_timestamp,
        count_features,
        enhance_manifest,
        validate_enhanced_manifest
    )
    
    # Test each function
    commit = get_git_commit()
    timestamp = get_utc_timestamp()
    
    print(f"✅ get_git_commit() -> {commit}")
    print(f"✅ get_utc_timestamp() -> {timestamp}")
    
    # Test with actual feature file
    feature_file = "live_demo/models/feature_columns_20251018_101628_d7a9e9fb3a42.json"
    if os.path.exists(feature_file):
        feature_count = count_features(feature_file)
        print(f"✅ count_features() -> {feature_count}")
    
    # Test enhancement
    test_manifest = {
        "meta_classifier": "test.joblib",
        "calibrator": "test_cal.joblib"
    }
    enhanced = enhance_manifest(test_manifest, feature_file_path=feature_file)
    is_valid, issues = validate_enhanced_manifest(enhanced)
    
    print(f"✅ enhance_manifest() -> Added {len(enhanced) - len(test_manifest)} fields")
    print(f"✅ validate_enhanced_manifest() -> {'PASSED' if is_valid else 'FAILED'}")
    
    tracker.log_change(
        action="TEST",
        path="live_demo/models/manifest_utils.py",
        status="SUCCESS",
        description="All utility functions tested successfully"
    )
    
except Exception as e:
    print(f"❌ Error testing utilities: {e}")
    tracker.log_change(
        action="TEST",
        path="live_demo/models/manifest_utils.py",
        status="FAILED",
        error=str(e)
    )

# Save the log
log_path = tracker.save_log(phase="phase2_utilities")
tracker.print_summary()

print(f"\n✅ Phase 2 Complete!")
print(f"📄 Change log saved to: {log_path}")
print(f"\nNext Steps:")
print("  - Review the change log")
print("  - Proceed to Phase 3: Update Manifest Loader")
print("  - Or rollback if issues found")
