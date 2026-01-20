#!/usr/bin/env python3
"""
Package Run - Zip and Ship Tool

Creates a zip file containing run outputs (manifest, logs, schemas) for easy sharing.
Excludes secrets and respects size limits.

Usage:
    python tools/package_run.py --run_dir paper_trading_outputs/5m
    python tools/package_run.py --run_dir paper_trading_outputs/5m --out review.zip --max_size_mb 50
"""

import os
import sys
import argparse
import zipfile
import json
from datetime import datetime
from pathlib import Path


# Exclusion patterns (files/folders to skip)
EXCLUSION_PATTERNS = [
    # Secrets and credentials
    '**/creds*.json',
    '**/credentials*.json',
    '**/*secret*',
    '**/*password*',
    '**/*api_key*',
    '**/.*env',
    
    # Large binary files
    '**/*.pyc',
    '**/__pycache__',
    '**/*.pkl',
    '**/*.h5',
    '**/*.pt',
    '**/*.pth',
    
    # Temporary files
    '**/*.tmp',
    '**/*.temp',
    '**/.DS_Store',
    '**/Thumbs.db',
]


def matches_exclusion(file_path: str, patterns: list) -> bool:
    """Check if file matches any exclusion pattern"""
    from fnmatch import fnmatch
    file_path_lower = file_path.lower()
    
    for pattern in patterns:
        # Convert pattern to lowercase for case-insensitive matching
        pattern_lower = pattern.lower()
        if fnmatch(file_path_lower, pattern_lower):
            return True
    return False


def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB"""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except:
        return 0.0


def create_readme(run_dir: str, manifest_path: str = None) -> str:
    """Generate README content for the zip file"""
    readme = []
    readme.append("=" * 60)
    readme.append("BOT RUN PACKAGE")
    readme.append("=" * 60)
    readme.append("")
    readme.append(f"Generated: {datetime.now().isoformat()}")
    readme.append(f"Source: {run_dir}")
    readme.append("")
    
    # Include manifest summary if available
    if manifest_path and os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            readme.append("RUN SUMMARY")
            readme.append("-" * 60)
            readme.append(f"Run ID: {manifest.get('run_id', 'N/A')}")
            readme.append(f"Asset: {manifest.get('asset', 'N/A')}")
            readme.append(f"Interval: {manifest.get('interval', 'N/A')}")
            readme.append(f"Start: {manifest.get('start_ts', 'N/A')}")
            readme.append(f"End: {manifest.get('end_ts', 'N/A')}")
            readme.append("")
            
            readme.append("STREAM COUNTS")
            readme.append("-" * 60)
            counts = manifest.get('stream_counts', {})
            if counts:
                for stream, count in counts.items():
                    readme.append(f"  {stream}: {count}")
            else:
                readme.append("  No events recorded yet")
            readme.append("")
        except Exception as e:
            readme.append(f"(Could not read manifest: {e})")
            readme.append("")
    
    readme.append("CONTENTS")
    readme.append("-" * 60)
    readme.append("This package contains:")
    readme.append("  - run_manifest.json (run summary)")
    readme.append("  - logs/ (event logs)")
    readme.append("  - schemas/ (if present)")
    readme.append("  - health snapshots (if present)")
    readme.append("")
    readme.append("NOTE: Secrets and credentials have been excluded.")
    readme.append("=" * 60)
    
    return "\n".join(readme)


def package_run(run_dir: str, output_path: str = None, max_size_mb: float = 100.0, verbose: bool = True):
    """
    Package a run directory into a zip file
    
    Args:
        run_dir: Path to run output directory
        output_path: Output zip file path (auto-generated if None)
        max_size_mb: Maximum zip size in MB
        verbose: Print progress messages
    
    Returns:
        Path to created zip file
    """
    # Validate run directory
    if not os.path.exists(run_dir):
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    
    # Generate output path if not provided
    if output_path is None:
        run_name = os.path.basename(os.path.normpath(run_dir))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"review_{run_name}_{timestamp}.zip"
    
    # Ensure output path has .zip extension
    if not output_path.endswith('.zip'):
        output_path += '.zip'
    
    if verbose:
        print(f"📦 Packaging run: {run_dir}")
        print(f"📁 Output: {output_path}")
        print(f"📏 Max size: {max_size_mb} MB")
        print()
    
    # Track total size
    total_size_mb = 0.0
    files_added = 0
    files_skipped = 0
    
    # Create zip file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through run directory
        for root, dirs, files in os.walk(run_dir):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not matches_exclusion(os.path.join(root, d), EXCLUSION_PATTERNS)]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check exclusion patterns
                if matches_exclusion(file_path, EXCLUSION_PATTERNS):
                    files_skipped += 1
                    if verbose:
                        print(f"⏭️  Skipped (excluded): {file}")
                    continue
                
                # Check file size
                file_size_mb = get_file_size_mb(file_path)
                
                # Check if adding this file would exceed max size
                if total_size_mb + file_size_mb > max_size_mb:
                    files_skipped += 1
                    if verbose:
                        print(f"⏭️  Skipped (size limit): {file} ({file_size_mb:.2f} MB)")
                    continue
                
                # Add file to zip
                arcname = os.path.relpath(file_path, run_dir)
                zipf.write(file_path, arcname)
                total_size_mb += file_size_mb
                files_added += 1
                
                if verbose:
                    print(f"✅ Added: {arcname} ({file_size_mb:.2f} MB)")
        
        # Add README
        manifest_path = os.path.join(run_dir, 'run_manifest.json')
        readme_content = create_readme(run_dir, manifest_path)
        zipf.writestr('README.txt', readme_content)
        if verbose:
            print(f"✅ Added: README.txt")
    
    # Final summary
    actual_size_mb = get_file_size_mb(output_path)
    
    if verbose:
        print()
        print("=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"Files added: {files_added}")
        print(f"Files skipped: {files_skipped}")
        print(f"Total size: {actual_size_mb:.2f} MB")
        print(f"Output: {os.path.abspath(output_path)}")
        print("=" * 60)
        print()
        print(f"✅ Package created successfully!")
        print(f"📤 Ready to upload: {output_path}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Package bot run outputs into a zip file for sharing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Package a 5m run
  python tools/package_run.py --run_dir paper_trading_outputs/5m
  
  # Package with custom output name
  python tools/package_run.py --run_dir paper_trading_outputs/5m --out my_review.zip
  
  # Package with size limit
  python tools/package_run.py --run_dir paper_trading_outputs/5m --max_size_mb 50
  
  # Quiet mode
  python tools/package_run.py --run_dir paper_trading_outputs/5m --quiet
        """
    )
    
    parser.add_argument(
        '--run_dir',
        required=True,
        help='Path to run output directory (e.g., paper_trading_outputs/5m)'
    )
    
    parser.add_argument(
        '--out',
        default=None,
        help='Output zip file path (auto-generated if not specified)'
    )
    
    parser.add_argument(
        '--max_size_mb',
        type=float,
        default=100.0,
        help='Maximum zip file size in MB (default: 100)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )
    
    args = parser.parse_args()
    
    try:
        output_path = package_run(
            run_dir=args.run_dir,
            output_path=args.out,
            max_size_mb=args.max_size_mb,
            verbose=not args.quiet
        )
        
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
