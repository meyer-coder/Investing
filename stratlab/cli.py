"""Command line for stratlab.

    python -m stratlab batch FILE.json      log, run and rank a batch of cards (with random controls)
    python -m stratlab run CARD.json        log and run one card
    python -m stratlab board [--top N]      the leaderboard
    python -m stratlab show L0001           one card, in words, with its results
    python -m stratlab families             the signal families and filters
"""
from __future__ import annotations

import argparse
import json
import sys

from . import filters as flt
from . import log
from . import signals as sig
from .batch import run_batch


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="stratlab", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("batch")
    b.add_argument("file")
    b.add_argument("--controls", type=int, default=None)
    r = sub.add_parser("run")
    r.add_argument("file")
    bd = sub.add_parser("board")
    bd.add_argument("--top", type=int, default=30)
    s = sub.add_parser("show")
    s.add_argument("id")
    sub.add_parser("families")
    a = p.parse_args(argv)
    if a.cmd == "batch":
        run_batch(json.load(open(a.file)), controls=a.controls)
        print(log.leaderboard(top=30))
    elif a.cmd == "run":
        card = json.load(open(a.file))
        ids = run_batch({"name": f"single:{a.file}", "base": card, "controls": 0})
        print(log.show(ids[0]))
    elif a.cmd == "board":
        print(log.leaderboard(top=a.top))
    elif a.cmd == "show":
        print(log.show(a.id))
    elif a.cmd == "families":
        print("Signal families:")
        for name in sig.FAMILIES:
            print(f"  {name:<24} {sig.describe(name, {})}")
        print("\nFilters (confluences):")
        for name in flt.FILTERS:
            print(f"  {name:<24} {flt.describe({'type': name})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
