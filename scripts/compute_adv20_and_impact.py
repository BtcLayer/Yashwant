#!/usr/bin/env python3
"""
compute_adv20_and_impact.py
Compute ADV20 per date (20-day rolling mean of daily abs notional) and recompute impact per trade.
Writes:
 - paper_trading_outputs/<frame>/sheets_fallback/adv20_by_date.csv
 - paper_trading_outputs/<frame>/sheets_fallback/executions_with_adv20.csv
 - paper_trading_outputs/adv20_summary.json
"""
import json
from pathlib import Path
import pandas as pd
import numpy as np

base = Path('paper_trading_outputs')
frames = ['5m','1h','12h','24h']
reports = {}

k = 2.0  # impact multiplier

for f in frames:
    folder = base / f / 'sheets_fallback'
    exec_file = folder / 'executions_dedup.csv'
    if not exec_file.exists():
        exec_file = folder / 'executions_paper.csv'
    if not exec_file.exists():
        reports[f] = {'status':'no_execs'}
        continue

    execs = pd.read_csv(exec_file)
    if 'notional_usd' not in execs.columns:
        if 'fill_price' in execs.columns and 'qty' in execs.columns:
            execs['notional_usd'] = pd.to_numeric(execs['fill_price'], errors='coerce') * pd.to_numeric(execs['qty'], errors='coerce')
        elif 'mid_price' in execs.columns and 'qty' in execs.columns:
            execs['notional_usd'] = pd.to_numeric(execs['mid_price'], errors='coerce') * pd.to_numeric(execs['qty'], errors='coerce')
        else:
            execs['notional_usd'] = np.nan

    execs['ts'] = pd.to_numeric(execs['ts'], errors='coerce')
    execs['dt'] = pd.to_datetime(execs['ts'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')
    execs['date'] = execs['dt'].dt.date

    daily = execs.groupby('date')['notional_usd'].apply(lambda s: s.abs().sum()).rename('daily_notional')
    adv20 = daily.rolling(20, min_periods=1).mean().rename('adv20')

    adv_df = pd.concat([daily, adv20], axis=1).reset_index()
    out_adv = folder / 'adv20_by_date.csv'
    adv_df.to_csv(out_adv, index=False)

    # map adv20 to execs
    adv_map = adv20.to_dict()
    execs['adv20'] = execs['date'].map(adv_map)

    # compute impact_bps = k * (notional / adv20)
    def compute_impact(row):
        if pd.isna(row['adv20']) or row['adv20'] == 0 or pd.isna(row['notional_usd']):
            return pd.NA
        return float(k * (row['notional_usd'] / row['adv20']))

    execs['impact_calc_bps'] = execs.apply(compute_impact, axis=1)

    # comparison with existing impact if available
    if 'impact' in execs.columns:
        execs['impact'] = pd.to_numeric(execs['impact'], errors='coerce')
        execs['impact_diff'] = execs['impact_calc_bps'] - execs['impact']

    out_exec = folder / 'executions_with_adv20.csv'
    execs.to_csv(out_exec, index=False)

    reports[f] = {'status':'ok','exec_rows': len(execs),'adv20_file': str(out_adv), 'out_exec': str(out_exec)}

# write global report
out = base / 'adv20_summary.json'
out.write_text(json.dumps(reports, indent=2), encoding='utf8')
print('Wrote adv20 summary to', out)
print(json.dumps(reports, indent=2))
