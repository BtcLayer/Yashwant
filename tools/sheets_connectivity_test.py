import json
import os
import sys
import datetime as dt
from os.path import abspath, dirname, join

# Make sure we can import live_demo.sheets_logger if needed
sys.path.insert(0, abspath(join(dirname(__file__), '..')))

try:
    from live_demo.sheets_logger import SheetsLogger
except Exception as e:
    print(f"ERROR: Unable to import SheetsLogger: {e}")
    sys.exit(2)


def main():
    # Default to 1h config
    repo_root = abspath(join(dirname(__file__), '..'))
    cfg_path = join(repo_root, 'live_demo_1h', 'config.json')
    if len(sys.argv) > 1:
        cfg_path = abspath(sys.argv[1])
    if not os.path.exists(cfg_path):
        print(f"ERROR: Config not found: {cfg_path}")
        sys.exit(2)

    with open(cfg_path, 'r', encoding='utf-8') as fh:
        cfg = json.load(fh)

    sheet_id = cfg['sheets']['sheet_id']
    creds_path = cfg['sheets'].get('creds_json')
    creds_path = abspath(join(repo_root, creds_path)) if creds_path else None

    tabs = cfg['sheets']['tabs']
    test_tab = tabs.get('health', 'health_ping')
    # minimal header
    headers = {test_tab: ['ts_iso', 'who', 'message']}

    # use per-timeframe root (1h)
    tf_root = join(repo_root, 'paper_trading_outputs', '1h')
    os.makedirs(tf_root, exist_ok=True)

    logger = SheetsLogger(creds_path, sheet_id, headers=headers, root_dir=tf_root)
    logger.ensure_headers()

    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    logger.buffer(test_tab, [now, 'sheets_connectivity_test', 'ping'])
    logger.flush()
    print('INFO: Flush attempted; check Google Sheet or paper_trading_outputs/1h/sheets_fallback.')


if __name__ == '__main__':
    main()
