"""
Unified Trade Summary Generator (LLM Bridge)
Consolidates Signals, Intent, Executions, and Outcomes into a flat JSONL for easier auditing.
"""

import json
import os
import gzip
import glob
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import argparse

def load_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    # Handle both .jsonl and .jsonl.gz
    open_func = gzip.open if path.endswith('.gz') else open
    try:
        with open_func(path, 'rt', encoding='utf-8') as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except:
                    continue
    except Exception as e:
        print(f"Error reading {path}: {e}")
    return rows

def to_ist_iso(ts):
    if not ts: return None
    try:
        t = float(ts)
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        if t > 1e12:
            dt = datetime.fromtimestamp(t / 1000.0, tz=timezone.utc).astimezone(tz_ist)
        else:
            dt = datetime.fromtimestamp(t, tz=timezone.utc).astimezone(tz_ist)
        return dt.isoformat()
    except:
        return None

def summarize(paper_root, output_file=None):
    log_base = os.path.join(paper_root, 'logs')
    if not os.path.exists(log_base):
        print(f"Error: Log directory not found at {log_base}")
        return

    # Topics and their relative paths
    topics = {
        'signals': 'signals',
        'executions': 'executions',
        'costs': 'costs',
        'intent': 'order_intent'
    }

    data_store = defaultdict(lambda: defaultdict(dict))

    for topic_key, topic_dir in topics.items():
        pattern = os.path.join(log_base, topic_dir, '**', f'*.jsonl*')
        files = glob.glob(pattern, recursive=True)
        print(f"Processing {topic_key}: found {len(files)} files")
        
        for f in files:
            rows = load_jsonl(f)
            for row in rows:
                ts = row.get('ts')
                # sanitized structure varies per topic
                san = row.get('sanitized', {})
                asset = san.get('symbol') or san.get('asset')
                
                if not ts or not asset: continue
                
                key = (asset, int(ts))
                
                if topic_key == 'signals':
                    data_store[key]['signal_alpha'] = san.get('decision', {}).get('alpha')
                    data_store[key]['s_model'] = san.get('model', {}).get('s_model')
                elif topic_key == 'intent':
                    intent_data = san.get('order_intent', {})
                    data_store[key]['intent_side'] = intent_data.get('side')
                    data_store[key]['intent_qty'] = intent_data.get('intent_qty')
                    data_store[key]['reason_codes'] = intent_data.get('reason_codes')
                elif topic_key == 'executions':
                    exec_data = san.get('exec', {})
                    data_store[key]['exec_side'] = exec_data.get('side')
                    data_store[key]['exec_price'] = exec_data.get('price')
                    data_store[key]['exec_qty'] = exec_data.get('qty')
                    data_store[key]['fill_px'] = exec_data.get('fill_px')
                elif topic_key == 'costs':
                    cost_data = san.get('costs', {})
                    data_store[key]['fee_usd'] = cost_data.get('fee')
                    data_store[key]['pnl_usd'] = cost_data.get('pnl_usd_bar')

    # Convert to flat list and sort by timestamp
    final_rows = []
    for (asset, ts), values in data_store.items():
        row = {
            "ts_ist": to_ist_iso(ts),
            "ts": ts,
            "asset": asset,
            **values
        }
        final_rows.append(row)

    final_rows.sort(key=lambda x: x['ts'])

    if not output_file:
        output_file = os.path.join(paper_root, 'trade_summary.jsonl')
        
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for row in final_rows:
            f.write(json.dumps(row) + "\n")
            
    print(f"Successfully generated trade summary: {len(final_rows)} events mapped.")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate unified trade summary bridge log.")
    parser.add_argument("--root", help="Paper trading root directory", default="paper_trading_outputs/5m")
    parser.add_argument("--out", help="Output filename", default=None)
    args = parser.parse_args()
    
    summarize(args.root, args.out)
