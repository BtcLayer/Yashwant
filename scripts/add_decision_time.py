#!/usr/bin/env python3
"""
add_decision_time.py
Map executions -> decision_time (nearest-left signal) and write diagnostics.

Produces:
 - paper_trading_outputs/<frame>/sheets_fallback/executions_paper_with_decision_time.csv
 - paper_trading_outputs/executions_decision_link_stats.json

Usage: python scripts/add_decision_time.py
"""
import json
from pathlib import Path
import pandas as pd
import numpy as np

def map_decision_time(base, frames):
	reports = {}
	for f in frames:
		folder = base / f / 'sheets_fallback'
		exec_file = folder / 'executions_paper.csv'
		# pick first signals file that starts with signals
		signals_file = None
		for cand in folder.glob('signals*.csv'):
			signals_file = cand
			break

		if not exec_file.exists():
			reports[f] = {'status':'no_executions_file', 'path': str(exec_file)}
			continue
		if not signals_file or not signals_file.exists():
			reports[f] = {'status':'no_signals_file', 'path': str(signals_file) if signals_file else None}
			continue

		execs = pd.read_csv(exec_file)
		sig = pd.read_csv(signals_file)

		# normalize and build dt
		execs['ts'] = pd.to_numeric(execs['ts'], errors='coerce')
		sig['ts'] = pd.to_numeric(sig['ts'], errors='coerce')
		execs['dt'] = pd.to_datetime(execs['ts'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')
		sig['dt'] = pd.to_datetime(sig['ts'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')

		if 'pred_bps' not in sig.columns:
			pred_cands = [c for c in sig.columns if 'pred' in c and 'bps' in c]
			if pred_cands:
				sig['pred_bps'] = sig[pred_cands[0]]
			else:
				sig['pred_bps'] = pd.NA

		agg_dict = {'pred_bps':'mean'}
		if 'S_top' in sig.columns:
			agg_dict['S_top'] = 'first'
		if 'S_bot' in sig.columns:
			agg_dict['S_bot'] = 'first'

		sig_agg = sig.groupby('dt', sort=True).agg(agg_dict)

		sig_ts = np.array([int(x.value // 10**6) for x in sig_agg.index])
		exec_ts = execs['ts'].to_numpy(dtype='float64')
		idxs = np.searchsorted(sig_ts, exec_ts, side='right') - 1

		decision_ts = []
		pred_at = []
		s_top = []
		s_bot = []
		latency_ms = []

		for i, ix in enumerate(idxs):
			if ix >= 0 and ix < len(sig_ts):
				dts = int(sig_ts[ix])
				decision_ts.append(dts)
				pred_at.append(sig_agg.iloc[ix]['pred_bps'])
				s_top.append(sig_agg.iloc[ix]['S_top'] if 'S_top' in sig_agg.columns else pd.NA)
				s_bot.append(sig_agg.iloc[ix]['S_bot'] if 'S_bot' in sig_agg.columns else pd.NA)
				latency_ms.append(int(exec_ts[i] - dts))
			else:
				decision_ts.append(pd.NA)
				pred_at.append(pd.NA)
				s_top.append(pd.NA)
				s_bot.append(pd.NA)
				latency_ms.append(pd.NA)

		execs['decision_ts'] = decision_ts
		execs['decision_dt'] = pd.to_datetime(execs['decision_ts'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')
		execs['pred_bps_at_decision'] = pred_at
		execs['S_top_at_decision'] = s_top
		execs['S_bot_at_decision'] = s_bot
		execs['latency_ms'] = latency_ms

		total = len(execs)
		mapped_count = int(execs['decision_ts'].notna().sum())
		mean_latency = float(execs['latency_ms'].dropna().astype(float).mean()) if mapped_count>0 else None
		median_latency = float(execs['latency_ms'].dropna().astype(float).median()) if mapped_count>0 else None
		unmatched = int(total - mapped_count)

		out_file = folder / 'executions_paper_with_decision_time.csv'
		execs.to_csv(out_file, index=False)

		reports[f] = {
			'status':'ok',
			'exec_rows': total,
			'mapped': mapped_count,
			'unmatched': unmatched,
			'mean_latency_ms': mean_latency,
			'median_latency_ms': median_latency,
			'out_file': str(out_file)
		}

	return reports

if __name__ == '__main__':
	base = Path('paper_trading_outputs')
	frames = ['5m','24h']
	r = map_decision_time(base, frames)
	diag_file = base / 'executions_decision_link_stats.json'
	diag_file.write_text(json.dumps(r, indent=2), encoding='utf8')
	print('Wrote mapping diagnostics to', diag_file)
	print(json.dumps(r, indent=2))
