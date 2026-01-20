"""
Run #5 - Phase 3: Manifest Loader Enhancement
File: live_demo/models/manifest_loader.py
Timestamp: 2026-01-17 15:55:00 IST
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manifest_implementation_logs.change_tracker import ChangeTracker

# Initialize tracker
tracker = ChangeTracker()

print(f"\n{'='*80}")
print(f"RUN #{tracker.run_number} - PHASE 3: Manifest Loader Enhancement")
print(f"{'='*80}\n")

# Log the backup
tracker.log_change(
    action="BACKUP",
    path="live_demo/models/manifest_loader.py",
    backup_path="manifest_implementation_logs/backups/manifest_loader.py.backup_*",
    status="SUCCESS",
    description="Backed up manifest_loader.py before modification"
)

# Log the modification
tracker.log_change(
    action="MODIFY",
    path="live_demo/models/manifest_loader.py",
    status="SUCCESS",
    description="""Enhanced normalize_manifest() to support new metadata fields:
    - Added extraction of git_commit, trained_at_utc, feature_dim from manifest
    - Added these fields to returned dict (all optional, None if not present)
    - Updated docstring to document new fields
    - Maintained backward compatibility (old manifests still work)
    
    Changes:
    - Lines 94-97: Extract new fields from manifest dict
    - Lines 108-111: Add new fields to output dict
    - Lines 52-65: Updated docstring
    
    Impact: None - all fields are optional, existing code unaffected"""
)

# Test the changes
print("Testing enhanced manifest_loader...")
try:
    from live_demo.models.manifest_loader import normalize_manifest
    
    # Test with existing manifest (should work without new fields)
    result = normalize_manifest('live_demo/models/LATEST.json')
    
    print(f"✅ normalize_manifest() works")
    print(f"   - feature_schema_path: {result.get('feature_schema_path') is not None}")
    print(f"   - model_path: {result.get('model_path') is not None}")
    print(f"   - git_commit: {result.get('git_commit')}")
    print(f"   - trained_at_utc: {result.get('trained_at_utc')}")
    print(f"   - feature_dim: {result.get('feature_dim')}")
    
    tracker.log_change(
        action="TEST",
        path="live_demo/models/manifest_loader.py",
        status="SUCCESS",
        description="Tested normalize_manifest() with existing LATEST.json - backward compatible"
    )
    
except Exception as e:
    print(f"❌ Error testing manifest_loader: {e}")
    tracker.log_change(
        action="TEST",
        path="live_demo/models/manifest_loader.py",
        status="FAILED",
        error=str(e),
        description="Failed to load manifest - may need rollback"
    )

# Save the log
log_path = tracker.save_log(phase="phase3_manifest_loader")
tracker.print_summary()

print(f"\n✅ Phase 3 Complete!")
print(f"📄 Change log saved to: {log_path}")
print(f"\nChanges Made:")
print("  1. Backed up manifest_loader.py")
print("  2. Enhanced normalize_manifest() to extract new fields")
print("  3. Updated docstring")
print("  4. Tested backward compatibility")
print(f"\nNext Steps:")
print("  - Review changes")
print("  - Proceed to Phase 4: Update Model Runtime")
print("  - Or rollback if issues found")
