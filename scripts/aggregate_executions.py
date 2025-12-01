#!/usr/bin/env python3
"""
Aggregate deduped 5m executions into higher-frame execution files (1h, 12h).
Writes to paper_trading_outputs/<frame>/sheets_fallback/executions_from_5m_agg.csv
Also writes a summary JSON: paper_trading_outputs/aggregation_summary.json
"""
import json
from pathlib import Path
import pandas as pd
import numpy as np

base = Path('paper_trading_outputs')
input_frame = '5m'
input_file = base / input_frame / 'sheets_fallback' / 'executions_dedup.csv'
if not input_file.exists():
    print('No 5m deduped executions found at', input_file)
    raise SystemExit(1)

exec5 = pd.read_csv(input_file)
# parse dt
exec5['dt'] = pd.to_datetime(exec5['ts_iso'])
exec5 = exec5.sort_values('dt').reset_index(drop=True)

# target frames and pandas offset alias -> floor rule
targets = {
    '1h': 'H',
    '12h': '12H'
}

summary = {}

for tgt, alias in targets.items():
    df = exec5.copy()
    # floor to period start
    df['period_start'] = df['dt'].dt.floor(alias)

    # aggregate
    def weighted_avg(col, weight):
        def fn(x):
            w = x[weight].astype(float).fillna(0)
            v = x[col].astype(float).fillna(0)
            if w.sum() == 0:
                return float(v.mean()) if len(v) else np.nan
            return float((v * w).sum() / w.sum())
        return fn

    grp = df.groupby('period_start')
    # basic aggregations
    agg = grp.agg({
        'qty': 'sum',
        'notional_usd': 'sum',
        'realized_pnl': 'sum',
        'fee': 'sum',
        'impact': 'sum',
        'equity': 'last'
    })

    # weighted averages for prices
    agg['fill_price'] = grp.apply(lambda g: weighted_avg('fill_price', 'notional_usd')(g))
    agg['mid_price'] = grp.apply(lambda g: weighted_avg('mid_price', 'notional_usd')(g))

    # side and raw concatenation
    agg['side'] = grp['side'].apply(lambda s: ','.join(sorted(set(s.astype(str)))))
    agg['raw'] = grp['raw'].apply(lambda s: '[' + ','.join(s.astype(str).tolist()) + ']')

    # period index -> ts fields
    agg = agg.reset_index()
    agg['ts_iso'] = agg['period_start'].dt.tz_convert(None).apply(lambda x: x.isoformat())
    agg['ts'] = agg['period_start'].astype('int64') // 10**6
    # reorder columns to match original file close enough
    cols = ['ts_iso','ts','side','qty','mid_price','fill_price','notional_usd','realized_pnl','fee','impact','equity','raw']
    agg = agg[[c for c in cols if c in agg.columns]]

    # write to file under frame
    out_dir = base / tgt / 'sheets_fallback'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'executions_from_5m_agg.csv'
    agg.to_csv(out_file, index=False)

    summary[tgt] = {
        'rows_in': len(exec5),
        'rows_out': len(agg),
        'out_file': str(out_file)
    }

# write global summary
out_summary = base / 'aggregation_summary.json'
out_summary.write_text(json.dumps(summary, indent=2), encoding='utf8')
print('Wrote aggregation_summary.json to', out_summary)
print(json.dumps(summary, indent=2))
