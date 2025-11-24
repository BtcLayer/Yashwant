import os
import time
from datetime import datetime, timezone

# Import before changing cwd so module resolution works
from unified_hyperliquid_scraper import UnifiedHyperliquidScraper, OUTPUT_FILES


def make_isolated_dir() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join(root, "scratch_runs", f"smoke_{ts}")
    os.makedirs(out_dir, exist_ok=True)
    # Ensure live_demo subdir exists in isolated path for cohort files
    os.makedirs(os.path.join(out_dir, "live_demo"), exist_ok=True)
    return out_dir


def run_smoke():
    # Prepare isolated working directory
    out_dir = make_isolated_dir()
    print(f"Writing outputs to: {out_dir}")

    # Change CWD so scraper writes relative CSVs into the isolated folder
    os.chdir(out_dir)

    s = UnifiedHyperliquidScraper()

    # Only run leaderboard -> cohorts -> BTC filter to keep this fast
    lb = s.collect_leaderboard_data()
    if lb is None or lb.empty:
        print("Leaderboard fetch returned empty; aborting smoke run.")
        return 2

    top, bot = s.identify_cohorts(lb, top_count=50, bottom_count=30)
    if not top and not bot:
        print("Cohort identification yielded no addresses; aborting smoke run.")
        return 3

    # Ultra-fast filter for smoke: skip checks (cap=0) so it writes fallback cohorts immediately
    ft, fb = s.filter_btc_active_cohorts(
        top, bot, days=1, min_fills=1, min_usd=0.0, cap=0
    )
    print(f"Filtered cohorts -> top: {len(ft)}, bottom: {len(fb)}")

    # Print a minimal summary of files present
    present = []
    for key, fname in OUTPUT_FILES.items():
        if os.path.exists(fname):
            present.append((key, fname, os.path.getsize(fname)))
    print("Files written:")
    for k, f, sz in present:
        print(f" - {k}: {f} ({sz} bytes)")

    # Exit code 0 means success
    return 0


if __name__ == "__main__":
    code = run_smoke()
    raise SystemExit(code)
