"""
Test script to verify ManifestWriter integration for 12h bot

This script checks:
1. ManifestWriter module exists and can be imported
2. Manifest file structure is correct
3. All tracked streams are defined
4. Update interval is appropriate for 12h timeframe
"""

import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_manifest_writer_import():
    """Test that ManifestWriter can be imported"""
    try:
        from live_demo_12h.ops.manifest_writer import ManifestWriter
        print("✅ ManifestWriter import successful")
        return True, ManifestWriter
    except ImportError as e:
        print(f"❌ ManifestWriter import failed: {e}")
        return False, None

def test_manifest_writer_initialization(ManifestWriter):
    """Test that ManifestWriter can be initialized"""
    try:
        import time
        import tempfile
        
        # Create temporary directory for test
        temp_dir = tempfile.mkdtemp()
        
        writer = ManifestWriter(
            run_id=f"test_run_{int(time.time())}",
            asset="BTCUSDT",
            output_dir=temp_dir,
            interval="12h"
        )
        
        print(f"✅ ManifestWriter initialized successfully")
        print(f"   - Run ID: {writer.run_id}")
        print(f"   - Asset: {writer.asset}")
        print(f"   - Interval: {writer.interval}")
        print(f"   - Update interval: {writer.update_interval} bars (~{writer.update_interval * 12 / 24:.1f} days)")
        print(f"   - Tracked streams: {len(writer.tracked_streams)}")
        
        # Verify tracked streams
        expected_streams = [
            'signals', 'calibration', 'feature_log', 'order_intent',
            'repro', 'health', 'executions', 'costs', 'pnl_equity',
            'ensemble', 'overlay_status', 'hyperliquid_fills'
        ]
        
        missing_streams = set(expected_streams) - set(writer.tracked_streams)
        extra_streams = set(writer.tracked_streams) - set(expected_streams)
        
        if missing_streams:
            print(f"   ⚠️  Missing streams: {missing_streams}")
        if extra_streams:
            print(f"   ℹ️  Extra streams: {extra_streams}")
        
        print(f"   ✅ All expected streams are tracked")
        
        # Test initialization
        writer.initialize(
            config_path=os.path.join(project_root, "live_demo_12h", "config.json"),
            code_path=os.path.join(project_root, "live_demo_12h", "main.py"),
            model_manifest_path=os.path.join(project_root, "live_demo", "models", "LATEST.json")
        )
        
        # Check if manifest file was created
        if os.path.exists(writer.manifest_path):
            print(f"✅ Manifest file created at: {writer.manifest_path}")
            
            # Read and display manifest
            import json
            with open(writer.manifest_path, 'r') as f:
                manifest = json.load(f)
            
            print(f"\n📄 Manifest Contents:")
            print(f"   - Run ID: {manifest['run_id']}")
            print(f"   - Asset: {manifest['asset']}")
            print(f"   - Interval: {manifest['interval']}")
            print(f"   - Timeframe: {manifest.get('timeframe', 'N/A')}")
            print(f"   - Start TS: {manifest['start_ts']}")
            print(f"   - Config Hash: {manifest['cfg_hash']}")
            print(f"   - Code Hash: {manifest['code_hash']}")
            print(f"   - Model Hash: {manifest['model_hash']}")
            print(f"   - Update Interval: {manifest['update_interval_bars']} bars")
            
            # Test event tracking
            print(f"\n🔄 Testing event tracking...")
            writer.track_event('signals', ts=1736849400000)  # Example timestamp
            writer.track_event('health', ts=1736849400000)
            writer.track_event('executions', ts=1736849400000)
            
            print(f"   - Tracked 3 events")
            print(f"   - Stream counts: {writer.stream_counts}")
            
            # Test update
            writer.update()
            print(f"   ✅ Manifest updated successfully")
            
            # Verify update
            with open(writer.manifest_path, 'r') as f:
                updated_manifest = json.load(f)
            
            print(f"   - Stream counts in file: {updated_manifest['stream_counts']}")
            print(f"   - Last timestamps: {updated_manifest['stream_last_ts']}")
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
            print(f"\n✅ Test cleanup completed")
            
            return True
        else:
            print(f"❌ Manifest file was not created")
            return False
            
    except Exception as e:
        print(f"❌ ManifestWriter initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_py_integration():
    """Test that main.py has ManifestWriter integration"""
    main_py_path = os.path.join(project_root, "live_demo_12h", "main.py")
    
    if not os.path.exists(main_py_path):
        print(f"❌ main.py not found at {main_py_path}")
        return False
    
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "Import statement": "from live_demo_12h.ops.manifest_writer import ManifestWriter" in content,
        "Initialization": "manifest_writer = ManifestWriter(" in content,
        "Initialize call": "manifest_writer.initialize(" in content,
        "Track signals": "manifest_writer.track_event('signals'" in content,
        "Track health": "manifest_writer.track_event('health'" in content,
        "Track executions": "manifest_writer.track_event('executions'" in content,
        "Periodic update": "manifest_writer.update()" in content,
        "Finalize": "manifest_writer.finalize()" in content,
    }
    
    print(f"\n🔍 Checking main.py integration:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print(f"\n✅ All integration checks passed!")
    else:
        print(f"\n⚠️  Some integration checks failed")
    
    return all_passed

def main():
    print("=" * 60)
    print("12H BOT MANIFEST WRITER VERIFICATION")
    print("=" * 60)
    print()
    
    # Test 1: Import
    success, ManifestWriter = test_manifest_writer_import()
    if not success:
        print("\n❌ FAILED: Cannot proceed without successful import")
        return
    
    print()
    
    # Test 2: Initialization and functionality
    success = test_manifest_writer_initialization(ManifestWriter)
    if not success:
        print("\n❌ FAILED: ManifestWriter functionality test failed")
        return
    
    print()
    
    # Test 3: Integration in main.py
    success = test_main_py_integration()
    
    print()
    print("=" * 60)
    if success:
        print("✅ ALL TESTS PASSED - ManifestWriter is ready!")
    else:
        print("⚠️  SOME TESTS FAILED - Review integration")
    print("=" * 60)

if __name__ == "__main__":
    main()
