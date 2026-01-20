"""
Builds a compact LLM context pack from unified gzipped JSONL logs.

Usage (Windows PowerShell):
  python -m live_demo.tools.build_context_pack

Optional env vars:
  LLM_PACK_HOURS   # default: 24
  LLM_PACK_TOP_K   # default: 500
  LOGS_ROOT        # default: paper_trading_outputs/logs (unified base)
  LLM_PACK_OUT     # default: paper_trading_outputs/llm_context/context_pack.json.gz
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import importlib


def _ensure_repo_root_on_path() -> None:
    # Add repo root (parent of live_demo) to sys.path so 'ops' package is importable
    here = Path(__file__).resolve()
    live_demo_root = here.parents[1]
    repo_root = live_demo_root.parent
    if str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))


_ensure_repo_root_on_path()

def _load_build_llm_context_pack():
    """Import build_llm_context_pack robustly without static import errors.
    Tries repo-level ops.llm_logging first, then package-local live_demo.ops.llm_logging.
    """
    try:
        mod = importlib.import_module("ops.llm_logging")
        return getattr(mod, "build_llm_context_pack")
    except ModuleNotFoundError:
        pass

    try:
        mod = importlib.import_module("live_demo.ops.llm_logging")
        return getattr(mod, "build_llm_context_pack")
    except ModuleNotFoundError:
        pass

    raise ModuleNotFoundError(
        "Unable to import 'build_llm_context_pack' from ops.llm_logging or live_demo.ops.llm_logging"
    )


build_llm_context_pack = _load_build_llm_context_pack()


def main() -> None:
    hours = int(os.environ.get("LLM_PACK_HOURS", "24"))
    top_k = int(os.environ.get("LLM_PACK_TOP_K", "500"))
    root = os.environ.get("LOGS_ROOT")
    if not root:
        # Prefer per-run PAPER_TRADING_ROOT/logs when available (timeframe-aware)
        ptr = os.environ.get("PAPER_TRADING_ROOT")
        if ptr:
            root = str((Path(ptr) / "logs").resolve())
        else:
            # Fallback to repo-level paper_trading_outputs/logs
            here = Path(__file__).resolve()
            live_demo_root = here.parents[1]
            repo_root = live_demo_root.parent
            root = str((repo_root / "paper_trading_outputs" / "logs").resolve())
    out = os.environ.get("LLM_PACK_OUT") or str(
        (Path(root).parent / "llm_context" / "context_pack.json").resolve()
    )
    path = build_llm_context_pack(root=root, hours=hours, top_k=top_k, out=out)
    print({"status": "ok", "out": path, "hours": hours, "top_k": top_k, "root": root})


if __name__ == "__main__":
    main()
