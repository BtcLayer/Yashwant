"""
Manifest Utilities for Model Metadata Enhancement
Provides helper functions for generating manifest metadata.
"""

import subprocess
import os
from datetime import datetime, timezone
from typing import Optional, List
import json


def get_git_commit(repo_path: str = ".") -> Optional[str]:
    """
    Get the current git commit SHA (short version).
    Returns None if not in a git repository or git is not available.
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def get_utc_timestamp() -> str:
    """
    Get current UTC timestamp in ISO 8601 format.
    Returns: String like "2026-01-17T09:47:00Z"
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def count_features(feature_file_path: str) -> Optional[int]:
    """
    Count the number of features from a feature columns JSON file.
    
    Args:
        feature_file_path: Path to feature_columns JSON file
    
    Returns:
        Number of features, or None if file cannot be read
    """
    try:
        with open(feature_file_path, 'r') as f:
            data = json.load(f)
        
        # Handle different formats
        if isinstance(data, dict):
            if 'feature_columns' in data:
                return len(data['feature_columns'])
            elif 'feature_cols' in data:
                return len(data['feature_cols'])
        elif isinstance(data, list):
            return len(data)
        
        return None
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def enhance_manifest(
    existing_manifest: dict,
    feature_file_path: Optional[str] = None,
    repo_path: str = "."
) -> dict:
    """
    Enhance an existing manifest with new metadata fields.
    
    Args:
        existing_manifest: The current manifest dict
        feature_file_path: Path to feature columns file (for counting features)
        repo_path: Path to git repository
    
    Returns:
        Enhanced manifest dict with new fields added
    """
    enhanced = existing_manifest.copy()
    
    # Add git commit
    git_commit = get_git_commit(repo_path)
    if git_commit:
        enhanced['git_commit'] = git_commit
    
    # Add timestamp
    enhanced['trained_at_utc'] = get_utc_timestamp()
    
    # Add feature dimension if feature file provided
    if feature_file_path:
        feature_dim = count_features(feature_file_path)
        if feature_dim is not None:
            enhanced['feature_dim'] = feature_dim
    
    return enhanced


def validate_enhanced_manifest(manifest: dict) -> tuple[bool, List[str]]:
    """
    Validate that a manifest has the expected enhanced fields.
    
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    
    # Check for new fields
    if 'git_commit' not in manifest:
        issues.append("Missing 'git_commit' field")
    
    if 'trained_at_utc' not in manifest:
        issues.append("Missing 'trained_at_utc' field")
    
    if 'feature_dim' not in manifest:
        issues.append("Missing 'feature_dim' field (optional but recommended)")
    
    # Validate field formats
    if 'git_commit' in manifest:
        if not isinstance(manifest['git_commit'], str) or len(manifest['git_commit']) < 7:
            issues.append("'git_commit' should be a string of at least 7 characters")
    
    if 'trained_at_utc' in manifest:
        if not isinstance(manifest['trained_at_utc'], str):
            issues.append("'trained_at_utc' should be a string")
        elif not manifest['trained_at_utc'].endswith('Z'):
            issues.append("'trained_at_utc' should be in UTC format ending with 'Z'")
    
    if 'feature_dim' in manifest:
        if not isinstance(manifest['feature_dim'], int) or manifest['feature_dim'] <= 0:
            issues.append("'feature_dim' should be a positive integer")
    
    return (len(issues) == 0, issues)


# Example usage and testing
if __name__ == "__main__":
    print("Testing Manifest Utilities")
    print("=" * 60)
    
    # Test git commit
    commit = get_git_commit()
    print(f"Git Commit: {commit}")
    
    # Test timestamp
    timestamp = get_utc_timestamp()
    print(f"UTC Timestamp: {timestamp}")
    
    # Test feature counting (use actual file if it exists)
    test_feature_file = "live_demo/models/feature_columns_20251018_101628_d7a9e9fb3a42.json"
    if os.path.exists(test_feature_file):
        feature_count = count_features(test_feature_file)
        print(f"Feature Count: {feature_count}")
    else:
        print(f"Feature file not found: {test_feature_file}")
    
    # Test manifest enhancement
    print("\n" + "=" * 60)
    print("Testing Manifest Enhancement")
    print("=" * 60)
    
    existing = {
        "meta_classifier": "meta_classifier_20251018_101628_d7a9e9fb3a42.joblib",
        "calibrator": "calibrator_20251018_101628_d7a9e9fb3a42.joblib",
        "feature_columns": "feature_columns_20251018_101628_d7a9e9fb3a42.json",
        "training_meta": "training_meta_20251018_101628_d7a9e9fb3a42.json"
    }
    
    enhanced = enhance_manifest(
        existing,
        feature_file_path=test_feature_file if os.path.exists(test_feature_file) else None
    )
    
    print("\nOriginal Manifest:")
    print(json.dumps(existing, indent=2))
    
    print("\nEnhanced Manifest:")
    print(json.dumps(enhanced, indent=2))
    
    # Validate
    is_valid, issues = validate_enhanced_manifest(enhanced)
    print(f"\nValidation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
    if issues:
        print("Issues:")
        for issue in issues:
            print(f"  - {issue}")
