import os
import sys
import pathlib

# Ensure repository root is on sys.path so 'ops' can be imported reliably
HERE = pathlib.Path(__file__).resolve()
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.llm_logging import (
    build_llm_context_pack,
    build_llm_context_bundle,
    build_llm_paste_pack,
)

if __name__ == "__main__":
    hours = int(os.environ.get("LLM_PACK_HOURS", 24))
    top_k = int(os.environ.get("LLM_PACK_TOPK", 500))
    out = os.environ.get("LLM_PACK_OUT", "llm_context/context_pack.json.gz")
    make_bundle = os.environ.get("LLM_PACK_BUNDLE", "1").strip() not in ("0", "false", "False")

    pack_path = build_llm_context_pack(hours=hours, top_k=top_k, out=out)
    print(pack_path)

    if make_bundle:
        out_zip = os.environ.get("LLM_PACK_ZIP", "llm_context/context_bundle.zip")
        zip_path = build_llm_context_bundle(hours=hours, top_k=top_k, out_zip=out_zip)
        print(zip_path)
        # Also generate the paste-friendly JSON pack
        paste_out = os.environ.get("LLM_PASTE_OUT", "llm_context/paste_pack.json.gz")
        paste_path = build_llm_paste_pack(hours=hours, top_k=top_k, out=paste_out)
        print(paste_path)
