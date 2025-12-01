#!/usr/bin/env python3
"""
oof_calibration.py
Simple OOF linear calibration (no sklearn) with purge/embargo for time-series.
Saves: paper_trading_outputs/<frame>/sheets_fallback/oof_calibration.json
"""
import json
from pathlib import Path
import pandas as pd
import numpy as np

base = Path('paper_trading_outputs')
frames = ['5m','1h','12h','24h']  # try all processing frames

n_splits = 5
purge = 1  # bars to purge before test
embargo = 1  # bars to embargo after test
threshold_bps = 15.0
reports = {}

for f in frames:
    folder = base / f / 'sheets_fallback'
    signals_file = None
    for cand in folder.glob('signals*.csv'):
        signals_file = cand
        break
    eq_file = None
    for cand in folder.glob('equity*.csv'):
        eq_file = cand
        break

    if not signals_file or not signals_file.exists() or not eq_file or not eq_file.exists():
        reports[f] = {'status':'missing_inputs'}
        continue

    sig = pd.read_csv(signals_file)
    eq = pd.read_csv(eq_file)

    # build dt
    sig['ts'] = pd.to_numeric(sig['ts'], errors='coerce')
    eq['ts'] = pd.to_numeric(eq['ts'], errors='coerce')
    sig['dt'] = pd.to_datetime(sig['ts'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')
    eq['dt'] = pd.to_datetime(eq['ts'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')

    # aggregate signals by dt
    if 'pred_bps' not in sig.columns:
        pred_cands = [c for c in sig.columns if 'pred' in c and 'bps' in c]
        if pred_cands:
            sig['pred_bps'] = sig[pred_cands[0]]
        else:
            reports[f] = {'status':'no_pred_bps'}
            continue

    sig_agg = sig.groupby('dt').agg({'pred_bps':'mean'})
    eq2 = eq[['dt','equity']].drop_duplicates('dt').set_index('dt').sort_index()
    eq2['r'] = eq2['equity'].pct_change()
    eq2['realized_bps'] = eq2['r'].shift(-1) * 1e4

    # join
    joined = sig_agg.join(eq2[['realized_bps']], how='inner').dropna()
    joined = joined.reset_index()
    if len(joined) < n_splits*2:
        reports[f] = {'status':'too_few_bars', 'bars': len(joined)}
        continue

    n = len(joined)
    fold_size = max(1, n // n_splits)
    oof_preds = np.full(n, np.nan)
    coefs = []

    for k in range(n_splits):
        start = k*fold_size
        end = (k+1)*fold_size if k < n_splits-1 else n
        test_idx = np.arange(start, end)
        # train idx everything else
        train_idx = np.setdiff1d(np.arange(n), test_idx)
        # purge/embargo removal
        purge_start = max(0, start - purge)
        purge_end = min(n, end + embargo)
        # remove indices in [purge_start, purge_end)
        mask = ~((train_idx >= purge_start) & (train_idx < purge_end))
        train_idx2 = train_idx[mask]
        if len(train_idx2) < 2:
            continue

        X_train = joined.loc[train_idx2, 'pred_bps'].values.reshape(-1,1)
        y_train = joined.loc[train_idx2, 'realized_bps'].values
        # linear fit via least squares y = a + b*x
        A = np.vstack([np.ones(len(X_train)), X_train.ravel()]).T
        sol, *_ = np.linalg.lstsq(A, y_train, rcond=None)
        a, b = float(sol[0]), float(sol[1])
        coefs.append({'fold': k, 'a':a, 'b':b, 'train_size': len(train_idx2), 'test_size': len(test_idx)})

        X_test = joined.loc[test_idx, 'pred_bps'].values.reshape(-1,1)
        if len(X_test)>0:
            yhat = a + b * X_test.ravel()
            oof_preds[test_idx] = yhat

    # aggregate a,b
    if len(coefs) == 0:
        reports[f] = {'status':'no_valid_splits'}
        continue

    a_mean = float(np.mean([c['a'] for c in coefs]))
    b_mean = float(np.mean([c['b'] for c in coefs]))

    joined['oof_pred_bps'] = oof_preds
    # compute fraction inside band
    calib_vals = a_mean + b_mean * joined['pred_bps']
    frac_in_band = float((abs(calib_vals) <= threshold_bps).mean())

    # save outputs
    out_file = folder / 'oof_calibration.csv'
    joined.to_csv(out_file, index=False)
    meta = {
        'status':'ok', 'folds':coefs, 'a_mean':a_mean, 'b_mean':b_mean, 'fraction_in_15bps_band': frac_in_band, 'out_file': str(out_file), 'rows': len(joined)
    }
    reports[f] = meta
    # persist per-frame CV metadata (for CI and artifact tracking)
    frame_meta_file = folder / 'oof_cv_meta.json'
    frame_meta = {k: meta[k] for k in ['status','folds','a_mean','b_mean','fraction_in_15bps_band','rows']}
    frame_meta['purge'] = purge
    frame_meta['embargo'] = embargo
    frame_meta['n_splits'] = n_splits
    frame_meta_file.write_text(json.dumps(frame_meta, indent=2), encoding='utf8')

# write global summary
out = base / 'oof_calibration_summary.json'
out.write_text(json.dumps(reports, indent=2), encoding='utf8')
print('Wrote OOF calibration summary to', out)
print(json.dumps(reports, indent=2))
