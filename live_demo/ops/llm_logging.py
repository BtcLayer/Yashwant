import os
import json
from datetime import datetime
from typing import Any, Dict, Optional


def _logs_dir() -> str:
    """Resolve unified logs directory under MetaStacker/paper_trading_outputs/logs.

    Priority:
      1) PAPER_TRADING_ROOT env var (absolute or relative) + '/logs'
      2) MetaStacker root (parent of repo) / 'paper_trading_outputs/logs'
    """
    pt_root = os.environ.get('PAPER_TRADING_ROOT')
    if pt_root:
        try:
            return os.path.abspath(os.path.join(pt_root, 'logs'))
        except Exception:
            return os.path.join(pt_root, 'logs')
    here = os.path.dirname(__file__)                 # .../MetaStackerBandit/live_demo/ops
    live_demo_root = os.path.abspath(os.path.join(here, os.pardir))   # .../MetaStackerBandit/live_demo
    repo_root = os.path.abspath(os.path.join(live_demo_root, os.pardir))  # .../MetaStackerBandit
    metastacker_root = os.path.abspath(os.path.join(repo_root, os.pardir)) # .../MetaStacker
    unified = os.path.normpath(os.path.join(metastacker_root, 'paper_trading_outputs', 'logs'))
    return unified


essential_max_fields = 32
essential_max_bytes = 1536  # ~1.5KB per line


def _prune_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(rec, dict):
        return {"value": rec}
    # Trim fields if too many
    items = list(rec.items())[:essential_max_fields]
    out: Dict[str, Any] = {}
    for k, v in items:
        out[k] = v
    # Enforce size cap by dropping trailing fields if needed
    data = json.dumps(out, ensure_ascii=False)
    if len(data.encode('utf-8')) <= essential_max_bytes:
        return out
    # Drop keys from the end until within the limit
    for k, _ in list(out.items())[::-1]:
        out.pop(k, None)
        data = json.dumps(out, ensure_ascii=False)
        if len(data.encode('utf-8')) <= essential_max_bytes:
            break
    return out


def write_jsonl(kind: str, record: Dict[str, Any], asset: Optional[str] = None, root: Optional[str] = None) -> None:
    """Write a single JSONL record to canonical partitioned path:
    paper_trading_outputs/{timeframe}/logs/{kind}/date=YYYY-MM-DD/asset={symbol}/{kind}.jsonl
    
    - Applies small field/size caps to keep lines LLM-friendly.
    - Best-effort: swallows IO errors to avoid impacting the trading loop.
    """
    try:
        # Use provided root or fall back to _logs_dir()
        if root:
            base = root
        else:
            base = _logs_dir()
        
        # Normalize kind names: e.g., ensemble_log -> ensemble
        sub = str(kind).lower().replace('_log', '')
        
        # Date partition
        date_dir = datetime.utcnow().strftime('date=%Y-%m-%d')
        
        # Asset partition (default to UNKNOWN if not provided)
        rec = dict(record) if isinstance(record, dict) else {"value": record}
        if asset:
            symbol = asset
            if 'asset' not in rec:
                rec['asset'] = asset
        else:
            # Try to extract from record
            symbol = rec.get('asset') or rec.get('symbol') or 'UNKNOWN'
        
        asset_dir = f"asset={symbol}"
        
        # Build canonical path: logs/{stream}/date=.../asset=.../{stream}.jsonl
        out_dir = os.path.join(base, sub, date_dir, asset_dir)
        os.makedirs(out_dir, exist_ok=True)
        
        fname = f"{sub}.jsonl"
        path = os.path.join(out_dir, fname)
        
        pruned = _prune_record(rec)
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(pruned, ensure_ascii=False) + "\n")
    except OSError:
        # Non-fatal: logging should not break the loop
        return

