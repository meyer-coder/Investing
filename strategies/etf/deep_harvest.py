"""Harvest every finished island more deeply than the grind's first pass.

    python strategies/etf/deep_harvest.py [--top 60]

The grind harvests each island's 20 best on training; the held-out months are
violent enough that the 21st to 60th often do better there.  Runs already deep
harvested are listed in runs/etf/deep_done.txt and skipped.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from gauntlet import harvest                                               # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=60)
    args = ap.parse_args(argv)
    done_file = ROOT / "runs" / "etf" / "deep_done.txt"
    done = set(done_file.read_text().split()) if done_file.exists() else set()
    for db in sorted((ROOT / "runs" / "etf").glob("*.sqlite")):
        try:
            rows = sqlite3.connect(db).execute("SELECT id, status FROM runs").fetchall()
        except sqlite3.Error:
            continue
        for run_id, status in rows:
            if status != "finished" or run_id in done:
                continue
            print(f"deep harvest {db.name} {run_id}", flush=True)
            harvest([run_id], args.top, str(db))
            done.add(run_id)
            done_file.write_text("\n".join(sorted(done)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
