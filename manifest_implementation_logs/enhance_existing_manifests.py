"""
Script to enhance all existing LATEST.json files with metadata
Phase 6: Update Existing Manifests
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_demo.models.manifest_utils import enhance_manifest

print("="*80)
print("PHASE 6: Enhancing Existing Manifests")
print("="*80)

# Define all manifest paths
manifests = [
    {
        'path': 'live_demo/models/LATEST.json',
        'name': '5m',
        'feature_file_key': 'feature_columns'
    },
    {
        'path': 'live_demo_1h/models/LATEST.json',
        'name': '1h',
        'feature_file_key': 'feature_columns'
    },
    {
        'path': 'live_demo_12h/models/LATEST.json',
        'name': '12h',
        'feature_file_key': 'feature_columns'
    },
    {
        'path': 'live_demo_24h/models/LATEST.json',
        'name': '24h',
        'feature_file_key': 'feature_columns'
    }
]

results = []

for manifest_info in manifests:
    manifest_path = manifest_info['path']
    name = manifest_info['name']
    
    print(f"\n{name} Timeframe")
    print("-" * 80)
    
    if not os.path.exists(manifest_path):
        print(f"  ⚠️  Manifest not found: {manifest_path}")
        results.append({'name': name, 'status': 'SKIPPED', 'reason': 'File not found'})
        continue
    
    try:
        # Load existing manifest
        with open(manifest_path, 'r') as f:
            existing = json.load(f)
        
        print(f"  📄 Loaded existing manifest")
        print(f"     Keys: {list(existing.keys())}")
        
        # Check if already enhanced
        if 'git_commit' in existing and 'trained_at_utc' in existing:
            print(f"  ✅ Already enhanced (has metadata)")
            results.append({'name': name, 'status': 'ALREADY_ENHANCED'})
            continue
        
        # Get feature file path
        feature_file_key = manifest_info['feature_file_key']
        feature_file = existing.get(feature_file_key)
        
        if not feature_file:
            print(f"  ⚠️  No feature file found in manifest")
            feature_file_path = None
        else:
            base_dir = os.path.dirname(manifest_path)
            feature_file_path = os.path.join(base_dir, feature_file)
            
            if not os.path.exists(feature_file_path):
                print(f"  ⚠️  Feature file not found: {feature_file_path}")
                feature_file_path = None
        
        # Enhance manifest
        enhanced = enhance_manifest(
            existing,
            feature_file_path=feature_file_path
        )
        
        # Save enhanced manifest
        with open(manifest_path, 'w') as f:
            json.dump(enhanced, f, indent=2)
        
        print(f"  ✅ Enhanced and saved")
        print(f"     - git_commit: {enhanced.get('git_commit')}")
        print(f"     - trained_at_utc: {enhanced.get('trained_at_utc')}")
        print(f"     - feature_dim: {enhanced.get('feature_dim')}")
        
        results.append({
            'name': name,
            'status': 'SUCCESS',
            'git_commit': enhanced.get('git_commit'),
            'trained_at_utc': enhanced.get('trained_at_utc'),
            'feature_dim': enhanced.get('feature_dim')
        })
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results.append({'name': name, 'status': 'FAILED', 'error': str(e)})

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
already_enhanced = sum(1 for r in results if r['status'] == 'ALREADY_ENHANCED')
failed_count = sum(1 for r in results if r['status'] == 'FAILED')
skipped_count = sum(1 for r in results if r['status'] == 'SKIPPED')

print(f"\nTotal Manifests: {len(manifests)}")
print(f"  ✅ Enhanced: {success_count}")
print(f"  ✅ Already Enhanced: {already_enhanced}")
print(f"  ❌ Failed: {failed_count}")
print(f"  ⚠️  Skipped: {skipped_count}")

print("\nDetails:")
for result in results:
    status_icon = {
        'SUCCESS': '✅',
        'ALREADY_ENHANCED': '✅',
        'FAILED': '❌',
        'SKIPPED': '⚠️'
    }.get(result['status'], '?')
    
    print(f"  {status_icon} {result['name']}: {result['status']}")
    if result['status'] == 'SUCCESS':
        print(f"     git_commit: {result.get('git_commit')}")
        print(f"     feature_dim: {result.get('feature_dim')}")

print("\n" + "="*80)
if success_count + already_enhanced == len(manifests):
    print("✅ ALL MANIFESTS ENHANCED SUCCESSFULLY!")
else:
    print("⚠️  Some manifests could not be enhanced")
print("="*80)
