import os
import json
import sys

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception as e:
    print(f"ERROR: Missing Google Sheets dependencies: {e}")
    sys.exit(1)


def main():
    # Resolve paths relative to this tools directory
    live_demo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    cfg_path = os.path.join(live_demo_dir, 'config.json')
    if not os.path.exists(cfg_path):
        print(f"ERROR: Config not found at {cfg_path}")
        sys.exit(2)

    with open(cfg_path, 'r', encoding='utf-8') as fp:
        cfg = json.load(fp)

    sheets_cfg = cfg.get('sheets', {})
    sheet_id = sheets_cfg.get('sheet_id')
    creds_rel = sheets_cfg.get('creds_json')
    if not sheet_id:
        print("ERROR: sheet_id missing in config")
        sys.exit(3)

    creds_path = creds_rel
    if creds_path and not os.path.isabs(creds_path):
        # First try relative to project root (parent of live_demo)
        project_root = os.path.abspath(os.path.join(live_demo_dir, os.pardir))
        candidate = os.path.join(project_root, creds_path)
        if os.path.exists(candidate):
            creds_path = candidate
        else:
            # Fallback to relative to live_demo directory
            creds_path = os.path.join(live_demo_dir, creds_path)
    if not creds_path or not os.path.exists(creds_path):
        print(f"ERROR: creds_json not found or missing: {creds_path}")
        sys.exit(4)

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    try:
        credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(sheet_id)
        titles = [ws.title for ws in sh.worksheets()]
        print("OK:WORKSHEETS:" + ",".join(titles))
    except Exception as e:
        print(f"ERROR: Failed to list worksheets: {e}")
        sys.exit(5)


if __name__ == '__main__':
    main()
