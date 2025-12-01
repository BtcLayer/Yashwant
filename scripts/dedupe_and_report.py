#!/usr/bin/env python3
"""
dedupe_and_report.py
Purpose: detect duplicates in signals and executions, write deduped outputs and produce diagnostics.
Usage: python scripts/dedupe_and_report.py
"""
import json
from pathlib import Path
import pandas as pd

base = Path('paper_trading_outputs')
frames = ['5m','1h','12h','24h']
reports = {}

for f in frames:
    folder = base / f / 'sheets_fallback'
    frame_report = {}

    # signals
    sig_file = None
    for cand in folder.glob('signals*.csv'):
        sig_file = cand
        break
    if sig_file and sig_file.exists():
        sig = pd.read_csv(sig_file)
        sig['ts'] = pd.to_numeric(sig['ts'], errors='coerce')
        sig['dt'] = pd.to_datetime(sig['ts'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')
        total = len(sig)
        # duplicates by full row
        dup_rows = sig.duplicated(keep='first').sum()
        # duplicates by dt
        dup_dt = sig.duplicated(subset=['dt'], keep='first').sum()

        # construct aggregated signals by dt
        # For required fields take mean/first
        agg = {}
        if 'pred_bps' in sig.columns:
            agg['pred_bps'] = 'mean'
        else:
            # find candidate
            pred_cands = [c for c in sig.columns if 'pred' in c and 'bps' in c]
            if pred_cands:
                sig['pred_bps'] = sig[pred_cands[0]]
                agg['pred_bps'] = 'mean'
        if 'S_top' in sig.columns:
            agg['S_top'] = 'first'
        if 'S_bot' in sig.columns:
            agg['S_bot'] = 'first'

        # also keep other columns first
        other_cols = [c for c in sig.columns if c not in ['ts','dt','pred_bps','S_top','S_bot']]
        for c in other_cols:
            agg[c] = 'first'

        sig_agg = sig.groupby('dt', sort=True).agg(agg).reset_index()
        out_file = folder / 'signals_dedup.csv'
        sig_agg.to_csv(out_file, index=False)

        frame_report['signals'] = {
            'file': str(sig_file), 'rows': total, 'dup_full_rows': int(dup_rows), 'dup_by_dt': int(dup_dt), 'out_file': str(out_file), 'out_rows': len(sig_agg)
        }
    else:
        frame_report['signals'] = 'missing'

    # execs
    exec_file = folder / 'executions_paper.csv'
    if exec_file.exists():
        execs = pd.read_csv(exec_file)
        total_e = len(execs)
        dup_e = execs.duplicated(keep='first').sum()
        # drop duplicates
        execs_dedup = execs.drop_duplicates().reset_index(drop=True)
        out_exec = folder / 'executions_dedup.csv'
        execs_dedup.to_csv(out_exec, index=False)
        frame_report['executions'] = {
            'file': str(exec_file), 'rows': total_e, 'dup_full_rows': int(dup_e), 'out_file': str(out_exec), 'out_rows': len(execs_dedup)
        }
    else:
        frame_report['executions'] = 'missing'

    reports[f] = frame_report

# write diagnostics
diag_file = base / 'dedupe_report.json'
diag_file.write_text(json.dumps(reports, indent=2), encoding='utf8')
print('Wrote dedupe report to', diag_file)
print(json.dumps(reports, indent=2))
