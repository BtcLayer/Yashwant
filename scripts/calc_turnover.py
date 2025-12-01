#!/usr/bin/env python3
"""
calc_turnover.py
Compute corrected turnover per frame using per-bar absolute executed notional (sum |qty*price| or notional_usd).
Writes outputs: paper_trading_outputs/turnover_report.json
"""
import json
from pathlib import Path
import pandas as pd
import numpy as np

base = Path('paper_trading_outputs')
frames = ['5m','1h','12h','24h']
bars_per_day = {'5m':288,'1h':24,'12h':2,'24h':1}
reports = {}

for f in frames:
    folder = base / f / 'sheets_fallback'
    # prefer deduped execs
    exec_file = folder / 'executions_dedup.csv'
    if not exec_file.exists():
        exec_file = folder / 'executions_paper.csv'
    eq_file = folder / [p for p in (folder.glob('equity*.csv'))][0].name if any(folder.glob('equity*.csv')) else None

    # load equity
    eq_path = None
    for cand in folder.glob('equity*.csv'):
        eq_path = cand
        break
    if not eq_path:
        reports[f] = {'status':'no_equity'}
        continue

    eq = pd.read_csv(eq_path)
    eq['ts'] = pd.to_numeric(eq['ts'], errors='coerce')
    eq['dt'] = pd.to_datetime(eq['ts'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')
    eq_unique = eq.drop_duplicates('dt').set_index('dt').sort_index()
    mean_equity = float(eq_unique['equity'].mean()) if 'equity' in eq_unique.columns else None

    if not exec_file.exists():
        reports[f] = {'status':'no_execs'}
        continue

    execs = pd.read_csv(exec_file)
    execs['ts'] = pd.to_numeric(execs['ts'], errors='coerce')
    execs['dt'] = pd.to_datetime(execs['ts'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')

    # compute notional per trade
    if 'notional_usd' in execs.columns:
        execs['notional_usd'] = pd.to_numeric(execs['notional_usd'], errors='coerce')
    else:
        # compute from qty*fill_price or qty*mid_price
        if 'fill_price' in execs.columns and 'qty' in execs.columns:
            execs['notional_usd'] = pd.to_numeric(execs['fill_price'], errors='coerce') * pd.to_numeric(execs['qty'], errors='coerce')
        elif 'mid_price' in execs.columns and 'qty' in execs.columns:
            execs['notional_usd'] = pd.to_numeric(execs['mid_price'], errors='coerce') * pd.to_numeric(execs['qty'], errors='coerce')
        else:
            execs['notional_usd'] = np.nan

    trades_by_bar_abs = execs.groupby('dt')['notional_usd'].apply(lambda s: s.abs().sum())
    mean_abs_notional = float(trades_by_bar_abs.mean()) if len(trades_by_bar_abs)>0 else 0.0

    report = {'exec_rows': len(execs), 'mean_abs_notional': mean_abs_notional, 'mean_equity': mean_equity}
    if mean_equity and mean_equity > 0:
        report['turnover_bps_day_approx'] = mean_abs_notional * bars_per_day[f] / mean_equity * 1e4
    else:
        report['turnover_bps_day_approx'] = None

    # also compute old (net signed delta method) for reference
    if 'side' in execs.columns:
        execs['side_sign'] = execs['side'].apply(lambda s: 1 if str(s).upper().strip()=='BUY' else (-1 if str(s).upper().strip()=='SELL' else 0))
        not_by_bar_signed = execs.groupby('dt').apply(lambda g: (g['side_sign']*g['notional_usd']).sum()).rename('net_notional')
        dnet = not_by_bar_signed.diff().abs().fillna(0)
        mean_dnotional = float(dnet.mean())
        report['turnover_net_signed_method_bps_day'] = mean_dnotional * bars_per_day[f] / mean_equity * 1e4 if mean_equity and mean_equity>0 else None
    else:
        report['turnover_net_signed_method_bps_day'] = None

    reports[f] = report

# write
out_file = base / 'turnover_report.json'
out_file.write_text(json.dumps(reports, indent=2), encoding='utf8')
print('Wrote turnover report to', out_file)
print(json.dumps(reports, indent=2))
