import sys
import gzip
from pathlib import Path


def tail_jsonl_gz(path: Path, n: int = 5):
    if not path.exists():
        print(f"[ERR] File not found: {path}")
        return 1
    try:
        with gzip.open(path, 'rt', encoding='utf-8', errors='replace') as fh:
            lines = fh.readlines()
        for line in lines[-n:]:
            print(line.rstrip())
        return 0
    except Exception as e:
        print(f"[ERR] Failed to read {path}: {e}")
        return 2


def main(argv):
    if len(argv) < 2:
        print("Usage: tail_jsonl_gz.py <path_to_jsonl.gz> [lines]")
        return 64
    p = Path(argv[1])
    try:
        n = int(argv[2]) if len(argv) > 2 else 5
    except ValueError:
        n = 5
    return tail_jsonl_gz(p, n)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
