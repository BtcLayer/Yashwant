from typing import Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials
import os
import csv
import json


class SheetsLogger:
    def __init__(self, creds_json_path: Optional[str], sheet_id: str, headers: Optional[Dict[str, List[str]]] = None, root_dir: Optional[str] = None):
        self.sheet_id = sheet_id
        self.gc = None
        self._warned_no_gc = False
        self._warned_api_error = False
        self._root_dir_override = os.path.abspath(root_dir) if root_dir else None
        self._sa_email: Optional[str] = None
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        if creds_json_path:
            try:
                # Capture service account email for helpful diagnostics
                try:
                    with open(creds_json_path, 'r', encoding='utf-8') as fh:
                        info = json.load(fh)
                        self._sa_email = info.get('client_email')
                except Exception:
                    self._sa_email = None
                credentials = Credentials.from_service_account_file(creds_json_path, scopes=scopes)
                self.gc = gspread.authorize(credentials)
                try:
                    out_dir = self._paper_root()
                    os.makedirs(out_dir, exist_ok=True)
                    with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                        msg = '[SheetsLogger] Google Sheets client initialized via file credentials.'
                        if self._sa_email:
                            msg += f" service_account={self._sa_email}"
                        fh.write(msg + '\n')
                except OSError:
                    pass
            except Exception as e:
                # Log detailed reason once per run root
                try:
                    out_dir = self._paper_root()
                    os.makedirs(out_dir, exist_ok=True)
                    import traceback
                    with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                        fh.write('[SheetsLogger] Failed to initialize Google Sheets client from file; falling back. ' + repr(e) + '\n')
                        if self._sa_email:
                            fh.write(f"[SheetsLogger] service_account={self._sa_email}\n")
                        fh.write(traceback.format_exc() + '\n')
                except OSError:
                    pass
                self.gc = None
        # Fallback: allow inline credentials via environment variable
        if self.gc is None:
            inline = os.environ.get('GOOGLE_SHEETS_JSON')
            if inline:
                try:
                    info = json.loads(inline)
                    self._sa_email = info.get('client_email') or self._sa_email
                    credentials = Credentials.from_service_account_info(info, scopes=scopes)
                    self.gc = gspread.authorize(credentials)
                    try:
                        out_dir = self._paper_root()
                        os.makedirs(out_dir, exist_ok=True)
                        with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                            msg = '[SheetsLogger] Google Sheets client initialized via env credentials.'
                            if self._sa_email:
                                msg += f" service_account={self._sa_email}"
                            fh.write(msg + '\n')
                    except OSError:
                        pass
                except Exception as e:
                    try:
                        out_dir = self._paper_root()
                        os.makedirs(out_dir, exist_ok=True)
                        import traceback
                        with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                            fh.write('[SheetsLogger] Failed to initialize Google Sheets client from env; falling back. ' + repr(e) + '\n')
                            fh.write(traceback.format_exc() + '\n')
                    except OSError:
                        pass
                    self.gc = None
        if self.gc is None:
            # Gracefully degrade to CSV fallback when creds are invalid or unreadable
            try:
                out_dir = self._paper_root()
                os.makedirs(out_dir, exist_ok=True)
                import traceback
                with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                    fh.write('[SheetsLogger] Google Sheets disabled or credentials invalid; using local CSV fallback.\n')
            except OSError:
                pass
        self._buffers: Dict[str, List[List]] = {}
        self._headers = headers or {}
        self._initialized_tabs: Dict[str, bool] = {}

    def _paper_root(self) -> str:
        """Resolve the base paper_trading_outputs directory.
        Policy: Use repo-local path, but if PAPER_TRADING_ROOT points to a subfolder
        inside that repo path, honor it (for per-timeframe segregation).
        """
        demo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))  # .../live_demo
        repo_root = os.path.abspath(os.path.join(demo_dir, os.pardir))       # .../MetaStackerBandit
        repo_paper = os.path.abspath(os.path.join(repo_root, 'paper_trading_outputs'))
        if self._root_dir_override:
            try:
                if os.path.commonpath([self._root_dir_override, repo_paper]) == repo_paper:
                    return self._root_dir_override
            except Exception:
                pass
        env = os.environ.get('PAPER_TRADING_ROOT')
        if env:
            try:
                env_abs = os.path.abspath(env)
                # Only honor env if it stays within repo_paper path
                if os.path.commonpath([env_abs, repo_paper]) == repo_paper:
                    return env_abs
            except Exception:
                pass
        return repo_paper

    def ensure_headers(self):
        """
        Proactively create tabs and insert header rows (if provided) before any data rows are appended.
        Safe to call multiple times.
        """
        if not self.gc or not self._headers or not self.sheet_id:
            return
        # Open sheet; if it fails via gspread, just return
        try:
            sh = self.gc.open_by_key(self.sheet_id)
        except gspread.exceptions.APIError as e:
            # Log once with helpful guidance
            try:
                out_dir = self._paper_root()
                os.makedirs(out_dir, exist_ok=True)
                with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                    fh.write('[SheetsLogger] APIError in ensure_headers when opening sheet. ' + repr(e) + '\n')
                    if self._sa_email:
                        fh.write(f"[SheetsLogger] Ensure the sheet is shared with service account: {self._sa_email}\n")
                    fh.write(f"[SheetsLogger] Sheet URL: https://docs.google.com/spreadsheets/d/{self.sheet_id}\n")
            except OSError:
                pass
            return
        except Exception as e:
            # Log unexpected errors to live_errors.log for diagnosis and bail out of header init
            try:
                out_dir = self._paper_root()
                os.makedirs(out_dir, exist_ok=True)
                import traceback

                with open(
                    os.path.join(out_dir, "live_errors.log"), "a", encoding="utf-8"
                ) as fh:
                    fh.write(
                        "[SheetsLogger] Unexpected error in ensure_headers: "
                        + repr(e)
                        + "\n"
                    )
                    fh.write(traceback.format_exc() + "\n")
            except OSError:
                pass
            return
        for tab, header in self._headers.items():
            try:
                try:
                    ws = sh.worksheet(tab)
                except gspread.WorksheetNotFound:
                    ws = sh.add_worksheet(title=tab, rows=1000, cols=30)
                # If first row empty, write header
                try:
                    first_row = ws.row_values(1)
                    if not first_row and header:
                        ws.append_row(header, value_input_option="RAW")
                except (gspread.exceptions.APIError, gspread.WorksheetNotFound):
                    pass
                self._initialized_tabs[tab] = True
            except gspread.exceptions.APIError:
                # Best-effort: continue with other tabs
                continue

    def buffer(self, tab: str, row: List):
        if tab not in self._buffers:
            self._buffers[tab] = []
        self._buffers[tab].append(row)

    def flush(self):
        if not self.gc:
            # No Sheets client configured; write buffers to local CSV fallback instead (centralized root)
            try:
                # Best-effort: log once so users know Sheets is disabled
                if not self._warned_no_gc:
                    # Centralize under repo-local paper_trading_outputs (or PAPER_TRADING_ROOT if set)
                    out_dir = self._paper_root()
                    os.makedirs(out_dir, exist_ok=True)
                    with open(
                        os.path.join(out_dir, "live_errors.log"), "a", encoding="utf-8"
                    ) as fh:
                        fh.write(
                            "[SheetsLogger] No Google Sheets credentials configured; using local CSV fallback.\n"
                        )
                    self._warned_no_gc = True
            except OSError:
                pass
            self._flush_to_csv_fallback()
            return
        if not self.sheet_id:
            self._flush_to_csv_fallback()
            return
        try:
            sh = self.gc.open_by_key(self.sheet_id)
        except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound) as e:
            # Fallback to local CSV for all tabs
            try:
                if not self._warned_api_error:
                    out_dir = self._paper_root()
                    os.makedirs(out_dir, exist_ok=True)
                    with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                        fh.write('[SheetsLogger] Google Sheets API error on open_by_key; falling back to local CSV. Ensure the sheet_id is correct and the service account has access. ' + repr(e) + '\n')
                        if self._sa_email:
                            fh.write(f"[SheetsLogger] Ensure the sheet is shared with service account: {self._sa_email}\n")
                        fh.write(f"[SheetsLogger] Sheet URL: https://docs.google.com/spreadsheets/d/{self.sheet_id}\n")
                    self._warned_api_error = True
            except OSError:
                pass
            self._flush_to_csv_fallback()
            return
        except Exception as e:
            # Catch any other unexpected errors when opening the sheet and fall back
            try:
                if not self._warned_api_error:
                    out_dir = self._paper_root()
                    os.makedirs(out_dir, exist_ok=True)
                    import traceback

                    with open(
                        os.path.join(out_dir, "live_errors.log"), "a", encoding="utf-8"
                    ) as fh:
                        fh.write(
                            "[SheetsLogger] Unexpected error while opening sheet; falling back to CSV. "
                            + repr(e)
                            + "\n"
                        )
                        fh.write(traceback.format_exc() + "\n")
                    self._warned_api_error = True
            except OSError:
                pass
            self._flush_to_csv_fallback()
            return
        for tab, rows in list(self._buffers.items()):
            if not rows:
                continue
            try:
                # Resolve or create worksheet; on any API error, fall back to CSV for this tab
                try:
                    try:
                        ws = sh.worksheet(tab)
                    except gspread.WorksheetNotFound:
                        try:
                            ws = sh.add_worksheet(title=tab, rows=1000, cols=30)
                        except gspread.exceptions.APIError as e:
                            # Cannot create worksheet (permissions/limits). Fallback to CSV.
                            try:
                                out_dir = self._paper_root()
                                os.makedirs(out_dir, exist_ok=True)
                                with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                                    fh.write('[SheetsLogger] APIError creating worksheet ' + str(tab) + '; using CSV fallback. ' + repr(e) + '\n')
                                    if self._sa_email:
                                        fh.write(f"[SheetsLogger] Ensure the sheet is shared with service account: {self._sa_email}\n")
                                    fh.write(f"[SheetsLogger] Sheet URL: https://docs.google.com/spreadsheets/d/{self.sheet_id}\n")
                            except OSError:
                                pass
                            if self._flush_single_tab_to_csv(tab, rows):
                                self._buffers[tab] = []
                            continue
                except gspread.exceptions.APIError as e:
                    # Unexpected API error resolving worksheet; fall back to CSV
                    try:
                        out_dir = self._paper_root()
                        os.makedirs(out_dir, exist_ok=True)
                        with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                            fh.write('[SheetsLogger] APIError resolving worksheet ' + str(tab) + '; using CSV fallback. ' + repr(e) + '\n')
                            if self._sa_email:
                                fh.write(f"[SheetsLogger] Ensure the sheet is shared with service account: {self._sa_email}\n")
                            fh.write(f"[SheetsLogger] Sheet URL: https://docs.google.com/spreadsheets/d/{self.sheet_id}\n")
                    except OSError:
                        pass
                    if self._flush_single_tab_to_csv(tab, rows):
                        self._buffers[tab] = []
                    continue

                # Initialize headers once per tab if provided and sheet appears empty
                if not self._initialized_tabs.get(tab):
                    header = self._headers.get(tab)
                    if header:
                        try:
                            first_row = ws.row_values(1)
                            if not first_row:
                                ws.append_row(header, value_input_option="RAW")
                        except (gspread.exceptions.APIError, gspread.WorksheetNotFound):
                            # Non-fatal; header init is best-effort
                            pass
                    self._initialized_tabs[tab] = True
                # Append rows
                try:
                    ws.append_rows(rows, value_input_option='RAW')
                except gspread.exceptions.APIError as e:
                    # Log APIError details for this tab
                    try:
                        out_dir = self._paper_root()
                        os.makedirs(out_dir, exist_ok=True)
                        with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                            fh.write('[SheetsLogger] APIError while appending rows to tab ' + str(tab) + ': ' + repr(e) + '\n')
                            if self._sa_email:
                                fh.write(f"[SheetsLogger] Ensure the sheet is shared with service account: {self._sa_email}\n")
                            fh.write(f"[SheetsLogger] Sheet URL: https://docs.google.com/spreadsheets/d/{self.sheet_id}\n")
                    except OSError:
                        pass
                    raise
                except Exception as e:
                    # Log non-API errors and raise to trigger fallback handling below
                    try:
                        out_dir = self._paper_root()
                        os.makedirs(out_dir, exist_ok=True)
                        import traceback

                        with open(
                            os.path.join(out_dir, "live_errors.log"),
                            "a",
                            encoding="utf-8",
                        ) as fh:
                            fh.write(
                                "[SheetsLogger] Error while appending rows to tab "
                                + str(tab)
                                + ": "
                                + repr(e)
                                + "\n"
                            )
                            fh.write(traceback.format_exc() + "\n")
                    except OSError:
                        pass
                    raise
                # Also mirror to local CSV for offline/debug analysis
                try:
                    self._flush_single_tab_to_csv(tab, rows)
                except Exception:
                    pass
                self._buffers[tab] = []
            except gspread.exceptions.APIError as e:
                # Fallback to local CSV for this tab; keep buffer empty only if CSV write succeeds
                try:
                    out_dir = self._paper_root()
                    os.makedirs(out_dir, exist_ok=True)
                    with open(os.path.join(out_dir, 'live_errors.log'), 'a', encoding='utf-8') as fh:
                        fh.write('[SheetsLogger] APIError caught for tab ' + str(tab) + '; using CSV fallback. ' + repr(e) + '\n')
                        if self._sa_email:
                            fh.write(f"[SheetsLogger] Ensure the sheet is shared with service account: {self._sa_email}\n")
                        fh.write(f"[SheetsLogger] Sheet URL: https://docs.google.com/spreadsheets/d/{self.sheet_id}\n")
                except OSError:
                    pass
                if self._flush_single_tab_to_csv(tab, rows):
                    self._buffers[tab] = []

    def _flush_to_csv_fallback(self) -> None:
        for tab, rows in list(self._buffers.items()):
            if not rows:
                continue
            if self._flush_single_tab_to_csv(tab, rows):
                self._buffers[tab] = []

    def _flush_single_tab_to_csv(self, tab: str, rows: List[List]) -> bool:
        try:
            out_dir = os.path.abspath(os.path.join(self._paper_root(), 'sheets_fallback'))
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"{tab}.csv")
            write_header = (not os.path.exists(path)) and bool(self._headers.get(tab))
            with open(path, "a", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                if write_header:
                    w.writerow(self._headers.get(tab))
                w.writerows(rows)
            return True
        except OSError:
            return False
