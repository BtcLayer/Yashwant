import os
import json
import sys
import datetime as dt
from os.path import abspath, dirname, join

# Reuse the repo's SheetsLogger
sys.path.insert(0, abspath(join(dirname(__file__), '..')))
from live_demo.sheets_logger import SheetsLogger


def main():
    repo_root = abspath(join(dirname(__file__), '..'))
    # Default to 1h config unless path passed as arg
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
    tab = tabs.get('health', 'health_metrics')

    # Ensure output root per-timeframe for logs
    tf = cfg['data'].get('interval', '1h')
    tf_root = join(repo_root, 'paper_trading_outputs', tf)
    os.makedirs(tf_root, exist_ok=True)

    # Prepare headers and row
    headers = {tab: ['ts_iso', 'who', 'message']}
    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    who = 'gsheet_probe'
    msg = f"probe-{now}"

    logger = SheetsLogger(creds_path, sheet_id, headers=headers, root_dir=tf_root)
    # Create headers/worksheet if needed
    logger.ensure_headers()
    logger.buffer(tab, [now, who, msg])
    logger.flush()

    print('SHEET_URL:', f'https://docs.google.com/spreadsheets/d/{sheet_id}')
    print('TAB:', tab)
    print('ROW:', now, who, msg)
    print('NOTE: If you do not see the row on the sheet, ensure the sheet is shared as Editor with the service account in creds JSON.')


if __name__ == '__main__':
    main()
