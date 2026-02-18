#!/usr/bin/env python3
"""Quick diagnostic to check calibration data availability."""

import argparse
import gzip
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--logs-root', type=Path, required=True)
args = parser.parse_args()

logs_root = args.logs_root
print(f"Scanning: {logs_root}")
print("="*70)

# Signal files
sig_files = list(logs_root.rglob("signals/date=*/signals.jsonl")) + list(logs_root.rglob("signals.jsonl"))
sig_files = list(set(sig_files))
print(f"\nSignal files: {len(sig_files)}")
if sig_files:
    total_sigs = sum(1 for f in sig_files for _ in open(f) if _.strip())
    print(f"  Total signals: {total_sigs}")
else:
    total_sigs = 0

# Execution files
exec_files = (
    list(logs_root.rglob("execution_log/**/execution_log.jsonl.gz")) +
    list(logs_root.rglob("execution.jsonl")) +
    list(logs_root.rglob("order_intent.jsonl"))
)
exec_files = list(set(exec_files))
print(f"\nExecution files: {len(exec_files)}")
if exec_files:
    gzipped = sum(1 for f in exec_files if str(f).endswith('.gz'))
    print(f"  Gzipped: {gzipped}")

# P&L files
pnl_files = (
    list(logs_root.rglob("pnl_equity_log/**/pnl_equity_log.jsonl.gz")) +
    list(logs_root.rglob("fills.jsonl"))
)
pnl_files = list(set(pnl_files))
print(f"\nP&L files: {len(pnl_files)}")

if pnl_files:
    non_zero = 0
    total_pnl = 0
    
    for pf in pnl_files:
        try:
            if str(pf).endswith('.gz'):
                f = gzip.open(pf, 'rb')
                lines = [l.decode() for l in f.readlines()]
                f.close()
            else:
                lines = open(pf).readlines()
            
            for line in lines:
                if line.strip():
                    rec = json.loads(line)
                    pnl_val = rec.get('pnl_total_usd') or rec.get('realized_pnl', 0)
                    total_pnl += 1
                    if pnl_val != 0:
                        non_zero += 1
        except:
            continue
    
    print(f"  Total P&L records: {total_pnl}")
    print(f"  Non-zero P&L: {non_zero}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

if total_sigs > 0 and pnl_files and non_zero > 0:
    print(f"✅ Data available: {total_sigs} signals, {non_zero} outcomes")
    if non_zero >= 500:
        print("   ✨ SUFFICIENT for calibration!")
    elif non_zero >= 100:
        print(f"   ⚠️  Marginal - need {500-non_zero} more for stable calibration")
    else:
        print(f"   ⚠️  Insufficient - need {500-non_zero} more outcomes")
        days_needed = (500 - non_zero) // max(1, non_zero // 7)
        print(f"   Estimated: {days_needed} more days of trading")
else:
    if total_sigs == 0:
        print("❌ No signals found")
    elif not pnl_files:
        print("❌ No P&L files found")
    elif non_zero == 0:
        print("⚠️  No non-zero P&L - no completed trades")

print("="*70)
