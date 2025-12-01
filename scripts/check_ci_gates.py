#!/usr/bin/env python3
"""
check_ci_gates.py
Simple gating script that inspects per-frame artifacts and produces a gates.json
Rules (defaults): bars >= 600, trades >= 30, OOF status == 'ok'
Writes: paper_trading_outputs/gates.json
Exits 0 if all frames pass; else writes summary with pass/fail per-frame.
"""
import json
from pathlib import Path
import pandas as pd

base = Path('paper_trading_outputs')
frames = ['5m','1h','12h','24h']

min_bars = 600
min_trades = 30

adv_file = base / 'adv20_summary.json'
oof_file = base / 'oof_calibration_summary.json'

adv = {}
oof = {}
if adv_file.exists():
    adv = json.loads(adv_file.read_text(encoding='utf8'))
if oof_file.exists():
    oof = json.loads(oof_file.read_text(encoding='utf8'))

report = {}
all_pass = True
for f in frames:
    folder = base / f / 'sheets_fallback'
    bars = None
    trades = None
    # count bars from signals_dedup.csv
    sfile = folder / 'signals_dedup.csv'
    if sfile.exists():
        try:
            df = pd.read_csv(sfile)
            bars = len(df)
        except Exception:
            bars = None
    else:
        # fallback to signals*.csv
        ss = list(folder.glob('signals*.csv'))
        if ss:
            try:
                df = pd.read_csv(ss[0])
                bars = len(df)
            except Exception:
                bars = None

    # count trades
    efile = folder / 'executions_dedup.csv'
    if not efile.exists():
        # accept executions_from_5m_agg as valid
        efile = folder / 'executions_from_5m_agg.csv'
    if efile.exists():
        try:
            edf = pd.read_csv(efile)
            trades = len(edf)
        except Exception:
            trades = None

    adv_status = adv.get(f, {}).get('status', 'no_data')
    oof_status = oof.get(f, {}).get('status', 'no_data')

    pass_bars = (bars is not None) and bars >= min_bars
    pass_trades = (trades is not None) and trades >= min_trades
    pass_oof = (oof_status == 'ok')

    frame_pass = pass_bars and pass_trades and pass_oof

    report[f] = {
        'bars': bars,
        'trades': trades,
        'adv_status': adv_status,
        'oof_status': oof_status,
        'pass_bars': pass_bars,
        'pass_trades': pass_trades,
        'pass_oof': pass_oof,
        'frame_pass': frame_pass
    }
    if not frame_pass:
        all_pass = False

out_file = base / 'gates.json'
out = {'summary_pass': all_pass, 'frames': report, 'min_bars': min_bars, 'min_trades': min_trades}
out_file.write_text(json.dumps(out, indent=2), encoding='utf8')
print('Wrote gates to', out_file)
print(json.dumps(out, indent=2))

# non-zero exit when gates fail to make it CI friendly
if not all_pass:
    raise SystemExit(2)
