from typing import Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials
import os
import csv


class SheetsLogger:
    def __init__(
        self,
        creds_json_path: Optional[str],
        sheet_id: str,
        headers: Optional[Dict[str, List[str]]] = None,
    ):
        self.sheet_id = sheet_id
        self.gc = None
        self._warned_no_gc = False
        self._warned_api_error = False
        if creds_json_path:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            credentials = Credentials.from_service_account_file(
                creds_json_path, scopes=scopes
            )
            self.gc = gspread.authorize(credentials)
        self._buffers: Dict[str, List[List]] = {}
        self._headers = headers or {}
        self._initialized_tabs: Dict[str, bool] = {}

    def _paper_root(self) -> str:
        """Resolve the base paper_trading_outputs directory.
        Priority:
          1) PAPER_TRADING_ROOT env var (absolute or relative)
          2) MetaStacker root (.. from repo root)
        """
        env = os.environ.get('PAPER_TRADING_ROOT')
        if env:
            try:
                return os.path.abspath(env)
            except Exception:
                return env
        # Default to MetaStacker central root
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))  # .../live_demo
        metastacker_root = os.path.abspath(os.path.join(repo_root, os.pardir))  # .../MetaStacker
        return os.path.abspath(os.path.join(metastacker_root, 'paper_trading_outputs'))

    def ensure_headers(self):
        """
        Proactively create tabs and insert header rows (if provided) before any data rows are appended.
        Safe to call multiple times.
        """
        if not self.gc or not self._headers:
            return
        # Open sheet; if it fails via gspread, just return
        try:
            sh = self.gc.open_by_key(self.sheet_id)
        except gspread.exceptions.APIError:
            return
        except Exception as e:
            # Log unexpected errors to live_errors.log for diagnosis and bail out of header init
            try:
                out_dir = os.path.abspath(
                    os.path.join(
                        os.path.dirname(__file__), "..", "paper_trading_outputs"
                    )
                )
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
<<<<<<< HEAD
                    # Centralize under MetaStacker/paper_trading_outputs
                    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))  # .../live_demo
                    metastacker_root = os.path.abspath(os.path.join(repo_root, os.pardir))  # .../MetaStackerBandit -> MetaStacker
                    out_dir = os.path.abspath(os.path.join(metastacker_root, 'paper_trading_outputs'))
=======
                    out_dir = os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__), "..", "paper_trading_outputs"
                        )
                    )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
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
        try:
            sh = self.gc.open_by_key(self.sheet_id)
        except gspread.exceptions.APIError:
            # Fallback to local CSV for all tabs
            try:
                if not self._warned_api_error:
<<<<<<< HEAD
                    out_dir = self._paper_root()
=======
                    out_dir = os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__), "..", "paper_trading_outputs"
                        )
                    )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
                    os.makedirs(out_dir, exist_ok=True)
                    with open(
                        os.path.join(out_dir, "live_errors.log"), "a", encoding="utf-8"
                    ) as fh:
                        fh.write(
                            "[SheetsLogger] Google Sheets API error; falling back to local CSV. Ensure the sheet_id is correct and the service account has access.\n"
                        )
                    self._warned_api_error = True
            except OSError:
                pass
            self._flush_to_csv_fallback()
            return
        except Exception as e:
            # Catch any other unexpected errors when opening the sheet and fall back
            try:
                if not self._warned_api_error:
<<<<<<< HEAD
                    out_dir = self._paper_root()
=======
                    out_dir = os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__), "..", "paper_trading_outputs"
                        )
                    )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
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
                try:
                    ws = sh.worksheet(tab)
                except gspread.WorksheetNotFound:
                    ws = sh.add_worksheet(title=tab, rows=1000, cols=30)
                # Initialize headers once per tab if provided and sheet appears empty
                if not self._initialized_tabs.get(tab):
                    header = self._headers.get(tab)
                    if header:
                        try:
                            first_row = ws.row_values(1)
                            if not first_row:
                                ws.append_row(header, value_input_option="RAW")
                        except (gspread.exceptions.APIError, gspread.WorksheetNotFound):
                            pass
                    self._initialized_tabs[tab] = True
                # Append rows
                try:
                    ws.append_rows(rows, value_input_option="RAW")
                except gspread.exceptions.APIError:
                    raise
                except Exception as e:
                    # Log non-API errors and raise to trigger fallback handling below
                    try:
<<<<<<< HEAD
                        out_dir = self._paper_root()
=======
                        out_dir = os.path.abspath(
                            os.path.join(
                                os.path.dirname(__file__), "..", "paper_trading_outputs"
                            )
                        )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
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
            except gspread.exceptions.APIError:
                # Fallback to local CSV for this tab; keep buffer empty only if CSV write succeeds
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
<<<<<<< HEAD
            out_dir = os.path.abspath(os.path.join(self._paper_root(), 'sheets_fallback'))
=======
            out_dir = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "paper_trading_outputs",
                    "sheets_fallback",
                )
            )
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
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
