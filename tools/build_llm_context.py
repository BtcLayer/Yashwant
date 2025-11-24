from __future__ import annotations

import argparse
from pathlib import Path  # Only one import needed

import sys

# Ensure repository root is on sys.path so 'ops' can be imported when executed from tools/
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.llm_logging import build_llm_context_pack  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(description="Build LLM context pack from unified logs")
    parser.add_argument("--hours", type=int, default=24, help="How many hours of logs to include")
    parser.add_argument("--top-k", type=int, default=500, help="Max rows per stream")
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path("paper_trading_outputs") / "logs" / "llm_context" / "context_pack.json.gz"),
        help="Output gzip JSON path",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the pack using unified logs root by default
    result = build_llm_context_pack(hours=int(args.hours), top_k=int(args.top_k), out=str(out_path))
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
