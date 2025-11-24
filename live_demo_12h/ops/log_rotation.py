import os
import time


def delete_old_logs(root: str, days: int = 30):
    """Delete log files under `root` older than `days` days.

    Deletes gzip and plain JSONL files (.jsonl.gz and .jsonl) and prunes empty dirs.
    Best-effort: do not throw on permission errors.
    """
    cutoff = time.time() - float(days) * 86400.0
    for dirpath, _, filenames in os.walk(root, topdown=False):
        for fn in filenames:
<<<<<<< HEAD
            if not (fn.endswith('.jsonl') or fn.endswith('.jsonl.gz')):
=======
            if not fn.endswith(".jsonl"):
>>>>>>> a425beb9a39dcb2c03ba879f40b73a3beb6babde
                continue
            fp = os.path.join(dirpath, fn)
            try:
                mtime = os.path.getmtime(fp)
            except OSError:
                continue
            if mtime < cutoff:
                try:
                    os.remove(fp)
                except OSError:
                    continue
        # try remove empty dirs
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
        except OSError:
            continue


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument(
        "--root", default=os.path.join(os.path.dirname(__file__), "..", "logs")
    )
    p.add_argument("--days", type=int, default=30)
    args = p.parse_args()
    delete_old_logs(os.path.abspath(args.root), days=args.days)
