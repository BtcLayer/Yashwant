"""
UNIFIED MULTI-TIMEFRAME RETRAINING SCRIPT
==========================================
Retrain all timeframes (5m, 1h, 12h, 24h) with one command

Usage:
  python retrain_all_timeframes.py --timeframes 5m 1h 12h 24h
  python retrain_all_timeframes.py --timeframes 5m  # Just 5m
  python retrain_all_timeframes.py  # All timeframes

Author: Senior Quant ML Engineer
Date: 2026-01-06
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import argparse

SCRIPTS = {
    '5m': 'retrain_5m_production_v2.py',
    '1h': 'retrain_1h_production.py',
    '12h': 'retrain_12h_production.py',
    '24h': 'retrain_24h_production.py'
}

def main():
    parser = argparse.ArgumentParser(description='Retrain all timeframe models')
    parser.add_argument('--timeframes', nargs='+', default=['5m', '1h', '12h', '24h'],
                       choices=['5m', '1h', '12h', '24h'],
                       help='Timeframes to retrain')
    parser.add_argument('--stop-on-failure', action='store_true',
                       help='Stop if any timeframe fails validation')
    
    args = parser.parse_args()
    
    print("="*80)
    print("MULTI-TIMEFRAME MODEL RETRAINING")
    print("="*80)
    print(f"Start time: {datetime.now()}")
    print(f"Timeframes: {', '.join(args.timeframes)}")
    print("="*80)
    
    results = {}
    
    for tf in args.timeframes:
        script = SCRIPTS[tf]
        
        if not Path(script).exists():
            print(f"\n✗ Script not found: {script}")
            print(f"  Skipping {tf}")
            results[tf] = 'SCRIPT_MISSING'
            continue
        
        print(f"\n{'='*80}")
        print(f"RETRAINING {tf.upper()} MODEL")
        print(f"{'='*80}")
        
        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=False,
                text=True,
                check=True
            )
            
            results[tf] = 'SUCCESS'
            print(f"\n✓ {tf} model retrained successfully")
            
        except subprocess.CalledProcessError as e:
            results[tf] = 'FAILED'
            print(f"\n✗ {tf} model retraining FAILED")
            print(f"  Exit code: {e.returncode}")
            
            if args.stop_on_failure:
                print("\n--stop-on-failure flag set. Aborting.")
                break
        
        except Exception as e:
            results[tf] = 'ERROR'
            print(f"\n✗ {tf} model retraining ERROR: {str(e)}")
            
            if args.stop_on_failure:
                print("\n--stop-on-failure flag set. Aborting.")
                break
    
    # Summary
    print("\n" + "="*80)
    print("RETRAINING SUMMARY")
    print("="*80)
    
    for tf in args.timeframes:
        status = results.get(tf, 'NOT_RUN')
        symbol = {
            'SUCCESS': '✓',
            'FAILED': '✗',
            'ERROR': '✗',
            'SCRIPT_MISSING': '⚠',
            'NOT_RUN': '-'
        }[status]
        
        print(f"{symbol} {tf:>4}: {status}")
    
    success_count = sum(1 for v in results.values() if v == 'SUCCESS')
    total_count = len(args.timeframes)
    
    print(f"\nSuccess rate: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("\n✓ ALL MODELS RETRAINED SUCCESSFULLY")
        print("\nNext steps:")
        print("1. Stop running bot (Ctrl+C)")
        print("2. Clear cache for all timeframes")
        print("3. Restart bot")
        print("4. Monitor for 1 hour")
        return 0
    else:
        print("\n⚠ SOME MODELS FAILED - Review logs above")
        return 1

if __name__ == '__main__':
    sys.exit(main())
