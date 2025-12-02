"""Small utility to locate heartbeat files under paper_trading_outputs/logs.

This is intentionally tiny and hermetic so it can be used in CI smoke steps.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import List


def find_heartbeat_files(root: str = "paper_trading_outputs/logs") -> List[str]:
    pattern = os.path.join(root, "**", "heartbeat.json")
    return glob.glob(pattern, recursive=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Find heartbeat files under a logs folder")
    parser.add_argument("root", nargs="?", default="paper_trading_outputs/logs", help="root logs path to search")
    args = parser.parse_args()

    found = find_heartbeat_files(args.root)
    if not found:
        print(f"No heartbeat.json files found under {args.root}")
        return 2

    # Print up to first 10 results for human readable output
    for p in found[:10]:
        print(p)

    print(f"Found {len(found)} heartbeat.json files (showing up to 10)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
